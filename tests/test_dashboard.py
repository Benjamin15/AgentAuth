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
    handle_agent_dashboard_logic,
    render_page,
    render_page_logic,
    save_gemini_key,
    save_gemini_key_logic,
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

    res1, id1 = render_page_logic("nav-logs", "nav-logs.n_clicks", None)
    assert "Global Audit Logs" in str(res1)

    res2, id2 = render_page_logic("nav-integrations", "nav-integrations.n_clicks", None)
    assert "Connect Providers" in str(res2)

    res3, id3 = render_page_logic("nav-agents", "nav-agents.n_clicks", None)
    assert "AI Agents" in str(res3)

    # Test dict triggers (Stats/Back)
    res4, id4 = render_page_logic({"type": "stats-btn", "index": 1}, None, None)
    assert id4 == 1

    res5, id5 = render_page_logic({"type": "back-btn", "index": "agents"}, None, 1)
    assert id5 is None
    assert "AI Agents" in str(res5)

    # Test unknown button id
    res6, id6 = render_page_logic("unknown-btn", "unknown-btn.n_clicks", None)
    assert id6 is None
    assert "Analytics Overview" in str(res6)

    # Test unknown dict trigger
    res7, id7 = render_page_logic({"type": "unknown"}, None, None)
    assert "Analytics Overview" in str(res7)

    # Default (no triggered_id)
    res8, id8 = render_page_logic(None, None, None)
    assert "Analytics Overview" in str(res8)


def test_save_gemini_key_logic(db_session):
    with pytest.raises(PreventUpdate):
        save_gemini_key_logic(0, "key")

    res = save_gemini_key_logic(1, "new_secret")
    assert "successfully" in res
    assert db_session.query(Integration).filter_by(name="gemini").one().provider_key == "new_secret"


def test_handle_agent_dashboard_logic_creation(db_session):
    # Missing name
    res, msg = handle_agent_dashboard_logic("create-agent-btn", [], "", "")
    assert "Name is required" in msg

    # Success
    res, msg = handle_agent_dashboard_logic("create-agent-btn", [], "New Bot", "Desc")
    assert "created" in msg
    assert db_session.query(Agent).filter_by(name="New Bot").one()


def test_handle_agent_dashboard_logic_freeze(db_session):
    agent = Agent(name="Ice", is_frozen=False)
    db_session.add(agent)
    db_session.commit()

    handle_agent_dashboard_logic({"type": "freeze-btn", "index": agent.id}, [], None, None)
    db_session.refresh(agent)
    assert agent.is_frozen is True


def test_handle_agent_dashboard_logic_permissions(db_session):
    agent = Agent(name="Perm Bot")
    db_session.add(agent)
    db_session.add(Integration(name="gemini", is_active=True))
    db_session.commit()

    # Grant
    states = [None, None, [{"id": {"type": "perm-dropdown", "index": agent.id}, "value": "gemini"}]]
    handle_agent_dashboard_logic({"type": "grant-btn", "index": agent.id}, states, None, None)
    db_session.refresh(agent)
    assert len(agent.permissions) == 1

    # Revoke
    handle_agent_dashboard_logic(
        {"type": "revoke-perm", "agent": agent.id, "scope": "gemini"}, [], None, None
    )
    db_session.refresh(agent)
    assert len(agent.permissions) == 0


@patch("agentauth.dashboard.app.render_page_logic")
def test_render_page_callback_ctx(mock_logic):
    # Mock dash.callback_context
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = []
        render_page(0, 0, 0, 0, 0, 0, None)
        mock_logic.assert_called_with(None, None, None)

        mock_ctx.triggered = [{"prop_id": "btn.n_clicks"}]
        mock_ctx.triggered_id = "btn"
        render_page(1, 0, 0, 0, 0, 0, None)
        mock_logic.assert_called_with("btn", "btn.n_clicks", None)


def test_save_gemini_key_callback():
    with patch("agentauth.dashboard.app.save_gemini_key_logic") as mock_logic:
        save_gemini_key(1, "key")
        mock_logic.assert_called_once_with(1, "key")


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
