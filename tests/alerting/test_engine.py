from datetime import datetime

import pytest

from agentauth.alerting.adapters.log import LogAlertAdapter
from agentauth.alerting.engine import AlertEngine, get_adapter
from agentauth.core.models import Agent, AlertEvent, AlertRule, AuditLog


def test_get_adapter_logic():
    # Valid
    assert isinstance(get_adapter("log", None), LogAlertAdapter)
    # Missing destination for webhook should fallback
    assert isinstance(get_adapter("webhook", None), LogAlertAdapter)


@pytest.mark.asyncio
async def test_engine_fires_at_threshold(db_session):
    agent = Agent(name="TestRuleBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.flush()
    rule = AlertRule(agent_id=agent.id, threshold_pct=80, channel="log")
    db_session.add(rule)
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=85.0, target_service="mock", response_status=200)
    )
    db_session.commit()
    await AlertEngine.evaluate(int(agent.id), db_session)
    events = db_session.query(AlertEvent).all()
    assert len(events) == 1
    assert "Budget alert" in events[0].message


@pytest.mark.asyncio
async def test_engine_deduplication(db_session):
    agent = Agent(name="DedupBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.flush()
    rule = AlertRule(agent_id=agent.id, threshold_pct=80, channel="log")
    db_session.add(rule)
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=85.0, target_service="mock", response_status=200)
    )
    # Add existing event
    db_session.add(
        AlertEvent(
            rule_id=1, agent_id=agent.id, message="Already fired", triggered_at=datetime.now()
        )
    )
    db_session.commit()
    await AlertEngine.evaluate(int(agent.id), db_session)
    # Should still be 1
    assert db_session.query(AlertEvent).count() == 1


@pytest.mark.asyncio
async def test_engine_threshold_not_reached(db_session):
    agent = Agent(name="UnderBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.flush()
    rule = AlertRule(agent_id=agent.id, threshold_pct=80, channel="log")
    db_session.add(rule)
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=50.0, target_service="mock", response_status=200)
    )
    db_session.commit()
    await AlertEngine.evaluate(int(agent.id), db_session)
    assert db_session.query(AlertEvent).count() == 0


@pytest.mark.asyncio
async def test_engine_global_rule(db_session):
    agent = Agent(name="GlobalRuleBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.flush()
    # Rule with agent_id=None is global
    rule = AlertRule(agent_id=None, threshold_pct=80, channel="log")
    db_session.add(rule)
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=85.0, target_service="mock", response_status=200)
    )
    db_session.commit()
    await AlertEngine.evaluate(int(agent.id), db_session)
    assert db_session.query(AlertEvent).count() == 1


@pytest.mark.asyncio
async def test_engine_agent_not_found(db_session):
    # Should just return gracefully
    await AlertEngine.evaluate(999, db_session)


@pytest.mark.asyncio
async def test_engine_no_budget_no_alert(db_session):
    agent = Agent(name="NoBudgetBot", monthly_budget_usd=None)
    db_session.add(agent)
    db_session.commit()
    await AlertEngine.evaluate(int(agent.id), db_session)
    assert db_session.query(AlertEvent).count() == 0
