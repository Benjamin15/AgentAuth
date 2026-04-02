from datetime import datetime
from unittest.mock import patch

import pytest
from dash.exceptions import PreventUpdate

from agentauth.core.models import Agent, AuditLog, Integration
from agentauth.dashboard.app import (
    get_agent_stats_view,
    get_agents_view,
    get_dashboard_view,
    get_integrations_view,
    get_logs_view,
    get_sidebar,
    handle_agent_dashboard,
    render_page,
    render_page_logic,
)


def test_get_sidebar():
    sidebar = get_sidebar()
    assert sidebar is not None
    assert "AgentAuth" in str(sidebar)


def test_get_dashboard_view_no_data(db_session):
    view = get_dashboard_view()
    assert "No data available yet" in str(view)


def test_get_dashboard_view_with_data(db_session):
    agent = Agent(name="Tester")
    db_session.add(agent)
    db_session.commit()
    log = AuditLog(
        agent_id=agent.id, target_service="mock", response_status=200, timestamp=datetime.now()
    )
    db_session.add(log)
    db_session.commit()

    view = get_dashboard_view()
    assert "Analytics Overview" in str(view)
    assert "1" in str(view)  # Total requests count


def test_get_agents_view(db_session):
    db_session.add(Agent(name="Agent 1", is_frozen=True))
    db_session.add(Integration(name="gemini", is_active=True))
    db_session.commit()

    view = get_agents_view()
    assert "AI Agents" in str(view)
    assert "Agent 1" in str(view)
    assert "(FROZEN)" in str(view)


def test_get_agent_stats_view_not_found(db_session):
    view = get_agent_stats_view(999)
    assert "Agent not found" in str(view)


def test_get_agent_stats_view_no_logs(db_session):
    agent = Agent(name="Silent Agent")
    db_session.add(agent)
    db_session.commit()
    view = get_agent_stats_view(agent.id)
    assert "No audit logs available" in str(view)


def test_get_agent_stats_view_with_logs(db_session):
    agent = Agent(name="Chatty Agent")
    db_session.add(agent)
    db_session.commit()
    db_session.add(
        AuditLog(
            agent_id=agent.id, target_service="mock", response_status=200, timestamp=datetime.now()
        )
    )
    db_session.commit()

    view = get_agent_stats_view(agent.id)
    assert "Analytics for Chatty Agent" in str(view)
    assert "Total Hits" in str(view)


def test_get_logs_view(db_session):
    agent = Agent(name="Logger")
    db_session.add(agent)
    db_session.commit()
    db_session.add(
        AuditLog(
            agent_id=agent.id, target_service="test", response_status=200, timestamp=datetime.now()
        )
    )
    db_session.commit()

    view = get_logs_view()
    assert "Global Audit Logs" in str(view)
    assert "test" in str(view)


def test_get_integrations_view(db_session):
    db_session.add(Integration(name="gemini", provider_key="abc"))
    db_session.commit()
    view = get_integrations_view()
    assert "Connect Providers" in str(view)
    assert "abc" in str(view)


def test_render_page_logic(db_session):
    # Add data so we get Analytics Overview
    agent = Agent(name="NavBot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(
        AuditLog(
            agent_id=agent.id, target_service="mock", response_status=200, timestamp=datetime.now()
        )
    )
    db_session.commit()

    res1, id1 = render_page_logic("nav-logs", "nav-logs.n_clicks", None, "24h")
    assert "Global Audit Logs" in str(res1)

    res2, id2 = render_page_logic("nav-integrations", "nav-integrations.n_clicks", None, "24h")
    assert "Connect Providers" in str(res2)

    res3, id3 = render_page_logic("nav-agents", "nav-agents.n_clicks", None, "24h")
    assert "AI Agents" in str(res3)

    # Test dict triggers (Stats/Back)
    res4, id4 = render_page_logic({"type": "stats-btn", "index": 1}, None, None, "24h")
    assert id4 == 1

    res5, id5 = render_page_logic({"type": "back-btn", "index": "agents"}, None, 1, "24h")
    assert id5 is None
    assert "AI Agents" in str(res5)

    # Test unknown button id
    res6, id6 = render_page_logic("unknown-btn", "unknown-btn.n_clicks", None, "24h")
    assert id6 is None

    # Test unknown dict trigger
    res7, id7 = render_page_logic({"type": "unknown"}, None, None, "24h")
    assert "AI Observability Dashboard" in str(res7)

    # Default (no triggered_id)
    res8, id8 = render_page_logic(None, None, None, "24h")
    assert "AI Observability Dashboard" in str(res8)


@patch("agentauth.dashboard.app.render_page_logic")
def test_render_page_callback_ctx(mock_logic):
    # Mock dash.callback_context
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = []
        render_page(0, 0, 0, 0, 0, 0, 0, None)
        mock_logic.assert_called_with(None, None, None, None)

        mock_ctx.triggered = [{"prop_id": "btn.n_clicks"}]
        mock_ctx.triggered_id = "btn"
        render_page(1, 0, 0, 0, 0, 0, 0, None)
        mock_logic.assert_called_with("btn", "btn.n_clicks", None, None)


@patch("agentauth.dashboard.app.handle_agent_dashboard_logic")
def test_handle_agent_dashboard_callback(mock_logic):
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = []
        with pytest.raises(PreventUpdate):
            handle_agent_dashboard(0, 0, 0, 0, "name", "desc", [])

        mock_ctx.triggered = [1]
        mock_ctx.triggered_id = "id"
        mock_ctx.states_list = "states"
        handle_agent_dashboard(1, 0, 0, 0, "name", "desc", [])
        mock_logic.assert_called_with("id", "states", "name", "desc")


def test_auth_login_get(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "AgentAuth" in response.text

    # Check error param rendering
    response_err = client.get("/login?error=Bad")
    assert "div class='error'>Bad</div>" in response_err.text


def test_auth_login_post(client, db_session):
    from agentauth.core.models import AdminUser
    from agentauth.core.security import get_password_hash

    # Create test admin
    admin = AdminUser(username="testadmin", hashed_password=get_password_hash("testpass"))
    db_session.add(admin)
    db_session.commit()

    # Success
    response = client.post(
        "/login", data={"username": "testadmin", "password": "testpass"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/"
    assert "access_token" in response.headers.get("set-cookie", "")

    # Failure
    response2 = client.post(
        "/login", data={"username": "testadmin", "password": "wrong"}, follow_redirects=False
    )
    assert response2.status_code == 303
    assert "error=Invalid+credentials" in response2.headers["location"]


def test_auth_logout(client):
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_dashboard_middleware_blocks_unauthenticated(client):
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_dashboard_middleware_allows_authenticated(client, db_session):
    from agentauth.core.models import AdminUser
    from agentauth.core.security import get_password_hash

    admin = AdminUser(username="testadmin2", hashed_password=get_password_hash("testpass"))
    db_session.add(admin)
    db_session.commit()

    # Log in
    client.post("/login", data={"username": "testadmin2", "password": "testpass"})

    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code != 303


def test_dashboard_middleware_invalid_jwt(client):
    # Set a cookie with an invalid/malformed JWT
    client.cookies.set("access_token", "Bearer invalid-jwt-here")
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
