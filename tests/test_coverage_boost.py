from unittest.mock import MagicMock, patch

import dash
import pytest
from dash import html

from agentauth.api.router import auth_cache
from agentauth.core.models import (
    Agent,
    AgentPermission,
    AuditLog,
    Integration,
    ModelPricing,
)
from agentauth.core.security import decrypt_secret, encrypt_secret
from agentauth.dashboard.app import (
    add_or_update_model_pricing,
    get_agents_view,
    get_inventory_view,
    handle_agent_dashboard_logic,
    handle_registration_submit,
    inspect_json,
    render_integration_pane,
    render_page_logic,
    save_integration_key,
    toggle_registration_drawer,
    update_active_integration,
)

from .conftest import get_token

# --- API Coverage Boost ---


def test_proxy_cache_hit(client, db_session):
    agent = Agent(name="Cache Bot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.add(Integration(name="mock", is_active=True))
    db_session.commit()

    token = get_token(client, agent)
    headers = {"Authorization": f"Bearer {token}"}

    # First call (Cache Miss)
    auth_cache.clear()
    res1 = client.post("/v1/proxy/mock", headers=headers, json={"test": 1})
    assert res1.status_code == 200

    # Second call (Cache Hit - Line 44)
    res2 = client.post("/v1/proxy/mock", headers=headers, json={"test": 2})
    assert res2.status_code == 200


def test_proxy_agent_deleted_mid_flight(client, db_session):
    # To hit Line 100, we need the token to be in Cache (so step 1 succeeds)
    # but the agent to be missing from DB (so step 98-100 fails).
    agent = Agent(name="Gone Bot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.add(Integration(name="mock", is_active=True))
    db_session.commit()

    token = get_token(client, agent)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Populate cache
    client.post("/v1/proxy/mock", headers=headers)
    assert (token, "mock") in auth_cache

    # 2. Delete agent from DB
    db_session.delete(agent)
    db_session.commit()

    # 3. Call again - hits cache but agent is missing from DB (Line 100)
    response = client.post("/v1/proxy/mock", headers=headers)
    assert response.status_code == 401
    assert "Agent not found" in response.json()["detail"]


def test_proxy_quota_exceeded(client, db_session):
    agent = Agent(name="Broke Bot", monthly_budget_usd=10.0)
    db_session.add(agent)
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.add(Integration(name="mock", is_active=True))
    # Add usage that exceeds $10
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=15.0, target_service="mock", response_status=200)
    )
    db_session.commit()

    token = get_token(client, agent)

    response = client.post("/v1/proxy/mock", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 402
    assert "budget" in response.json()["detail"]


@patch("agentauth.core.adapters.MockAdapter.forward")
def test_proxy_token_summation_and_cost(mock_forward, client, db_session):
    # Case: Prompt + Completion present, but Total is None (Line 174)
    # Case: Pricing exists (Lines 182-184)
    mock_forward.return_value = {
        "status": "success",
        "model_name": "gpt-4-test",
        "usage": {"prompt": 100, "completion": 50, "total": None},
    }

    agent = Agent(name="Math Bot")
    db_session.add(agent)
    db_session.add(ModelPricing(model_name="gpt-4-test", input_1m_price=10.0, output_1m_price=30.0))
    db_session.add(Integration(name="mock", is_active=True))
    db_session.commit()
    db_session.add(AgentPermission(agent_id=agent.id, scope="mock"))
    db_session.commit()

    token = get_token(client, agent)

    response = client.post("/v1/proxy/mock", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    log = db_session.query(AuditLog).filter_by(agent_id=agent.id).first()
    assert log.total_tokens == 150  # 100 + 50
    assert log.cost_usd > 0
    # (100 * 10/1M) + (50 * 30/1M) = 0.001 + 0.0015 = 0.0025
    assert float(log.cost_usd) == pytest.approx(0.0025)


# --- Dashboard Coverage Boost ---


def test_get_agents_view_error_handling(db_session):
    # Trigger Exception in get_agents_view (Lines 687-688)
    with patch("agentauth.dashboard.app.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB Failure")
        mock_session.return_value = mock_db

        view = get_agents_view()
        assert "Registry Data Error" in str(view)


def test_get_agents_view_complex_states(db_session):
    # Hit tags and sparklines (Lines 705-711)
    agent = Agent(name="Tagged Bot", monthly_budget_usd=100.0)
    db_session.add(agent)
    db_session.commit()
    # Add 3 perms to trigger "+1" tag
    db_session.add(AgentPermission(agent_id=agent.id, scope="openai"))
    db_session.add(AgentPermission(agent_id=agent.id, scope="anthropic"))
    db_session.add(AgentPermission(agent_id=agent.id, scope="gemini"))
    # Add spend to trigger budget bar
    db_session.add(
        AuditLog(agent_id=agent.id, cost_usd=95.0, total_tokens=100000, target_service="openai")
    )
    db_session.commit()

    view = get_agents_view()

    # Find the row by checking for Tagged Bot text
    def find_in_tree(comp, target):
        if hasattr(comp, "children") and comp.children:
            if isinstance(comp.children, list):
                for child in comp.children:
                    if find_in_tree(child, target):
                        return True
            else:
                if find_in_tree(comp.children, target):
                    return True
        if hasattr(comp, "id") and comp.id == target:
            return True
        if str(comp) == target:
            return True
        return False

    # More direct check: get_agents_view returns a Div containing a Table
    # We just need to ensure the logic runs and returns a component tree
    assert isinstance(view, html.Div)
    assert "Tagged Bot" in str(view) or any("Tagged Bot" in str(c) for c in view.children)


def test_get_inventory_view_coverage(db_session):
    db_session.add(ModelPricing(model_name="zzz-bot", input_1m_price=1.0, output_1m_price=1.0))
    db_session.commit()
    view = get_inventory_view()
    assert "zzz-bot" in str(view)


def test_save_integration_key_callback_unit(db_session):
    # Line 2842 prevent update
    with pytest.raises(dash.exceptions.PreventUpdate):
        save_integration_key(0, None, "openai")

    # Success branch (Lines 2842-2860)
    res = save_integration_key(1, "sk-new-key", "openai")
    assert "Saved Successfully" in str(res)

    integration = db_session.query(Integration).filter_by(name="openai").first()
    assert integration.provider_key is not None


def test_toggle_registration_drawer_callback_unit():
    # Mock dash context
    with patch("dash.callback_context") as mock_ctx:
        # Trigger: open
        mock_ctx.triggered = [{"prop_id": "open-register-agent.n_clicks"}]
        mock_ctx.triggered_id = "open-register-agent"
        res = toggle_registration_drawer(1, 0, 0, 0, "side-drawer", "")
        # Output: side-drawer open, overlay open, name, desc, budget, scopes
        assert "side-drawer open" in res[0]

        # Trigger: error preserved (Line 2896-2904)
        mock_ctx.triggered_id = "submit-registration"
        res_err = toggle_registration_drawer(0, 0, 0, 1, "side-drawer open", "❌ missing name")
        assert "side-drawer open" in res_err[0]

        # Trigger: close (Line 2910)
        mock_ctx.triggered_id = "close-registration-drawer"
        res_close = toggle_registration_drawer(0, 1, 0, 0, "side-drawer open", "")
        assert res_close[0] == "side-drawer"  # Closed state


def test_handle_registration_submit_callback_unit(db_session):
    # No clicks
    with pytest.raises(dash.exceptions.PreventUpdate):
        handle_registration_submit(0, "Name", "Desc", 100, ["openai"])

    # Missing name (Line 2939)
    res_no_name = handle_registration_submit(1, "", "Desc", 100, ["openai"])
    assert "Agent name is required" in res_no_name[1]

    # Success (Lines 2942-2961)
    res_ok = handle_registration_submit(1, "Callback Bot", "Test", 500, ["openai", "gemini"])
    assert res_ok[1] == ""  # No error message

    agent = db_session.query(Agent).filter_by(name="Callback Bot").first()
    assert agent is not None
    assert agent.monthly_budget_usd == 500.0
    assert len(agent.permissions) == 2

    # Exception branch (Lines 2962-2965)
    with patch("agentauth.dashboard.app.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("Crash")
        mock_session.return_value = mock_db
        res_fail = handle_registration_submit(1, "Fail", "D", 0, [])
    assert "Error: Crash" in res_fail[1]


# --- Additional Dashboard Coverage ---


def test_render_page_logic_unit_coverage(db_session):
    # Line 1846: stats view
    agent = Agent(name="Stats Bot")
    db_session.add(agent)
    db_session.commit()
    # Trigger must NOT be None/nav-dashboard to enter the sidebar/stats logic cleanly in some paths
    # but handle the case where it IS nav-dashboard but active_agent_id is set
    res, active_id = render_page_logic("nav-dashboard", "", agent.id, "24h")
    assert active_id == agent.id

    # Line 1865: inventory view - use actual nav ID as trigger
    res_inv, _ = render_page_logic("nav-inventory", "nav-inventory.n_clicks", None, "24h")
    assert "Model Registry" in str(res_inv)

    # Other sidebar links (Logs, Integrations, alerts)
    for target in ["nav-logs", "nav-integrations", "nav-alerts", "nav-agents"]:
        res_link, _ = render_page_logic(target, f"{target}.n_clicks", None, "24h")
        assert res_link is not None


def test_handle_agent_dashboard_logic_unit_complex(db_session):
    agent = Agent(name="Complex Bot", is_frozen=False)
    db_session.add(agent)
    db_session.commit()

    # Freeze toggle (Lines 1927-1932)
    handle_agent_dashboard_logic({"type": "freeze-btn", "index": agent.id}, [], None, None)
    db_session.refresh(agent)
    assert agent.is_frozen is True

    # Set Budget (Lines 1934-1945)
    states = [
        None,
        None,
        None,
        [{"id": {"type": "budget-input", "index": agent.id}, "value": 123.45}],
    ]
    handle_agent_dashboard_logic({"type": "set-budget-btn", "index": agent.id}, states, None, None)
    db_session.refresh(agent)
    assert agent.monthly_budget_usd == 123.45

    # Grant Perm (Lines 1947-1963)
    states_perm = [
        None,
        None,
        [{"id": {"type": "perm-dropdown", "index": agent.id}, "value": "anthropic"}],
    ]
    handle_agent_dashboard_logic({"type": "grant-btn", "index": agent.id}, states_perm, None, None)
    db_session.refresh(agent)
    assert any(p.scope == "anthropic" for p in agent.permissions)


def test_inspect_json_unit_coverage(db_session):
    agent = Agent(name="Inspect Bot")
    db_session.add(agent)
    db_session.commit()
    db_session.add(AuditLog(agent_id=agent.id, request_details='{"foo":"bar"}'))
    db_session.commit()

    with patch("dash.callback_context") as mock_ctx:
        # Trigger
        mock_ctx.triggered = [{"prop_id": '{"type":"inspect-row","index":0}.n_clicks'}]
        mock_ctx.triggered_id = {"type": "inspect-row", "index": 0}
        style, content = inspect_json([1], agent.id)
        assert style["display"] == "block"
        assert '{"foo":"bar"}' in content


def test_add_or_update_model_pricing_unit(db_session):
    # Add (Lines 2044-2048)
    res_add = add_or_update_model_pricing(1, "new-m", 10.0, 20.0)
    assert "added successfully" in res_add

    # Update (Lines 2038-2042)
    res_upd = add_or_update_model_pricing(1, "new-m", 15.0, 25.0)
    assert "Pricing updated" in res_upd

    # Missing fields (Line 2034)
    assert "required" in add_or_update_model_pricing(1, None, 1, 1)


def test_update_active_integration_unit():
    ids = [
        {"type": "integration-sidebar-item", "name": "openai"},
        {"type": "integration-sidebar-item", "name": "gemini"},
    ]
    styles = [{"backgroundColor": "transparent"}, {"backgroundColor": "transparent"}]

    with patch("dash.callback_context") as mock_ctx:
        # Simulate JSON stringified ID (Line 2146-2151)
        mock_ctx.triggered = [
            {"prop_id": '{"name":"openai","type":"integration-sidebar-item"}.n_clicks'}
        ]

        name, new_styles = update_active_integration([1, 0], ids, styles)
        assert name == "openai"
        assert new_styles[0]["backgroundColor"] == "var(--bg-secondary)"

        # Exception branch (Line 2152-2153)
        mock_ctx.triggered = [{"prop_id": "malformed@@@.n_clicks"}]
        with pytest.raises(dash.exceptions.PreventUpdate):
            update_active_integration([1], ids, styles)


def test_render_integration_pane_unit_coverage(db_session):
    # None (Line 2171)
    assert "Please select" in str(render_integration_pane(None))
    # Unknown (Line 2176)
    assert "Unknown provider" in str(render_integration_pane("ghost"))
    # Integration with key (Line 2189)
    db_session.add(Integration(name="openai", provider_key="key", is_active=True))
    db_session.commit()
    res = render_integration_pane("openai")
    assert isinstance(res, list)
    assert len(res) > 0


# --- Security Coverage Boost ---


def test_security_error_branches():
    # decrypt_secret fallback (Line 42)
    assert decrypt_secret("not-encrypted") == "not-encrypted"

    # encrypt_secret / decrypt_secret success
    secret = "my-secret"
    enc = encrypt_secret(secret)
    assert decrypt_secret(enc) == secret
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None


def test_jwt_coverage():
    import datetime

    from agentauth.core.security import create_access_token, decode_access_token

    # Default expiry (Line 63)
    token1 = create_access_token({"sub": "test1"})
    payload1 = decode_access_token(token1)
    assert payload1["sub"] == "test1"

    # Custom expiry (Line 61)
    delta = datetime.timedelta(minutes=10)
    token2 = create_access_token({"sub": "test2"}, expires_delta=delta)
    payload2 = decode_access_token(token2)
    assert payload2["sub"] == "test2"
