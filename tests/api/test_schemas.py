import pytest

from agentauth.api.schemas import AgentCreate


def test_agent_create_schema():
    # Valid
    a = AgentCreate(name="Test", description="Desc")
    assert a.name == "Test"

    # Invalid (missing name)
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        AgentCreate(description="No name")  # type: ignore[call-arg]


def test_api_create_agent_missing_name(client):
    response = client.post("/internal/agents", json={"description": "Missing name"})
    assert response.status_code == 422
