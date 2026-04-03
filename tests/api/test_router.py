from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentauth.api.router import auth_cache
from agentauth.core.models import (
    Agent,
    AgentPermission,
    AgentToken,
    AuditLog,
    Integration,
)


@pytest.fixture(autouse=True)
def clear_cache():
    auth_cache.clear()


@pytest.mark.asyncio
async def test_proxy_auth_success(client, db_session):
    agent = Agent(name="ProxyBot")
    db_session.add(agent)
    db_session.flush()
    future = datetime.now() + timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="valid-token", expires_at=future))
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.merge(Integration(name="mock", is_active=True, provider_key="encrypted-key"))
    db_session.commit()

    with patch("agentauth.api.router.get_adapter") as mock_get:
        adapter_cls = MagicMock()
        adapter = AsyncMock()
        adapter.forward.return_value = {
            "model_name": "mock-model",
            "usage": {"prompt": 10, "completion": 20},
            "data": {"result": "success"},
        }
        adapter_cls.return_value = adapter
        adapter_cls.requires_auth = True
        mock_get.return_value = adapter_cls

        response = client.post(
            "/v1/proxy/mock",
            json={"model": "gpt-3.5", "messages": []},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        assert response.json()["result"] == "success"


def test_proxy_401_no_auth(client):
    response = client.post("/v1/proxy/mock", json={})
    assert response.status_code == 401


def test_proxy_401_invalid_token(client):
    response = client.post("/v1/proxy/mock", json={}, headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_proxy_401_expired_token(client, db_session):
    agent = Agent(name="ExpBot")
    db_session.add(agent)
    db_session.flush()
    past = datetime.now() - timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="exp-token", expires_at=past))
    db_session.commit()
    response = client.post("/v1/proxy/mock", json={}, headers={"Authorization": "Bearer exp-token"})
    assert response.status_code == 401


def test_proxy_403_agent_frozen(client, db_session):
    agent = Agent(name="FrozenBot", is_frozen=True)
    db_session.add(agent)
    db_session.flush()
    future = datetime.now() + timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="frozen-token", expires_at=future))
    db_session.commit()
    response = client.post(
        "/v1/proxy/mock", json={}, headers={"Authorization": "Bearer frozen-token"}
    )
    assert response.status_code == 403


def test_proxy_403_no_permission(client, db_session):
    agent = Agent(name="NoPermBot")
    db_session.add(agent)
    db_session.flush()
    future = datetime.now() + timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="no-perm-token", expires_at=future))
    db_session.commit()
    response = client.post(
        "/v1/proxy/mock", json={}, headers={"Authorization": "Bearer no-perm-token"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_proxy_402_quota_exceeded(client, db_session):
    agent = Agent(name="QuotaBot", monthly_budget_usd=10.0)
    db_session.add(agent)
    db_session.flush()
    future = datetime.now() + timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="quota-token", expires_at=future))
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    # Add spend
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=11.0, target_service="mock", response_status=200)
    )
    db_session.commit()

    response = client.post(
        "/v1/proxy/mock", json={}, headers={"Authorization": "Bearer quota-token"}
    )
    assert response.status_code == 402


def test_proxy_400_integration_not_found(client, db_session):
    agent = Agent(name="NotFoundBot")
    db_session.add(agent)
    db_session.flush()
    future = datetime.now() + timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="nf-token", expires_at=future))
    db_session.add(AgentPermission(agent_id=agent.id, scope="unknown"))
    db_session.commit()
    response = client.post(
        "/v1/proxy/unknown", json={}, headers={"Authorization": "Bearer nf-token"}
    )
    assert response.status_code == 400


def test_proxy_500_key_not_configured(client, db_session):
    agent = Agent(name="KeyBot")
    db_session.add(agent)
    db_session.flush()
    future = datetime.now() + timedelta(days=1)
    db_session.add(AgentToken(agent_id=agent.id, access_token="key-token", expires_at=future))
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.merge(Integration(name="mock", provider_key=None, is_active=True))
    db_session.commit()

    with patch("agentauth.api.router.get_adapter") as mock_get:
        adapter_cls = MagicMock()
        adapter_cls.requires_auth = True
        mock_get.return_value = adapter_cls
        response = client.post(
            "/v1/proxy/mock", json={}, headers={"Authorization": "Bearer key-token"}
        )
        assert response.status_code == 500


def test_oauth_token_client_credentials(client, db_session):
    agent = Agent(name="OAuthBot")
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": agent.client_id,
            "client_secret": agent.client_secret,
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_oauth_token_invalid_creds(client):
    response = client.post(
        "/oauth/token",
        data={"grant_type": "client_credentials", "client_id": "wrong", "client_secret": "wrong"},
    )
    assert response.status_code == 401


def test_oauth_token_frozen_agent(client, db_session):
    agent = Agent(name="FrozenOAuthBot", is_frozen=True)
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": agent.client_id,
            "client_secret": agent.client_secret,
        },
    )
    assert response.status_code == 403


def test_internal_get_agents(client, db_session):
    db_session.add(Agent(name="Bot1"))
    db_session.add(Agent(name="Bot2"))
    db_session.commit()
    response = client.get("/internal/agents")
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_create_agent_success(client):
    response = client.post("/internal/agents", json={"name": "NewBot", "description": "Desc"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_delete_agent_success(client, db_session):
    agent = Agent(name="DeleteBot")
    db_session.add(agent)
    db_session.commit()
    response = client.delete(f"/internal/agents/{agent.id}")
    assert response.status_code == 200
    assert db_session.get(Agent, agent.id) is None


def test_freeze_agent_endpoint(client, db_session):
    agent = Agent(name="FreezeMe")
    db_session.add(agent)
    db_session.commit()
    response = client.post(f"/internal/agents/{agent.id}/freeze")
    assert response.status_code == 200
    db_session.refresh(agent)
    assert agent.is_frozen is True


def test_permissions_grant_revoke(client, db_session):
    agent = Agent(name="PermBot")
    db_session.add(agent)
    db_session.commit()
    # Grant
    res = client.post(f"/internal/agents/{agent.id}/permissions", json={"scope": "openai"})
    assert res.status_code == 200
    assert (
        db_session.query(AgentPermission).filter_by(agent_id=agent.id, scope="openai").count() == 1
    )
    # Revoke
    res = client.delete(f"/internal/agents/{agent.id}/permissions/openai")
    assert res.status_code == 200
    assert (
        db_session.query(AgentPermission).filter_by(agent_id=agent.id, scope="openai").count() == 0
    )


def test_update_integration_key(client, db_session):
    res = client.post("/internal/integrations/openai/key", json={"key": "sk-new-key"})
    assert res.status_code == 200
    integration = db_session.query(Integration).filter_by(name="openai").first()
    assert integration is not None
    assert integration.provider_key is not None
