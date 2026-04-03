import dataclasses
import logging
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError

from agentauth.alerting.adapters.log import LogAlertAdapter
from agentauth.alerting.adapters.slack import SlackAlertAdapter
from agentauth.alerting.adapters.webhook import WebhookAlertAdapter
from agentauth.alerting.base import AlertPayload
from agentauth.alerting.engine import get_adapter

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


@pytest.mark.asyncio
async def test_log_adapter_returns_true(caplog):
    adapter = LogAlertAdapter()
    with caplog.at_level(logging.WARNING, logger="agentauth.alerts"):
        result = await adapter.send(_make_payload())
    assert result is True
    assert "Test Bot" in caplog.text


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
