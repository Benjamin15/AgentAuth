import importlib
import os
from unittest.mock import patch

import dash
import pytest

from agentauth.alerting.base import AlertPayload
from agentauth.alerting.engine import AlertEngine, get_adapter
from agentauth.alerting.log import LogAlertAdapter
from agentauth.alerting.slack import SlackAlertAdapter
from agentauth.alerting.webhook import WebhookAlertAdapter
from agentauth.core.adapters import GeminiAdapter
from agentauth.core.database import SessionLocal
from agentauth.core.models import (
    Agent,
    AgentPermission,
    AlertEvent,
    AlertRule,
    AuditLog,
    Integration,
)
from agentauth.dashboard.app import (
    get_agents_view,
    get_dashboard_view,
    get_time_delta,
    handle_agent_dashboard_logic,
    inspect_json,
    toggle_registration_drawer,
    update_active_integration,
)

# --- Dashboard & Utils Coverage ---


def test_get_time_delta_coverage():
    # Line 29
    assert get_time_delta("1h") is not None
    # Lines 32-34
    assert get_time_delta("7d") is not None
    assert get_time_delta("unknown") is None


def test_dashboard_view_with_spend(db_session):
    # Lines 406-415: Spend bar chart
    # Ensure numerical comparisons work by avoiding None
    agent = Agent(name="Rich Bot", monthly_budget_usd=1000.0)
    db_session.add(agent)
    db_session.commit()
    db_session.add(
        AuditLog(
            agent_id=agent.id,
            cost_usd=100.0,
            total_tokens=1000,
            target_service="mock",
            response_status=200,
        )
    )
    db_session.commit()
    view = get_dashboard_view("24h")
    assert "Rich Bot" in str(view)


def test_agents_view_model_tags_coverage(db_session):
    # Lines 705-706: "Limited" status (reached budget)
    # Lines 709-711: Model tags
    agent = Agent(name="Model Bot", monthly_budget_usd=10.0)  # non-zero budget
    db_session.add(agent)
    db_session.commit()
    # Add audit log with model name AND latency AND 40M tokens (to hit Limited: 40M * 0.0000003 = 12 USD > 10 USD budget)
    db_session.add(
        AuditLog(
            agent_id=agent.id,
            cost_usd=10.0,
            target_service="gemini",
            response_status=200,
            total_tokens=40000000,
            request_details='{"model":"gemini-pro"}',
            latency_ms=150,
        )
    )
    db_session.commit()
    view = get_agents_view()
    assert "Limited" in str(view)
    assert "Model Bot" in str(view)


def test_handle_agent_dashboard_old_logic_coverage(db_session):
    # Lines 1915-1917: Old create agent empty name (already covered)
    res_err, msg_err = handle_agent_dashboard_logic("create-agent-btn", [], None, None)
    assert "Name is required" in msg_err

    # Lines 1918-1921: Success branch (Line 1918 onwards)
    res_ok, msg_ok = handle_agent_dashboard_logic("create-agent-btn", [], "Old Style Bot", "Legacy")
    assert "created!" in msg_ok
    assert db_session.query(Agent).filter_by(name="Old Style Bot").count() == 1


def test_inspect_json_early_exits_coverage():
    # Line 2008 & 2022
    with patch("dash.callback_context") as mock_ctx:
        # Trigger is None
        mock_ctx.triggered = []
        with pytest.raises(dash.exceptions.PreventUpdate):
            inspect_json([], 1)

        # Index out of bounds
        mock_ctx.triggered = [{"prop_id": '{"type":"inspect-row","index":99}.n_clicks'}]
        mock_ctx.triggered_id = {"type": "inspect-row", "index": 99}
        res = inspect_json([1], 1)
        assert res[0]["display"] == "none"


def test_update_active_integration_early_exit_coverage():
    # Line 2142
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = []
        with pytest.raises(dash.exceptions.PreventUpdate):
            update_active_integration([], [], [])


def test_toggle_registration_drawer_early_exit_coverage():
    # Line 2891
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = []
        with pytest.raises(dash.exceptions.PreventUpdate):
            toggle_registration_drawer(0, 0, 0, 0, "", "")


# --- Alerting Coverage ---


