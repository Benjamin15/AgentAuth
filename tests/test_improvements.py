from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agentauth.alerting.base import AlertPayload
from agentauth.alerting.engine import AlertEngine
from agentauth.core.database import Base
from agentauth.core.models import Agent, AlertRule, AuditLog
from agentauth.core.utils import mask_sensitive_data


@pytest.fixture
def db_session():
    """In-memory SQLite for testing logic."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_data_masking():
    """Verify that sensitive keys are masked recursively."""
    data = {
        "api_key": "secret123",
        "user": {
            "name": "Ben",
            "password": "mypassword",
            "nested": {"token": "abc-123"},
        },
        "safe_key": "safe_value",
        "items": [{"key": "val1"}, {"other": "val2"}],
    }
    masked = mask_sensitive_data(data)

    assert masked["api_key"] == "********"
    assert masked["user"]["password"] == "********"
    assert masked["user"]["nested"]["token"] == "********"
    assert masked["safe_key"] == "safe_value"
    assert masked["items"][0]["key"] == "********"
    assert masked["items"][1]["other"] == "val2"


@pytest.mark.asyncio
async def test_alert_engine_sql_sum(db_session):
    """Verify that AlertEngine correctly sums costs via SQL."""
    agent = Agent(name="Test Agent", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()

    # Add 10 logs of $1.0 each
    for _ in range(10):
        log = AuditLog(agent_id=agent.id, target_service="openai", cost_usd=1.0)
        db_session.add(log)
    db_session.commit()

    # Budget alert rule at 5% (should trigger as we spent $10 / $100)
    rule = AlertRule(agent_id=agent.id, threshold_pct=5, channel="log")
    db_session.add(rule)
    db_session.commit()

    with patch("agentauth.alerting.engine.get_adapter") as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.send.return_value = True
        mock_get_adapter.return_value = mock_adapter

        # Evaluate (SQL SUM should find $10.0)
        await AlertEngine.evaluate(int(agent.id), db=db_session)

        # check if adapter was called
        assert mock_adapter.send.called
        payload: AlertPayload = mock_adapter.send.call_args[0][0]
        assert payload.current_spend == 10.0
        assert payload.current_pct == 10.0


@pytest.mark.asyncio
async def test_alert_engine_retry_logic():
    """Verify that _fire retries failed delivery."""
    rule = MagicMock(spec=AlertRule)
    rule.channel = "webhook"
    rule.destination = "http://example.com"
    rule.id = 1

    payload = MagicMock(spec=AlertPayload)
    payload.subject = "Test"
    payload.current_pct = 50.0
    payload.agent_name = "Test"

    mock_adapter = AsyncMock()
    # Fail twice, then succeed
    mock_adapter.send.side_effect = [False, Exception("Net Error"), True]

    db = MagicMock()

    with (
        patch("agentauth.alerting.engine.get_adapter", return_value=mock_adapter),
        patch("asyncio.sleep", return_value=None),
    ):  # Don't wait in tests
        await AlertEngine._fire(rule, payload, 1, db)

        assert mock_adapter.send.call_count == 3
        assert db.add.called
        event = db.add.call_args[0][0]
        assert event.delivered is True
