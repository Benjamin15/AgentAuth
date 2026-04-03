import datetime
import time
import uuid

from cachetools import TTLCache
from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..alerting import AlertEngine
from ..core.adapters import BaseAdapter, GeminiAdapter, MockAdapter
from ..core.database import SessionLocal
from ..core.models import Agent, AgentPermission, AgentToken, AuditLog, Integration, ModelPricing
from ..core.security import decrypt_secret, encrypt_secret

# Cache for authentication: (token, integration_name) -> (agent_id, is_frozen, has_permission)
auth_cache: TTLCache = TTLCache(maxsize=1024, ttl=60)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/v1/proxy/{integration_name}")
async def proxy_request(
    integration_name: str,
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    cache_key = (token, integration_name)

    # 1. & 2. Authenticate Token and IAM Check (Scoped Permissions)
    if cache_key in auth_cache:
        agent_id, is_frozen, has_permission = auth_cache[cache_key]
    else:
        # DB Lookup
        agent_token = db.query(AgentToken).filter(AgentToken.access_token == token).first()
        if not agent_token or agent_token.expires_at < datetime.datetime.now(datetime.UTC).replace(
            tzinfo=None
        ):
            raise HTTPException(status_code=401, detail="Invalid or expired Agent API Key")

        agent = agent_token.agent

        # Check permissions
        permission = (
            db.query(AgentPermission)
            .filter(AgentPermission.agent_id == agent.id, AgentPermission.scope == integration_name)
            .first()
        )

        agent_id = agent.id
        is_frozen = agent.is_frozen
        has_permission = True if permission else False

        # Store in cache
        auth_cache[cache_key] = (agent_id, is_frozen, has_permission)

    # 3. Handle Frozen or Unauthorized in Proxy Logic
    if is_frozen:
        log = AuditLog(
            agent_id=agent_id,
            target_service=integration_name,
            request_details="Blocked by Kill Switch (Cached)",
            response_status=403,
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=403, detail="Agent is currently frozen (Kill Switch Enabled)."
        )

    if not has_permission:
        log = AuditLog(
            agent_id=agent_id,
            target_service=integration_name,
            request_details="Unauthorized Scope Access (Cached)",
            response_status=403,
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: Agent does not have the '{integration_name}' scope.",
        )

    # Load agent object for the rest of the flow
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=401, detail="Agent not found.")

    # 3. Quota Check (Hard Block)
    if agent.monthly_budget_usd is not None:
        # Calculate total spent this month
        first_of_month = (
            datetime.datetime.now(datetime.UTC)
            .replace(tzinfo=None)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
        total_spent = (
            db.query(AuditLog)
            .filter(AuditLog.agent_id == agent.id, AuditLog.timestamp >= first_of_month)
            .with_entities(AuditLog.cost_usd)
            .all()
        )
        current_spend = sum([float(log.cost_usd or 0) for log in total_spent])

        if current_spend >= agent.monthly_budget_usd:
            log = AuditLog(
                agent_id=agent.id,
                target_service=integration_name,
                request_details=f"Blocked: Quota Exceeded (${current_spend:.2f} / ${agent.monthly_budget_usd:.2f})",
                response_status=402,
            )
            db.add(log)
            db.commit()
            raise HTTPException(
                status_code=402,
                detail=f"Payment Required: Monthly budget of ${agent.monthly_budget_usd:.2f} reached.",
            )

    # 3. Check Integration and Get Adapter
    integration = db.query(Integration).filter(Integration.name == integration_name).first()
    if not integration:
        raise HTTPException(
            status_code=400, detail=f"Integration '{integration_name}' not found in database"
        )

    adapter: BaseAdapter
    if integration_name == "gemini":
        if not integration.provider_key:
            raise HTTPException(
                status_code=500, detail="Gemini API Key not configured in AgentAuth"
            )
        decrypted_key = decrypt_secret(str(integration.provider_key))
        if decrypted_key is None:
            raise HTTPException(status_code=500, detail="Failed to decrypt Gemini API Key")
        adapter = GeminiAdapter(api_key=decrypted_key)
    elif integration_name == "mock":
        adapter = MockAdapter()
    else:
        raise HTTPException(
            status_code=400, detail=f"Adapter for '{integration_name}' not implemented"
        )

    # 4. Forward Request
    try:
        body = await request.json()
    except Exception:
        body = {}

    start_time = time.perf_counter()
    response = await adapter.forward(body)
    end_time = time.perf_counter()
    latency_ms = int((end_time - start_time) * 1000)

    # 5. Log request
    status_code = 200 if "error" not in response else 400
    usage = response.get("usage", {})

    # Calculate total if not provided but prompt/completion are
    p_tokens = usage.get("prompt")
    c_tokens = usage.get("completion")
    t_tokens = usage.get("total")
    if t_tokens is None and p_tokens is not None and c_tokens is not None:
        t_tokens = p_tokens + c_tokens

    # Calculate cost
    model_name = response.get("model_name", "unknown")
    pricing = db.query(ModelPricing).filter(ModelPricing.model_name == model_name).first()

    cost_usd: float = 0.0
    if pricing:
        input_cost = (p_tokens or 0) * (pricing.input_1m_price / 1_000_000)
        output_cost = (c_tokens or 0) * (pricing.output_1m_price / 1_000_000)
        cost_usd = float(input_cost + output_cost)  # type: ignore[arg-type]

    log = AuditLog(
        agent_id=agent.id,
        target_service=integration_name,
        request_details=str(body),
        response_status=status_code,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        total_tokens=t_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )
    db.add(log)
    db.commit()

    # Evaluate budget alert rules in the background (fire-and-forget).
    # A new DB session is NOT needed here because the commit above has already
    # persisted the latest cost data; the engine re-queries inside its own call.
    import asyncio

    asyncio.create_task(AlertEngine.evaluate(agent, db))

    # If the response was wrapped by the adapter (e.g. Gemini), return the 'data' part
    return response.get("data", response)


@router.post("/oauth/token")
def oauth_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    expires_in: int = Form(3600),
    db: Session = Depends(get_db),
):
    """Obtain an access token using Client Credentials Grant."""
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")

    agent = (
        db.query(Agent)
        .filter(Agent.client_id == client_id, Agent.client_secret == client_secret)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid client_id or client_secret")

    if agent.is_frozen:
        raise HTTPException(status_code=403, detail="Agent is currently frozen.")

    # Validate expires_in (max 24 hours)
    expires_in = min(expires_in, 86400)
    expires_in = max(expires_in, 60)  # min 1 minute

    # Generate token
    token_str = f"aa_token_{uuid.uuid4().hex}"
    expires = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(
        seconds=expires_in
    )

    agent_token = AgentToken(agent_id=agent.id, access_token=token_str, expires_at=expires)
    db.add(agent_token)
    db.commit()

    return {"access_token": token_str, "token_type": "bearer", "expires_in": expires_in}


@router.post("/internal/agents/{agent_id}/permissions")
def grant_permission(agent_id: int, payload: dict, db: Session = Depends(get_db)):
    """Grant a scope to an agent."""
    scope = payload.get("scope")
    if not scope:
        raise HTTPException(status_code=400, detail="Missing 'scope' in JSON payload")

    # Check if exists
    existing = (
        db.query(AgentPermission)
        .filter(AgentPermission.agent_id == agent_id, AgentPermission.scope == scope)
        .first()
    )
    if existing:
        return {"status": "success", "message": "Permission already exists"}

    new_perm = AgentPermission(agent_id=agent_id, scope=scope)
    db.add(new_perm)
    db.commit()
    auth_cache.clear()  # Invalidate all cached auth results
    return {"status": "success", "message": f"Permission '{scope}' granted"}


@router.delete("/internal/agents/{agent_id}/permissions/{scope}")
def revoke_permission(agent_id: int, scope: str, db: Session = Depends(get_db)):
    """Revoke a scope from an agent."""
    perm = (
        db.query(AgentPermission)
        .filter(AgentPermission.agent_id == agent_id, AgentPermission.scope == scope)
        .first()
    )
    if perm:
        db.delete(perm)
        db.commit()
        auth_cache.clear()  # Invalidate all cached auth results
        return {"status": "success", "message": f"Permission '{scope}' revoked"}
    raise HTTPException(status_code=404, detail="Permission not found")


@router.post("/internal/integrations/{name}/key")
def update_integration_key(name: str, payload: dict, db: Session = Depends(get_db)):
    """Update the provider API key via Curl"""
    integration = db.query(Integration).filter(Integration.name == name).first()
    if not integration:
        # Create it if it doesn't exist
        integration = Integration(name=name)
        db.add(integration)

    key = payload.get("key")
    if not key:
        raise HTTPException(status_code=400, detail="Missing 'key' in JSON payload")

    integration.provider_key = encrypt_secret(key)  # type: ignore
    db.commit()
    return {"status": "success", "message": f"Key for {name} updated"}


# Internal management endpoints for the Dash UI
@router.get("/internal/agents")
def get_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


@router.post("/internal/agents")
def create_agent(payload: dict, db: Session = Depends(get_db)):
    """Create a new agent with a custom name and optional description."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name' in JSON payload")

    new_agent = Agent(name=name, description=payload.get("description", ""))
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return {
        "status": "success",
        "agent": {
            "id": new_agent.id,
            "name": new_agent.name,
            "client_id": new_agent.client_id,
            "client_secret": new_agent.client_secret,
        },
    }


@router.post("/internal/agents/{agent_id}/freeze")
def freeze_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent:
        agent.is_frozen = True  # type: ignore
        db.commit()
        auth_cache.clear()  # Kill switch: Invalidate all cached auth results instantly
        return {"status": "success", "is_frozen": agent.is_frozen}
    raise HTTPException(status_code=404)
