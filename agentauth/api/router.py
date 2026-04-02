from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.adapters import BaseAdapter, GeminiAdapter, MockAdapter
from ..core.database import SessionLocal
from ..core.models import Agent, AgentPermission, AuditLog, Integration

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

    # 1. Authenticate Agent
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid Agent API Key")

    if agent.is_frozen:
        log = AuditLog(
            agent_id=agent.id,
            target_service=integration_name,
            request_details="Blocked by Kill Switch",
            response_status=403,
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=403, detail="Agent is currently frozen (Kill Switch Enabled)."
        )

    # 2. IAM Check (Scoped Permissions)
    permission = (
        db.query(AgentPermission)
        .filter(AgentPermission.agent_id == agent.id, AgentPermission.scope == integration_name)
        .first()
    )

    if not permission:
        log = AuditLog(
            agent_id=agent.id,
            target_service=integration_name,
            request_details="Unauthorized Scope Access",
            response_status=403,
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: Agent does not have the '{integration_name}' scope.",
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
        adapter = GeminiAdapter(api_key=str(integration.provider_key))
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

    response = await adapter.forward(body)

    # 5. Log request
    status_code = 200 if "error" not in response else 400
    log = AuditLog(
        agent_id=agent.id,
        target_service=integration_name,
        request_details=str(body),
        response_status=status_code,
    )
    db.add(log)
    db.commit()

    return response


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

    integration.provider_key = key
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
        "agent": {"id": new_agent.id, "name": new_agent.name, "api_key": new_agent.api_key},
    }


@router.post("/internal/agents/{agent_id}/freeze")
def freeze_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent:
        agent.is_frozen = True  # type: ignore
        db.commit()
        return {"status": "success", "is_frozen": agent.is_frozen}
    raise HTTPException(status_code=404)
