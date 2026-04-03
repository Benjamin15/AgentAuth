"""Tests for the alerting subsystem.

Covers:
- ``AlertPayload`` properties.
- Each adapter in isolation (mocked HTTP / logger).
- ``get_adapter`` factory.
- ``AlertEngine`` end-to-end with an in-memory database.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
import dataclasses
import logging
from unittest.mock import MagicMock, patch

import pytest

from agentauth.alerting.adapters.log import LogAlertAdapter
from agentauth.alerting.adapters.slack import SlackAlertAdapter
from agentauth.alerting.adapters.webhook import WebhookAlertAdapter
from agentauth.alerting.base import AlertPayload
from agentauth.alerting.engine import AlertEngine, get_adapter
from agentauth.core.models import Agent, AlertEvent, AlertRule, AuditLog

# A fully-typed default payload; tests can override fields via dataclasses.replace().
_DEFAULT_PAYLOAD = AlertPayload(
    agent_id=1,
    agent_name="Test Bot",
    threshold_pct=80,
    current_pct=85.0,
    current_spend=42.5,
    budget_usd=50.0,
    rule_id=1,
)


def _make_payload(**kwargs: object) -> AlertPayload:
    """Return a copy of the default ``AlertPayload`` with overridden fields."""
    return dataclasses.replace(_DEFAULT_PAYLOAD, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AlertPayload
# ---------------------------------------------------------------------------


def test_payload_subject():
    p = _make_payload()
    assert "Test Bot" in p.subject
    assert "80%" in p.subject
    assert "$42.50" in p.subject


def test_payload_body():
    p = _make_payload()
    assert "42.5" in p.body
    assert "$50.00" in p.body
    assert "threshold 80%" in p.body


# ---------------------------------------------------------------------------
# LogAlertAdapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_adapter_returns_true(caplog):
    adapter = LogAlertAdapter()
    with caplog.at_level(logging.WARNING, logger="agentauth.alerts"):
        result = await adapter.send(_make_payload())
    assert result is True
    assert "Test Bot" in caplog.text


# ---------------------------------------------------------------------------
# WebhookAlertAdapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_adapter_success():
    adapter = WebhookAlertAdapter(url="https://example.com/hook")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch(
        "agentauth.alerting.adapters.webhook.requests.post", return_value=mock_resp
    ) as mock_post:
        result = await adapter.send(_make_payload())
    assert result is True
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["event"] == "budget_alert"
    assert kwargs["json"]["agent_name"] == "Test Bot"


@pytest.mark.asyncio
async def test_webhook_adapter_failure():
    adapter = WebhookAlertAdapter(url="https://example.com/hook")
    with patch(
        "agentauth.alerting.adapters.webhook.requests.post", side_effect=ConnectionError("down")
    ):
        result = await adapter.send(_make_payload())
    assert result is False


# ---------------------------------------------------------------------------
# SlackAlertAdapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slack_adapter_success():
    adapter = SlackAlertAdapter(webhook_url="https://hooks.slack.com/services/test")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch(
        "agentauth.alerting.adapters.slack.requests.post", return_value=mock_resp
    ) as mock_post:
        result = await adapter.send(_make_payload())
    assert result is True
    _, kwargs = mock_post.call_args
    assert "blocks" in kwargs["json"]


@pytest.mark.asyncio
async def test_slack_adapter_failure():
    adapter = SlackAlertAdapter(webhook_url="https://hooks.slack.com/services/test")
    with patch(
        "agentauth.alerting.adapters.slack.requests.post", side_effect=ConnectionError("down")
    ):
        result = await adapter.send(_make_payload())
    assert result is False


# ---------------------------------------------------------------------------
# get_adapter factory
# ---------------------------------------------------------------------------


def test_get_adapter_log():
    a = get_adapter("log", None)
    assert isinstance(a, LogAlertAdapter)


def test_get_adapter_webhook():
    a = get_adapter("webhook", "https://example.com")
    assert isinstance(a, WebhookAlertAdapter)


def test_get_adapter_slack():
    a = get_adapter("slack", "https://hooks.slack.com/services/x")
    assert isinstance(a, SlackAlertAdapter)


def test_get_adapter_fallback_on_missing_destination():
    """Webhook / Slack without a destination should fall back to Log."""
    a = get_adapter("webhook", None)
    assert isinstance(a, LogAlertAdapter)


def test_get_adapter_unknown_channel():
    a = get_adapter("carrier_pigeon", None)
    assert isinstance(a, LogAlertAdapter)


# ---------------------------------------------------------------------------
# AlertEngine — end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_no_budget(db_session):
    """Agents without a budget should generate no events."""
    agent = Agent(name="NoBudget")
    db_session.add(agent)
    db_session.commit()

    await AlertEngine.evaluate(int(agent.id), db_session)
    assert db_session.query(AlertEvent).count() == 0


@pytest.mark.asyncio
async def test_engine_below_threshold(db_session):
    """Agents spending less than their threshold should not trigger an alert."""
    agent = Agent(name="UnderBudget", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()

    db_session.add(AlertRule(agent_id=agent.id, threshold_pct=80, channel="log"))
    db_session.add(
        AuditLog(agent_id=agent.id, target_service="mock", response_status=200, cost_usd=50.0)
    )
    db_session.commit()

    await AlertEngine.evaluate(int(agent.id), db_session)
    assert db_session.query(AlertEvent).count() == 0


@pytest.mark.asyncio
async def test_engine_fires_at_threshold(db_session):
    """Engine should create an AlertEvent when spend crosses the threshold."""
    agent = Agent(name="OverBudget", monthly_budget_usd=50.0)
    db_session.add(agent)
    db_session.commit()

    db_session.add(AlertRule(agent_id=agent.id, threshold_pct=80, channel="log"))
    # Spend = $45 = 90 % of $50 budget → threshold 80 % crossed
    db_session.add(
        AuditLog(agent_id=agent.id, target_service="mock", response_status=200, cost_usd=45.0)
    )
    db_session.commit()

    with patch(
        "agentauth.alerting.adapters.log.LogAlertAdapter.send", return_value=True
    ) as mock_send:
        await AlertEngine.evaluate(int(agent.id), db_session)
        mock_send.assert_called_once()

    events = db_session.query(AlertEvent).all()
    assert len(events) == 1
    assert events[0].delivered is True
    assert events[0].agent_id == agent.id


@pytest.mark.asyncio
async def test_engine_deduplicates_within_month(db_session):
    """An alert should only fire once per calendar month per rule."""
    import datetime

    agent = Agent(name="RepeatedAlert", monthly_budget_usd=50.0)
    db_session.add(agent)
    db_session.commit()

    rule = AlertRule(agent_id=agent.id, threshold_pct=80, channel="log")
    db_session.add(rule)
    db_session.add(
        AuditLog(agent_id=agent.id, target_service="mock", response_status=200, cost_usd=45.0)
    )
    db_session.commit()

    # Seed an existing event this month
    existing = AlertEvent(
        rule_id=rule.id,
        agent_id=agent.id,
        triggered_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        current_pct=90.0,
        message="Already fired",
        delivered=True,
    )
    db_session.add(existing)
    db_session.commit()

    with patch("agentauth.alerting.adapters.log.LogAlertAdapter.send") as mock_send:
        await AlertEngine.evaluate(int(agent.id), db_session)
        mock_send.assert_not_called()

    assert db_session.query(AlertEvent).count() == 1  # No new event created


@pytest.mark.asyncio
async def test_engine_global_rule_applies_to_all_agents(db_session):
    """A global rule (agent_id=None) should fire for any agent over threshold."""
    agent = Agent(name="GlobalTarget", monthly_budget_usd=10.0)
    db_session.add(agent)
    db_session.commit()

    db_session.add(AlertRule(agent_id=None, threshold_pct=80, channel="log"))
    db_session.add(
        AuditLog(agent_id=agent.id, target_service="mock", response_status=200, cost_usd=9.0)
    )
    db_session.commit()

    with patch("agentauth.alerting.adapters.log.LogAlertAdapter.send", return_value=True):
        await AlertEngine.evaluate(int(agent.id), db_session)

    assert db_session.query(AlertEvent).count() == 1


@pytest.mark.asyncio
async def test_engine_evaluate_catches_exception(caplog, db_session):
    agent = Agent(name="FailBot", monthly_budget_usd=10.0)
    db_session.add(agent)
    db_session.commit()
    with patch("agentauth.alerting.engine.AlertEngine._run", side_effect=ValueError("Test error")):
        with caplog.at_level(logging.ERROR, logger="agentauth.alerts"):
            await AlertEngine.evaluate(int(agent.id), db_session)
    assert "Unexpected error during evaluation" in caplog.text


@pytest.mark.asyncio
async def test_engine_returns_early_no_rules_for_agent(db_session):
    agent = Agent(name="NoRules", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()
    db_session.add(
        AuditLog(agent_id=agent.id, target_service="test", response_status=200, cost_usd=90.0)
    )
    db_session.commit()

    # No AlertRule added!
    with patch("agentauth.alerting.engine.asyncio.gather") as mock_gather:
        await AlertEngine.evaluate(int(agent.id), db_session)
        mock_gather.assert_not_called()
