from unittest.mock import patch

from agentauth.core.models import Agent, AgentPermission, AuditLog, Integration


def test_create_agent_success(client, db_session):
    response = client.post(
        "/internal/agents", json={"name": "New Agent", "description": "A new bot"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "api_key" in response.json()["agent"]

    agent = db_session.query(Agent).filter_by(name="New Agent").one()
    assert agent.description == "A new bot"


def test_create_agent_missing_name(client):
    response = client.post("/internal/agents", json={"description": "Missing name"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing 'name' in JSON payload"


def test_get_agents(client, db_session):
    agent1 = Agent(name="Bot 1")
    agent2 = Agent(name="Bot 2")
    db_session.add(agent1)
    db_session.add(agent2)
    db_session.commit()

    response = client.get("/internal/agents")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_freeze_agent(client, db_session):
    agent = Agent(name="Kill Me")
    db_session.add(agent)
    db_session.commit()

    response = client.post(f"/internal/agents/{agent.id}/freeze")
    assert response.status_code == 200
    assert response.json()["is_frozen"] is True

    db_session.refresh(agent)
    assert agent.is_frozen is True


def test_freeze_agent_not_found(client):
    response = client.post("/internal/agents/999/freeze")
    assert response.status_code == 404


def test_manage_permissions(client, db_session):
    agent = Agent(name="IAM Bot")
    db_session.add(agent)
    db_session.commit()

    # 1. Grant
    response = client.post(f"/internal/agents/{agent.id}/permissions", json={"scope": "gemini"})
    assert response.status_code == 200

    db_session.refresh(agent)
    assert len(agent.permissions) == 1
    assert agent.permissions[0].scope == "gemini"

    # Existing perm test
    client.post(f"/internal/agents/{agent.id}/permissions", json={"scope": "gemini"})

    # Missing scope
    response3 = client.post(f"/internal/agents/{agent.id}/permissions", json={})
    assert response3.status_code == 400

    # 2. Revoke
    response4 = client.delete(f"/internal/agents/{agent.id}/permissions/gemini")
    assert response4.status_code == 200
    db_session.refresh(agent)
    assert len(agent.permissions) == 0

    # Revoke not found
    response5 = client.delete(f"/internal/agents/{agent.id}/permissions/missing")
    assert response5.status_code == 404


def test_update_integration_key(client, db_session):
    response = client.post("/internal/integrations/openai/key", json={"key": "sk-test"})
    assert response.status_code == 200
    assert db_session.query(Integration).filter_by(name="openai").first().provider_key == "sk-test"

    # Update existing
    client.post("/internal/integrations/openai/key", json={"key": "sk-test-new"})
    assert (
        db_session.query(Integration).filter_by(name="openai").first().provider_key == "sk-test-new"
    )

    # Missing key
    response3 = client.post("/internal/integrations/openai/key", json={})
    assert response3.status_code == 400


def test_proxy_auth_errors(client):
    # No auth
    response = client.post("/v1/proxy/mock")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid Authorization header"

    # Invalid token
    response2 = client.post("/v1/proxy/mock", headers={"Authorization": "Bearer invalid_token"})
    assert response2.status_code == 401
    assert response2.json()["detail"] == "Invalid Agent API Key"


def test_proxy_frozen_agent(client, db_session):
    agent = Agent(name="Frozen", is_frozen=True)
    db_session.add(agent)
    db_session.commit()

    response = client.post("/v1/proxy/mock", headers={"Authorization": f"Bearer {agent.api_key}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    assert "frozen" in response.json()["detail"]
    assert db_session.query(AuditLog).filter_by(agent_id=agent.id, response_status=403).count() == 1


def test_proxy_unauthorized_scope(client, db_session):
    agent = Agent(name="Forbidden")
    db_session.add(agent)
    db_session.commit()

    response = client.post("/v1/proxy/gemini", headers={"Authorization": f"Bearer {agent.api_key}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    assert "Permission denied" in response.json()["detail"]


def test_proxy_integration_not_found(client, db_session):
    agent = Agent(name="Ghost Integration")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="ghost"))
    db_session.commit()

    response = client.post("/v1/proxy/ghost", headers={"Authorization": f"Bearer {agent.api_key}"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "Integration 'ghost' not found" in response.json()["detail"]


def test_proxy_unimplemented_adapter(client, db_session):
    agent = Agent(name="Mystery Adapter")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="mystery"))
    db_session.add(Integration(name="mystery", is_active=True))
    db_session.commit()

    response = client.post(
        "/v1/proxy/mystery", headers={"Authorization": f"Bearer {agent.api_key}"}
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "Adapter for 'mystery' not implemented" in response.json()["detail"]


def test_proxy_gemini_key_missing(client, db_session):
    agent = Agent(name="Gemini Config Error")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="gemini"))
    db_session.add(Integration(name="gemini", provider_key="", is_active=True))
    db_session.commit()

    response = client.post("/v1/proxy/gemini", headers={"Authorization": f"Bearer {agent.api_key}"})
    assert response.status_code == 500, f"Expected 500, got {response.status_code}: {response.text}"
    assert "Gemini API Key not configured" in response.json()["detail"]


def test_proxy_success_mock(client, db_session):
    agent = Agent(name="Mock Bot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.add(Integration(name="mock", is_active=True))
    db_session.commit()

    response = client.post(
        "/v1/proxy/mock", headers={"Authorization": f"Bearer {agent.api_key}"}, json={"hi": "there"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["status"] == "success"
    assert db_session.query(AuditLog).filter_by(agent_id=agent.id, response_status=200).count() == 1


@patch("agentauth.core.adapters.GeminiAdapter.forward")
def test_proxy_success_gemini(mock_forward, client, db_session):
    mock_forward.return_value = {"candidates": [], "status": "ok"}

    agent = Agent(name="Gemini Bot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="gemini"))
    db_session.add(Integration(name="gemini", provider_key="actual_key", is_active=True))
    db_session.commit()

    response = client.post(
        "/v1/proxy/gemini",
        headers={"Authorization": f"Bearer {agent.api_key}"},
        json={"input": "text"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["status"] == "ok"


def test_proxy_invalid_json(client, db_session):
    agent = Agent(name="JSON Hater")
    db_session.add(agent)
    db_session.commit()

    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.add(Integration(name="mock", is_active=True))
    db_session.commit()

    # Send a request with invalid JSON body
    response = client.post(
        "/v1/proxy/mock",
        headers={"Authorization": f"Bearer {agent.api_key}", "Content-Type": "application/json"},
        content="{invalid}",
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["echoed_data"] == {}
