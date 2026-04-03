from agentauth.core.models import Agent, ModelPricing
from agentauth.dashboard.pages import page_registry


def test_page_registry_discovery():
    page_registry.discover("agentauth.dashboard.pages")
    assert "dashboard" in page_registry.list_all()
    assert "agents" in page_registry.list_all()


def test_dashboard_page_rendering(db_session):
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("dashboard")
    assert page_cls is not None
    view = page_cls().render()
    assert "Observability Dashboard" in str(view)


def test_agents_page_rendering(db_session):
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("agents")
    assert page_cls is not None
    # List view
    view_list = page_cls().render()
    assert "AI Agents Registry" in str(view_list)

    # Stats view
    agent = Agent(name="StatsBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()
    view_stats = page_cls().render(active_agent_id=str(agent.id))
    assert "Deep Inspection" in str(view_stats)


def test_agent_stats_no_data(db_session):
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("agents")
    assert page_cls is not None
    agent = Agent(name="NoDataBot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()
    view = page_cls().render(active_agent_id=str(agent.id))
    assert "No data" in str(view)


def test_alerts_page_rendering(db_session):
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("alerts")
    assert page_cls is not None
    view = page_cls().render()
    assert "Real-time Alerting" in str(view)


def test_integrations_page_rendering(db_session):
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("integrations")
    assert page_cls is not None
    view = page_cls().render()
    assert "Services' Sidebar" in str(view)


def test_logs_page_rendering(db_session):
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("logs")
    assert page_cls is not None
    view = page_cls().render()
    assert "Global Audit Logs" in str(view)


def test_models_page_rendering(db_session):
    db_session.add(ModelPricing(model_name="zzz-bot", input_1m_price=1.0, output_1m_price=1.0))
    db_session.commit()
    page_registry.discover("agentauth.dashboard.pages")
    page_cls = page_registry.get("models")
    assert page_cls is not None
    view = page_cls().render()
    assert "Pricing" in str(view) or "Model" in str(view)
    assert "zzz-bot" in str(view)