def test_alert_payload_props():
    payload = AlertPayload(
        agent_id=1,
        agent_name="Bot",
        threshold_pct=80,
        current_pct=85.0,
        current_spend=85.0,
        budget_usd=100.0,
        rule_id=1,
    )
    assert "Bot reached 80%" in payload.subject
    assert "consumed 85.0%" in payload.body


@pytest.mark.asyncio
async def test_alert_engine_complete_coverage(db_session):
    # Missing: evaluate error handling, threshold eval, fire-and-forget logic
    agent = Agent(name="Alert Bot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()

    # 1. Test get_adapter branches (Line 42-51)
    assert isinstance(get_adapter("webhook", "http://hooks.com"), WebhookAlertAdapter)
    assert isinstance(get_adapter("slack", "http://slack.com"), SlackAlertAdapter)
    assert isinstance(get_adapter("unknown", None), LogAlertAdapter)

    # 2. Test Evaluate with spend (Lines 93-151)
    rule = AlertRule(agent_id=agent.id, threshold_pct=80, channel="log", is_active=True)
    db_session.add(rule)
    db_session.add(AuditLog(agent_id=agent.id, cost_usd=90.0, target_service="mock"))
    db_session.commit()

    # Run evaluation
    await AlertEngine.evaluate(agent, db_session)

    # Verify AlertEvent created (Line 172-180)
    event = db_session.query(AlertEvent).filter_by(agent_id=agent.id).first()
    assert event is not None
    assert event.delivered is True

    # 3. Test Deduplication (Line 136-137)
    # Running again should NOT create a new event
    await AlertEngine.evaluate(agent, db_session)
    assert db_session.query(AlertEvent).filter_by(agent_id=agent.id).count() == 1


@pytest.mark.asyncio
@patch("requests.post")
async def test_alert_adapters_sending_coverage(mock_post):
    payload = AlertPayload(1, "Bot", 80, 85, 85, 100, 1)

    # Slack Success
    mock_post.return_value.status_code = 200
    slack = SlackAlertAdapter(webhook_url="http://slack")
    assert await slack.send(payload) is True

    # Webhook Fail (Lines 112-114 in slack/webhook)
    mock_post.side_effect = Exception("Network Down")
    assert await slack.send(payload) is False

    webhook = WebhookAlertAdapter(url="http://webhook")
    assert await webhook.send(payload) is False


# --- Core Adapters & Master Key ---


@pytest.mark.asyncio
@patch("requests.post")
async def test_gemini_adapter_coverage(mock_post):
    adapter = GeminiAdapter(api_key="test-key")

    # Success (Lines 61-71)
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15}
    }
    res = await adapter.forward({"input": "hi"})
    assert res["usage"]["total"] == 15

    # Non-200 (Lines 58-59)
    mock_post.return_value.status_code = 403
    mock_post.return_value.text = "Forbidden"
    res_err = await adapter.forward({})
    assert res_err["status"] == "error"


@pytest.mark.asyncio
async def test_proxy_decryption_failure_coverage(db_session, client):
    # Line 147 in router.py
    agent = Agent(name="Decrypt Fail Bot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="gemini"))
    db_session.add(Integration(name="gemini", provider_key="encrypted", is_active=True))
    db_session.commit()

    from .conftest import get_token

    token = get_token(client, agent)

    with patch("agentauth.api.router.decrypt_secret", return_value=None):
        response = client.post("/v1/proxy/gemini", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 500
        assert "Failed to decrypt" in response.json()["detail"]


def test_security_master_key_env_coverage():
    # Line 17: AGENTAUTH_MASTER_KEY in env
    from cryptography.fernet import Fernet

    valid_key = Fernet.generate_key().decode()

    import agentauth.core.security as security

    with patch.dict(os.environ, {"AGENTAUTH_MASTER_KEY": valid_key}):
        importlib.reload(security)
        assert security._fernet_key == valid_key.encode()

    # Restore for other tests
    importlib.reload(security)


def test_database_session_logic_coverage():
    # Lines 14-18: Initializer logic
    # Just ensure SessionLocal can be called and creates a session
    session = SessionLocal()
    assert session is not None
    session.close()


# --- Main Coverage ---


def test_main_init_coverage():
    # Line 48 in main.py
    from agentauth.main import app as fastapi_app

    assert "AgentAuth" in fastapi_app.title
