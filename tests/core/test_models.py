from datetime import datetime

from agentauth.core.models import (
    AdminUser,
    Agent,
    AgentPermission,
    AgentToken,
    AlertRule,
    AuditLog,
    Integration,
    ModelPricing,
)


def test_models_creation(db_session):
    agent = Agent(name="Test")
    db_session.add(agent)
    db_session.commit()
    assert agent.id is not None
    assert "aa_client_" in agent.client_id


def test_audit_log_repr():
    log = AuditLog(id=1, target_service="openai", response_status=200)
    assert log is not None


def test_model_pricing_creation(db_session):
    m = ModelPricing(model_name="m1", input_1m_price=1.0)
    db_session.add(m)
    db_session.commit()
    assert m.model_name == "m1"


def test_admin_user_creation(db_session):
    u = AdminUser(username="admin", hashed_password="pwd")
    db_session.add(u)
    db_session.commit()
    assert u.username == "admin"


def test_agent_permission_creation(db_session):
    a = Agent(name="PermBot")
    db_session.add(a)
    db_session.flush()
    p = AgentPermission(agent_id=a.id, scope="openai")
    db_session.add(p)
    db_session.commit()
    assert p.scope == "openai"


def test_agent_token_creation(db_session):
    a = Agent(name="TokenBot")
    db_session.add(a)
    db_session.flush()
    t = AgentToken(agent_id=a.id, access_token="t1", expires_at=datetime.now())
    db_session.add(t)
    db_session.commit()
    assert t.access_token == "t1"


def test_integration_creation(db_session):
    i = Integration(name="int1", provider_key="key")
    db_session.add(i)
    db_session.commit()
    assert i.name == "int1"


def test_alert_rule_creation(db_session):
    r = AlertRule(threshold_pct=80, channel="log")
    db_session.add(r)
    db_session.commit()
    assert r.threshold_pct == 80
