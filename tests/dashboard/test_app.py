import json
from unittest.mock import patch

import dash

from agentauth.core.models import Agent, AuditLog, Integration
from agentauth.dashboard.app import (
    add_or_update_model_pricing,
    handle_agent_dashboard_logic,
    handle_registration_submit,
    inspect_json,
    render_page_logic,
    save_alert_rule,
    save_integration_key,
    serve_layout,
    toggle_registration_drawer,
    update_active_integration,
)


def test_handle_registration_submit_logic_unit(db_session):
    res_ok = handle_registration_submit(1, "Callback Bot", "Test", 500, ["openai"])
    assert res_ok[1] == ""
    assert db_session.query(Agent).filter_by(name="Callback Bot").count() == 1
    res_err = handle_registration_submit(1, "", "Desc", 100, ["openai"])
    assert res_err[0] == dash.no_update
    assert "agent name is required" in res_err[1].lower()


def test_toggle_registration_drawer_unit():
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "open-register-agent"}]
        mock_ctx.triggered_id = "open-register-agent"
        res = toggle_registration_drawer(1, 0, 0, 0, "side-drawer", "")
        # Toggle returns (class, class, name, desc, budget, scopes)
        assert "open" in res[0]

        mock_ctx.triggered = [{"prop_id": "close-registration-drawer"}]
        mock_ctx.triggered_id = "close-registration-drawer"
        res_close = toggle_registration_drawer(0, 1, 0, 0, "side-drawer open", "")
        assert "open" not in res_close[0]


def test_handle_agent_dashboard_logic_branches(db_session):
    agent = Agent(name="HandleBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()
    handle_agent_dashboard_logic({"type": "freeze-btn", "index": agent.id}, [], None, None)
    db_session.refresh(agent)
    assert agent.is_frozen is True
    states_budget = [None, None, None, [{"id": {"index": agent.id}, "value": 200}]]
    handle_agent_dashboard_logic(
        {"type": "set-budget-btn", "index": agent.id}, states_budget, None, None
    )
    db_session.refresh(agent)
    assert agent.monthly_budget_usd == 200.0
    handle_agent_dashboard_logic({"type": "delete-btn", "index": agent.id}, [], None, None)
    db_session.expire_all()
    assert db_session.get(Agent, agent.id) is None


def test_render_page_logic_fallback():
    with patch("agentauth.dashboard.app.page_registry.get") as mock_get:
        mock_get.return_value = None
        res, aid = render_page_logic({"type": "nav-link", "index": "missing"}, "", None, "24h")
        assert res is not None


def test_update_active_integration_logic(db_session):
    db_session.merge(Integration(name="openai", is_active=True, provider_key="key"))
    db_session.commit()
    with patch("dash.callback_context") as mock_ctx:
        # Dash pattern-match IDs are JSON strings in prop_id
        triggered_id = {"type": "integration-sidebar-item", "name": "openai"}
        mock_ctx.triggered = [{"prop_id": json.dumps(triggered_id) + ".n_clicks"}]
        res = update_active_integration(1, [triggered_id], [{"backgroundColor": "transparent"}])
        assert res is not None


def test_add_or_update_model_pricing_logic(db_session):
    res = add_or_update_model_pricing(1, "gpt-new", 10.0, 20.0)
    assert "added" in str(res).lower()
    res2 = add_or_update_model_pricing(1, "gpt-new", 11.0, 22.0)
    assert "updated" in str(res2).lower()


def test_save_alert_rule_logic(db_session):
    agent = Agent(name="AlertMeBot")
    db_session.add(agent)
    db_session.commit()
    res = save_alert_rule(1, str(agent.id), 80, "log", None)
    assert "rule saved" in str(res).lower()


def test_save_integration_key_logic(db_session):
    res = save_integration_key(1, "sk-valid-key", "openai")
    assert "saved" in str(res).lower()
    db_session.expire_all()
    integration = db_session.query(Integration).filter_by(name="openai").first()
    assert integration is not None
    assert integration.provider_key == "sk-valid-key"


def test_serve_layout():
    layout = serve_layout()
    assert layout is not None
    assert "AgentAuth" in str(layout)


def test_inspect_json_logic(db_session):
    agent = Agent(name="LogBot")
    db_session.add(agent)
    db_session.flush()
    db_session.add(
        AuditLog(agent_id=agent.id, request_details='{"test": 123}', response_status=200)
    )
    db_session.commit()
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": '{"index":0,"type":"inspect-row"}.n_clicks'}]
        mock_ctx.triggered_id = {"type": "inspect-row", "index": 0}
        style, contents = inspect_json([1], agent.id)
        assert style["display"] == "block"
        assert "123" in str(contents)
