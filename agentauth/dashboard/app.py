from typing import Any

import dash
from dash import ALL, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from ..core.database import SessionLocal
from ..core.models import (
    Agent,
    AgentPermission,
    AlertRule,
    AuditLog,
    Integration,
    ModelPricing,
)
from .pages import get_registered_pages, page_registry
from .utils import SUPPORTED_PROVIDERS, get_icon

app = dash.Dash(
    __name__,
    requests_pathname_prefix="/dashboard/",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css"
    ],
)


# Define layout components
def get_sidebar():
    """Generate the sidebar components dynamically from the page registry."""
    pages = get_registered_pages()
    sections: dict[str, list[Any]] = {}

    for page_cls in pages:
        page = page_cls()
        page_id = page_cls.__name__.lower().replace("page", "")
        link = html.A(
            [html.I(className=f"bi bi-{page.icon}", style={"marginRight": "10px"}), page.label],
            href="#",
            id={"type": "nav-link", "index": page_id},
            className="nav-link",
        )
        if page.section not in sections:
            sections[page.section] = []
        sections[page.section].append(link)

    sidebar_content: list[Any] = []
    for section_name, links in sections.items():
        sidebar_content.append(
            html.Div(section_name, className="nav-label", style={"marginTop": "20px"})
        )
        sidebar_content.extend(links)

    return html.Div(
        className="sidebar",
        children=[
            html.Div(
                className="sidebar-header",
                children=[html.Div(className="status-dot dot-active"), html.H2("AgentAuth")],
            ),
            html.Div(className="nav-section", children=sidebar_content),
        ],
    )


def get_registration_drawer():
    db = SessionLocal()
    integrations = db.query(Integration).all()
    db.close()

    scope_options = [{"label": f" {i.name.capitalize()}", "value": i.name} for i in integrations]

    return html.Div(
        [
            # Backdrop overlay
            html.Div(id="registration-drawer-overlay", className="drawer-overlay"),
            # Side Drawer
            html.Div(
                id="registration-side-drawer",
                className="side-drawer",
                children=[
                    html.Div(
                        className="drawer-header",
                        children=[
                            html.H3("Register New Enterprise Agent", style={"margin": "0"}),
                            html.Span(
                                "✕",
                                id="close-registration-drawer",
                                style={
                                    "cursor": "pointer",
                                    "fontSize": "1.2rem",
                                    "color": "var(--text-muted)",
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        className="drawer-body",
                        children=[
                            html.P(
                                "Configure identity, guardrails, and capabilities for this new agent probe.",
                                style={
                                    "fontSize": "0.85rem",
                                    "color": "var(--text-muted)",
                                    "marginBottom": "24px",
                                },
                            ),
                            html.Div(
                                className="form-group",
                                children=[
                                    html.Label("Agent Name", className="form-label"),
                                    dcc.Input(
                                        id="reg-agent-name",
                                        type="text",
                                        placeholder="e.g. FinanceBot HighDensity",
                                        className="form-control",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="form-group",
                                children=[
                                    html.Label("Description", className="form-label"),
                                    dcc.Textarea(
                                        id="reg-agent-desc",
                                        placeholder="Briefly describe the agent's primary goals...",
                                        className="form-control",
                                        style={"height": "80px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                className="form-group",
                                children=[
                                    html.Label(
                                        "Monthly Budget Ceiling (USD)", className="form-label"
                                    ),
                                    html.Div(
                                        style={"padding": "0 10px"},
                                        children=[
                                            dcc.Slider(
                                                id="reg-agent-budget",
                                                min=0,
                                                max=5000,
                                                step=100,
                                                value=1500,
                                                marks={
                                                    0: "$0",
                                                    1000: "$1k",
                                                    2500: "$2.5k",
                                                    5000: "$5k",
                                                },
                                                tooltip={
                                                    "placement": "bottom",
                                                    "always_visible": True,
                                                },
                                            )
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="form-group",
                                style={"marginTop": "32px"},
                                children=[
                                    html.Label("Authorized API Scopes", className="form-label"),
                                    html.P(
                                        "Select the upstream AI integrations this agent is permitted to call.",
                                        style={
                                            "fontSize": "0.75rem",
                                            "color": "var(--text-muted)",
                                            "marginBottom": "12px",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="reg-agent-scopes",
                                        options=scope_options,
                                        value=["openai"],  # Default
                                        labelStyle={
                                            "display": "block",
                                            "padding": "8px",
                                            "borderBottom": "1px solid #f1f5f9",
                                            "fontSize": "0.85rem",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="drawer-footer",
                        children=[
                            html.Button(
                                "Create Agent",
                                id="submit-registration",
                                className="btn-premium",
                                style={"flexGrow": "1"},
                            ),
                            html.Button(
                                "Cancel",
                                id="cancel-registration",
                                className="btn-secondary",
                                style={
                                    "padding": "8px 16px",
                                    "border": "1px solid var(--card-border)",
                                    "borderRadius": "6px",
                                    "background": "white",
                                    "fontSize": "0.85rem",
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        id="registration-error-msg",
                        style={
                            "color": "var(--danger)",
                            "padding": "0 24px 24px",
                            "fontSize": "0.8rem",
                            "textAlign": "center",
                        },
                    ),
                ],
            ),
        ]
    )


def get_top_header():
    return html.Div(
        className="top-header",
        children=[
            html.Div(className="search-box", children="🔍 Search agents, logs, or models..."),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "20px"},
                children=[
                    html.Div(
                        style={"width": "180px", "marginRight": "10px"},
                        children=[
                            dcc.Dropdown(
                                id="global-time-filter",
                                options=[
                                    {"label": "Last 1 Hour", "value": "1h"},
                                    {"label": "Last 6 Hours", "value": "6h"},
                                    {"label": "Last 24 Hours", "value": "24h"},
                                    {"label": "Last 7 Days", "value": "7d"},
                                    {"label": "All Time", "value": "all"},
                                ],
                                value="24h",
                                clearable=False,
                                style={
                                    "background": "var(--bg-card)",
                                    "color": "var(--text-main)",
                                    "border": "1px solid var(--border-color)",
                                    "borderRadius": "4px",
                                    "fontSize": "0.85rem",
                                },
                            )
                        ],
                    ),
                    html.Div(style={"fontSize": "1.2rem", "cursor": "pointer"}, children="🔔"),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Div(
                                style={"textAlign": "right"},
                                children=[
                                    html.Div(
                                        "Admin User",
                                        style={"fontWeight": "600", "fontSize": "0.85rem"},
                                    ),
                                    html.Div(
                                        "Super Admin",
                                        style={"fontSize": "0.75rem", "color": "var(--text-muted)"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={
                                    "width": "32px",
                                    "height": "32px",
                                    "borderRadius": "50%",
                                    "background": "#e2e8f0",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "fontWeight": "bold",
                                },
                                children="A",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def serve_layout():
    dash_page = page_registry.get("dashboard")
    return html.Div(
        className="app-container",
        children=[
            get_sidebar(),
            html.Div(
                className="main-wrapper",
                children=[
                    get_top_header(),
                    html.Div(
                        id="page-content",
                        className="main-content",
                        children=dash_page().render()
                        if dash_page
                        else html.Div("Dashboard page not found."),
                    ),
                ],
            ),
            # Registration UI
            get_registration_drawer(),
            dcc.Interval(id="dashboard-interval", interval=30 * 1000, n_intervals=0),
            dcc.Store(id="active-agent-id", data=None),
            dcc.Store(id="active-integration-store", data="openai"),
            dcc.Location(id="url", refresh=False),
        ],
    )


app.layout = serve_layout


# Logic Functions for Callbacks
def render_page_logic(triggered_id, triggered_prop_id, active_agent_id, time_range):
    """Dynamic routing logic using the page registry."""
    # Default to dashboard if no trigger or specific dashboard trigger
    page_id = "dashboard"

    if triggered_id:
        if isinstance(triggered_id, dict):
            t_type = triggered_id.get("type")
            if t_type == "nav-link":
                page_id = triggered_id["index"]
            elif t_type in ["stats-btn", "agent-row", "agent-card"]:
                agent_id = triggered_id["index"]
                page_id = "agents"
                active_agent_id = agent_id
            elif t_type == "back-btn" and triggered_id.get("index") == "agents":
                page_id = "agents"
                active_agent_id = None
        elif triggered_id == "global-time-filter":
            # Keep current page, but we need to know what it is.
            # For simplicity, if we don't have a sticky state, we default or use context.
            # In a better design, we'd have a 'current-page' Store.
            page_id = "dashboard" if not active_agent_id else "agents"

    page_cls = page_registry.get(page_id)
    if page_cls:
        return (
            page_cls().render(time_range=time_range, active_agent_id=active_agent_id),
            active_agent_id,
        )

    # Fallback
    fallback_cls = page_registry.get("dashboard")
    if fallback_cls:
        return fallback_cls().render(time_range=time_range), None
    return html.Div("No dashboard found in registry."), None


@app.callback(
    Output({"type": "nav-link", "index": ALL}, "className"),
    Input({"type": "nav-link", "index": ALL}, "n_clicks"),
    State({"type": "nav-link", "index": ALL}, "id"),
    prevent_initial_call=False,
)
def update_active_nav(n_clicks, ids):
    ctx = dash.callback_context
    triggered_id = ctx.triggered_id

    # If no trigger (initial load), dashboard is active
    active_index = "dashboard"
    if triggered_id and isinstance(triggered_id, dict):
        active_index = triggered_id.get("index", "dashboard")

    return ["nav-link active" if i["index"] == active_index else "nav-link" for i in ids]


@app.callback(
    Output("page-content", "children"),
    Output("active-agent-id", "data"),
    Input({"type": "nav-link", "index": ALL}, "n_clicks"),
    Input({"type": "back-btn", "index": ALL}, "n_clicks"),
    Input({"type": "stats-btn", "index": ALL}, "n_clicks"),
    Input({"type": "agent-row", "index": ALL}, "n_clicks"),
    Input({"type": "agent-card", "index": ALL}, "n_clicks"),
    Input("global-time-filter", "value"),
    State("active-agent-id", "data"),
    prevent_initial_call=False,
)
def render_page(
    nav_clicks,
    back_clicks,
    stats_clicks,
    row_clicks,
    card_clicks,
    time_range,
    active_agent_id,
):
    ctx = dash.callback_context
    triggered_id = ctx.triggered_id
    triggered_prop_id = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    return render_page_logic(triggered_id, triggered_prop_id, active_agent_id, time_range)


def handle_agent_dashboard_logic(triggered_id, states_list, new_name, new_desc):
    db = SessionLocal()
    status_msg = ""

    # 1. Handle Creation
    if triggered_id == "create-agent-btn":
        if not new_name:
            db.close()
            return dash.no_update, "❌ Name is required"
        new_agent = Agent(name=new_name, description=new_desc or "")
        db.add(new_agent)
        db.commit()
        status_msg = f"✅ Agent '{new_name}' created!"

    # 2. Handle Dictionary IDs (Freeze, Grant, Revoke)
    elif isinstance(triggered_id, dict):
        t_type = triggered_id.get("type")

        if t_type == "freeze-btn":
            agent_id = triggered_id["index"]
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.is_frozen = not bool(agent.is_frozen)  # type: ignore[assignment]
                db.commit()

        elif t_type == "set-budget-btn":
            agent_id = triggered_id["index"]
            budget = None
            if states_list and len(states_list) > 3:
                for s_item in states_list[3]:
                    if s_item.get("id", {}).get("index") == agent_id:
                        budget = s_item.get("value")
                        break
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.monthly_budget_usd = float(budget) if budget is not None else None  # type: ignore[assignment]
                db.commit()

        elif t_type == "grant-btn":
            agent_id = triggered_id["index"]
            scope = None
            if states_list and len(states_list) > 2:
                for s_item in states_list[2]:
                    if s_item.get("id", {}).get("index") == agent_id:
                        scope = s_item.get("value")
                        break
            if scope:
                existing = (
                    db.query(AgentPermission)
                    .filter(AgentPermission.agent_id == agent_id, AgentPermission.scope == scope)
                    .first()
                )
                if not existing:
                    db.add(AgentPermission(agent_id=agent_id, scope=scope))
                    db.commit()

    db.close()
    agents_page = page_registry.get("agents")
    updated_view = agents_page().render() if agents_page else None
    if updated_view:
        # Corrected indexing: 0: Header, 1: Metrics, 2: AgentsTable/Card, 3: CreationStatus
        return updated_view.children[2].children, status_msg
    return [], status_msg


@app.callback(
    Output("agents-container", "children"),
    Output("creation-status", "children"),
    Input({"type": "freeze-btn", "index": ALL}, "n_clicks"),
    Input({"type": "set-budget-btn", "index": ALL}, "n_clicks"),
    State("new-agent-name", "value"),
    State("new-agent-desc", "value"),
    State({"type": "perm-dropdown", "index": ALL}, "value"),
    State({"type": "budget-input", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def handle_agent_dashboard(
    freeze_clicks,
    create_clicks,
    grant_clicks,
    budget_clicks,
    new_name,
    new_desc,
    dropdown_values,
    budget_values,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    return handle_agent_dashboard_logic(ctx.triggered_id, ctx.states_list, new_name, new_desc)


@app.callback(
    Output("json-inspector-panel", "style"),
    Output("json-content", "children"),
    Input({"type": "inspect-row", "index": ALL}, "n_clicks"),
    State("active-agent-id", "data"),
    prevent_initial_call=True,
)
def inspect_json(row_clicks, agent_id):
    ctx = dash.callback_context
    if not ctx.triggered or not any(row_clicks or []):
        raise PreventUpdate
    clicked_idx = ctx.triggered_id["index"]
    db = SessionLocal()
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.agent_id == agent_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )
    db.close()
    if clicked_idx < len(logs):
        log = logs[clicked_idx]
        return {"display": "block"}, (log.request_details or "{}")
    return {"display": "none"}, ""


@app.callback(
    Output("model-save-status", "children"),
    Input("save-model-btn", "n_clicks"),
    State("new-model-name", "value"),
    State("new-model-in-price", "value"),
    State("new-model-out-price", "value"),
    prevent_initial_call=True,
)
def add_or_update_model_pricing(n_clicks, name, in_price, out_price):
    if not name or in_price is None or out_price is None:
        return "❌ All fields are required."

    db = SessionLocal()
    model = db.query(ModelPricing).filter(ModelPricing.model_name == name).first()
    if model:
        model.input_1m_price = float(in_price)  # type: ignore[assignment]
        model.output_1m_price = float(out_price)  # type: ignore[assignment]
        msg = f"✅ Pricing updated for '{name}'"
    else:
        new_model = ModelPricing(
            model_name=name, input_1m_price=float(in_price), output_1m_price=float(out_price)
        )
        db.add(new_model)
        msg = f"✅ Model '{name}' added successfully"
    db.commit()
    db.close()
    return msg


@app.callback(
    Output("alert-save-status", "children"),
    Input("save-alert-btn", "n_clicks"),
    State("alert-agent-select", "value"),
    State("alert-threshold-select", "value"),
    State("alert-channel-select", "value"),
    State("alert-destination-input", "value"),
    prevent_initial_call=True,
)
def save_alert_rule(n_clicks, agent_value, threshold, channel, destination):
    """Persist a new :class:`~agentauth.core.models.AlertRule` to the database.

    Args:
    ----
        n_clicks: Number of times the Save button was clicked.
        agent_value: String agent ID from the dropdown, or empty string for global.
        threshold: Integer threshold percentage (80 | 90 | 100).
        channel: Notification channel identifier (``"log"``, ``"webhook"``, ``"slack"``).
        destination: Destination URL; may be ``None`` for the ``"log"`` channel.

    Returns:
    -------
        A status message string displayed below the form.

    """
    if not threshold or not channel:
        return "❌ Threshold and channel are required."
    if channel in ("webhook", "slack") and not destination:
        return f"❌ A destination URL is required for the '{channel}' channel."

    agent_id = int(agent_value) if agent_value else None

    db = SessionLocal()
    rule = AlertRule(
        agent_id=agent_id,
        threshold_pct=int(threshold),
        channel=channel,
        destination=destination or None,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.close()

    scope = f"Agent #{agent_id}" if agent_id else "Global"
    return f"✅ Rule saved: {scope} → {threshold}% via {channel}"


@app.callback(
    Output("alert-delete-status", "children"),
    Input({"type": "delete-alert-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def delete_alert_rule(n_clicks_list):
    """Soft-delete (deactivate) an :class:`~agentauth.core.models.AlertRule`.

    Args:
    ----
        n_clicks_list: List of click counts for each delete button (pattern-match).

    Returns:
    -------
        A status message string displayed below the rules table.

    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    rule_id = ctx.triggered_id["index"]
    db = SessionLocal()
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if rule:
        rule.is_active = False  # type: ignore[assignment]
        db.commit()
        msg = f"🗑️ Rule #{rule_id} deactivated."
    else:
        msg = f"❌ Rule #{rule_id} not found."
    db.close()
    return msg


@app.callback(
    [
        Output("active-integration-store", "data"),
        Output({"type": "integration-sidebar-item", "name": ALL}, "style"),
    ],
    Input({"type": "integration-sidebar-item", "name": ALL}, "n_clicks"),
    State({"type": "integration-sidebar-item", "name": ALL}, "id"),
    State({"type": "integration-sidebar-item", "name": ALL}, "style"),
    prevent_initial_call=True,
)
def update_active_integration(n_clicks, ids, styles):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    try:
        triggered_prop = ctx.triggered[0]["prop_id"]
        # Handle dict-based IDs passed as strings like '{"name":"openai","type":"integration-sidebar-item"}.n_clicks'
        triggered_id_str = triggered_prop.split(".")[0]
        import json

        triggered_id = json.loads(triggered_id_str)
        selected_name = triggered_id["name"]
    except Exception as err:
        raise PreventUpdate from err

    new_styles = []
    for item_id, style_dict in zip(ids, styles):
        new_style = style_dict.copy() if style_dict else {}
        if item_id["name"] == selected_name:
            new_style["backgroundColor"] = "var(--bg-secondary)"
        else:
            new_style["backgroundColor"] = "transparent"
        new_styles.append(new_style)
    return selected_name, new_styles


@app.callback(
    Output("integration-details-pane", "children"),
    Input("active-integration-store", "data"),
)
def render_integration_pane(selected_name):
    if not selected_name:
        return html.Div("Please select a service from the sidebar.", style={"padding": "20px"})

    info = SUPPORTED_PROVIDERS.get(selected_name)
    if not info:
        return html.Div("Unknown provider.", style={"padding": "20px"})

    from agentauth.core.database import SessionLocal
    from agentauth.core.models import Integration

    db = SessionLocal()
    integration = db.query(Integration).filter(Integration.name == selected_name).first()
    db.close()

    masked_key = ""
    is_active = False
    if integration and integration.provider_key:
        is_active = integration.is_active  # type: ignore[assignment]
        masked_key = "sk-" + ("•" * 32)

    # Generate dummy data for latency chart
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go

    times = pd.date_range(start="2023-06-05 00:00", periods=24, freq="h")
    latencies = np.random.normal(15, 5, 24).clip(5, 50)
    latency_fig = go.Figure()
    latency_fig.add_trace(
        go.Scatter(
            x=times,
            y=latencies,
            mode="lines",
            line={"width": 3, "color": "#0f172a"},
            fill="tozeroy",
            fillcolor="rgba(15, 23, 42, 0.05)",
        )
    )
    latency_fig.update_layout(
        margin={"t": 10, "b": 30, "l": 30, "r": 10},
        height=150,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": True, "showgrid": False, "tickfont": {"size": 10}},
        yaxis={"visible": True, "showgrid": True, "gridcolor": "#f1f5f9", "tickfont": {"size": 10}},
    )

    return [
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "borderBottom": "1px solid var(--border-color)",
                "paddingBottom": "15px",
            },
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "12px"},
                    children=[
                        get_icon(selected_name, size=36),
                        html.H2(
                            f"{info['name']} ({'Serverless' if 'pinecone' in selected_name else 'Cloud'})",
                            style={"margin": "0", "fontSize": "22px", "fontWeight": "700"},
                        ),
                        html.Span(
                            "Active" if is_active else "Setup",
                            style={
                                "backgroundColor": "#dcfce7" if is_active else "#f3f4f6",
                                "color": "#166534" if is_active else "#4b5563",
                                "padding": "2px 8px",
                                "borderRadius": "4px",
                                "fontSize": "12px",
                                "marginLeft": "10px",
                                "fontWeight": "bold",
                            },
                        ),
                    ],
                ),
                html.Button("Manage Service", className="btn-secondary"),
            ],
        ),
        # Service Configuration Row
        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, 1fr)",
                "gap": "20px",
                "padding": "10px 0",
                "borderBottom": "1px solid var(--border-color)",
            },
            children=[
                html.Div(
                    [
                        html.Label(
                            "SERVICE CONFIGURATION",
                            style={
                                "fontSize": "11px",
                                "color": "var(--text-muted)",
                                "display": "block",
                                "marginBottom": "8px",
                            },
                        ),
                        html.Span(
                            "Current Version",
                            style={
                                "display": "block",
                                "fontSize": "13px",
                                "color": "var(--text-muted)",
                            },
                        ),
                        html.Strong(
                            f"{info.get('version', '1.0.0')}",
                            style={"fontSize": "14px", "color": "var(--text-main)"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div(style={"height": "16px"}),  # Spacer
                        html.Span(
                            "Region",
                            style={
                                "display": "block",
                                "fontSize": "13px",
                                "color": "var(--text-muted)",
                            },
                        ),
                        html.Strong(
                            f"{info.get('region', 'us-east-1')}",
                            style={"fontSize": "14px", "color": "var(--text-main)"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div(style={"height": "16px"}),  # Spacer
                        html.Span(
                            "Indices" if "pinecone" in selected_name else "Context Window",
                            style={
                                "display": "block",
                                "fontSize": "13px",
                                "color": "var(--text-muted)",
                            },
                        ),
                        html.Strong(
                            "8 Active" if "pinecone" in selected_name else "128K",
                            style={"fontSize": "14px", "color": "var(--text-main)"},
                        ),
                    ]
                ),
            ],
        ),
        # API Settings Section
        html.Div(
            children=[
                html.H4(
                    "API SETTINGS",
                    style={
                        "fontSize": "12px",
                        "color": "var(--text-muted)",
                        "marginBottom": "12px",
                        "letterSpacing": "0.5px",
                    },
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "24px"},
                    children=[
                        html.Div(
                            [
                                html.Label(
                                    f"{info['name']} API Key",
                                    style={
                                        "display": "block",
                                        "fontSize": "13px",
                                        "marginBottom": "8px",
                                        "fontWeight": "600",
                                    },
                                ),
                                html.Div(
                                    style={
                                        "position": "relative",
                                        "display": "flex",
                                        "alignItems": "center",
                                    },
                                    children=[
                                        dcc.Input(
                                            id="integration-api-key-input",
                                            type="password",
                                            value=masked_key,
                                            placeholder="Enter new API Key...",
                                            className="enterprise-input",
                                            style={
                                                "width": "100%",
                                                "backgroundColor": "var(--bg-secondary)"
                                                if is_active
                                                else "var(--bg-primary)",
                                            },
                                            disabled=is_active,
                                        ),
                                        html.I(
                                            className="bi bi-eye-slash",
                                            style={
                                                "position": "absolute",
                                                "right": "35px",
                                                "cursor": "pointer",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                        html.I(
                                            className="bi bi-copy",
                                            style={
                                                "position": "absolute",
                                                "right": "10px",
                                                "cursor": "pointer",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={"marginTop": "12px", "display": "flex", "gap": "10px"},
                                    children=[
                                        html.Button(
                                            "Regenerate API Key" if is_active else "Save API Key",
                                            id="save-integration-key-btn",
                                            className="btn-secondary",
                                            style={"fontSize": "12px"},
                                        ),
                                        html.Button(
                                            "Test Connection",
                                            className="btn-secondary",
                                            style={"fontSize": "12px"},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="save-integration-key-status",
                                    style={"marginTop": "8px", "fontSize": "12px"},
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Environment Name",
                                    style={
                                        "display": "block",
                                        "fontSize": "13px",
                                        "marginBottom": "8px",
                                        "fontWeight": "600",
                                    },
                                ),
                                dcc.Input(
                                    type="text",
                                    placeholder="gcp-starter"
                                    if "pinecone" in selected_name
                                    else "production",
                                    className="enterprise-input",
                                    style={"width": "100%"},
                                ),
                            ]
                        ),
                    ],
                ),
            ]
        ),
        # Usage & Quotas Section
        html.Div(
            children=[
                html.H4(
                    "USAGE & QUOTAS",
                    style={
                        "fontSize": "12px",
                        "color": "var(--text-muted)",
                        "marginBottom": "12px",
                    },
                ),
                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(3, 1fr)",
                        "gap": "15px",
                    },
                    children=[
                        html.Div(
                            className="card",
                            style={"padding": "16px", "backgroundColor": "var(--bg-primary)"},
                            children=[
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                        "marginBottom": "12px",
                                    },
                                    children=[
                                        html.I(
                                            className="bi bi-search", style={"color": "#3b82f6"}
                                        ),
                                        html.Span(
                                            "Total Queries (30 Days)",
                                            style={
                                                "fontSize": "12px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                    ],
                                ),
                                html.H3(
                                    "12.4M",
                                    style={"margin": "0", "fontSize": "28px", "fontWeight": "700"},
                                ),
                            ],
                        ),
                        html.Div(
                            className="card",
                            style={"padding": "16px", "backgroundColor": "var(--bg-primary)"},
                            children=[
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                        "marginBottom": "12px",
                                    },
                                    children=[
                                        html.I(
                                            className="bi bi-pencil-square",
                                            style={"color": "#10b981"},
                                        ),
                                        html.Span(
                                            "Write Requests (30 Days)",
                                            style={
                                                "fontSize": "12px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                    ],
                                ),
                                html.H3(
                                    "4.9M",
                                    style={"margin": "0", "fontSize": "28px", "fontWeight": "700"},
                                ),
                            ],
                        ),
                        html.Div(
                            className="card",
                            style={"padding": "16px", "backgroundColor": "var(--bg-primary)"},
                            children=[
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px",
                                        "marginBottom": "12px",
                                    },
                                    children=[
                                        html.I(
                                            className="bi bi-database", style={"color": "#f59e0b"}
                                        ),
                                        html.Span(
                                            "Vectors Stored",
                                            style={
                                                "fontSize": "12px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "alignItems": "baseline",
                                        "gap": "6px",
                                    },
                                    children=[
                                        html.H3(
                                            "85.2M",
                                            style={
                                                "margin": "0",
                                                "fontSize": "28px",
                                                "fontWeight": "700",
                                            },
                                        ),
                                        html.Span(
                                            "/ 100M",
                                            style={
                                                "fontSize": "13px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                        html.Span(
                                            "85%",
                                            style={
                                                "fontSize": "13px",
                                                "color": "#f59e0b",
                                                "marginLeft": "auto",
                                            },
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={
                                        "height": "6px",
                                        "width": "100%",
                                        "backgroundColor": "#f1f5f9",
                                        "marginTop": "8px",
                                        "borderRadius": "3px",
                                        "overflow": "hidden",
                                    },
                                    children=[
                                        html.Div(
                                            style={
                                                "height": "100%",
                                                "width": "85%",
                                                "backgroundColor": "#0f172a",
                                            }
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                # Quota Usage Bar (Mockup Style)
                html.Div(
                    style={
                        "marginTop": "20px",
                        "padding": "15px",
                        "borderBottom": "1px solid var(--border-color)",
                    },
                    children=[
                        html.Div(
                            style={
                                "display": "flex",
                                "justifyContent": "space-between",
                                "marginBottom": "10px",
                            },
                            children=[
                                html.Strong("Quota Usage", style={"fontSize": "13px"}),
                                html.Span(
                                    "Status: Normal",
                                    style={"fontSize": "12px", "color": "var(--text-muted)"},
                                ),
                            ],
                        ),
                        html.Div(
                            style={
                                "height": "8px",
                                "width": "100%",
                                "display": "flex",
                                "borderRadius": "4px",
                                "overflow": "hidden",
                            },
                            children=[
                                html.Div(style={"flex": "7", "backgroundColor": "#0f172a"}),
                                html.Div(style={"flex": "2", "backgroundColor": "#10b981"}),
                                html.Div(style={"flex": "1", "backgroundColor": "#dc2626"}),
                                html.Div(style={"flex": "2", "backgroundColor": "#f1f5f9"}),
                            ],
                        ),
                        html.Div(
                            style={
                                "display": "flex",
                                "justifyContent": "space-between",
                                "marginTop": "10px",
                            },
                            children=[
                                html.Span("Pinecone", style={"fontSize": "12px"}),
                                html.Div(
                                    [
                                        html.Strong("8.52 GB", style={"fontSize": "12px"}),
                                        html.Span(
                                            " / 10 GB",
                                            style={
                                                "fontSize": "12px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        ),
        # Latency Chart Section
        html.Div(
            children=[
                html.H4(
                    "LATENCY CHART",
                    style={
                        "fontSize": "12px",
                        "color": "var(--text-muted)",
                        "marginBottom": "12px",
                    },
                ),
                html.Div(
                    className="card",
                    style={"padding": "20px", "backgroundColor": "white"},
                    children=[
                        html.Div(
                            style={
                                "display": "flex",
                                "justifyContent": "space-between",
                                "marginBottom": "15px",
                            },
                            children=[
                                html.Strong(
                                    "Query Latency (Last 24h, ms)", style={"fontSize": "14px"}
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            "Average: ",
                                            style={
                                                "fontSize": "12px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                        html.Strong("18ms  ", style={"fontSize": "12px"}),
                                        html.Span(
                                            "P99: ",
                                            style={
                                                "fontSize": "12px",
                                                "color": "var(--text-muted)",
                                            },
                                        ),
                                        html.Strong("45ms", style={"fontSize": "12px"}),
                                    ]
                                ),
                            ],
                        ),
                        dcc.Graph(figure=latency_fig, config={"displayModeBar": False}),
                    ],
                ),
            ]
        ),
        # Log Section
        html.Div(
            className="card",
            style={
                "padding": "0",
                "marginTop": "10px",
                "overflow": "hidden",
                "border": "1px solid #f1f5f9",
            },
            children=[
                html.Div(
                    style={"padding": "15px", "borderBottom": "1px solid #f1f5f9"},
                    children=[
                        html.H4(
                            "Recent Logs",
                            style={"margin": "0", "fontSize": "14px", "fontWeight": "700"},
                        )
                    ],
                ),
                html.Table(
                    style={
                        "width": "100%",
                        "textAlign": "left",
                        "fontSize": "13px",
                        "borderCollapse": "collapse",
                    },
                    children=[
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th(
                                        "Timestamp",
                                        style={
                                            "padding": "12px 15px",
                                            "backgroundColor": "#f8fafc",
                                        },
                                    ),
                                    html.Th(
                                        "Operation",
                                        style={
                                            "padding": "12px 15px",
                                            "backgroundColor": "#f8fafc",
                                        },
                                    ),
                                    html.Th(
                                        "Status",
                                        style={
                                            "padding": "12px 15px",
                                            "backgroundColor": "#f8fafc",
                                        },
                                    ),
                                    html.Th(
                                        "Latency",
                                        style={
                                            "padding": "12px 15px",
                                            "backgroundColor": "#f8fafc",
                                        },
                                    ),
                                ]
                            )
                        ),
                        html.Tbody(
                            [
                                html.Tr(
                                    [
                                        html.Td(
                                            "2023-06-05 13:43:10",
                                            style={
                                                "padding": "12px 15px",
                                                "borderBottom": "1px solid #f1f5f9",
                                            },
                                        ),
                                        html.Td(
                                            "Operation",
                                            style={
                                                "padding": "12px 15px",
                                                "borderBottom": "1px solid #f1f5f9",
                                            },
                                        ),
                                        html.Td(
                                            "Actived",
                                            style={
                                                "padding": "12px 15px",
                                                "borderBottom": "1px solid #f1f5f9",
                                                "color": "#166534",
                                                "fontWeight": "600",
                                            },
                                        ),
                                        html.Td(
                                            "45ms",
                                            style={
                                                "padding": "12px 15px",
                                                "borderBottom": "1px solid #f1f5f9",
                                            },
                                        ),
                                    ]
                                ),
                                html.Tr(
                                    [
                                        html.Td(
                                            "2023-06-05 13:42:05", style={"padding": "12px 15px"}
                                        ),
                                        html.Td("Operation", style={"padding": "12px 15px"}),
                                        html.Td(
                                            "Actived",
                                            style={
                                                "padding": "12px 15px",
                                                "color": "#166534",
                                                "fontWeight": "600",
                                            },
                                        ),
                                        html.Td("42ms", style={"padding": "12px 15px"}),
                                    ]
                                ),
                            ]
                        ),
                    ],
                ),
            ],
        ),
    ]


@app.callback(
    Output("save-integration-key-status", "children"),
    Input("save-integration-key-btn", "n_clicks"),
    State("integration-api-key-input", "value"),
    State("active-integration-store", "data"),
    prevent_initial_call=True,
)
def save_integration_key(n_clicks, api_key, selected_name):
    if not n_clicks or not api_key or api_key.startswith("sk-••••••"):
        raise PreventUpdate

    from agentauth.core.database import SessionLocal
    from agentauth.core.models import Integration

    db = SessionLocal()
    integration = db.query(Integration).filter(Integration.name == selected_name).first()

    if not integration:
        integration = Integration(name=selected_name, is_active=True)  # type: ignore[assignment]
        db.add(integration)

    integration.provider_key = api_key
    integration.is_active = True  # type: ignore[assignment]
    db.commit()
    db.close()

    return html.Span(
        "✅ API Key Saved Successfully! Refresh the page.", style={"color": "var(--success)"}
    )


# --- Registration Drawer Callbacks ---


@app.callback(
    [
        Output("registration-side-drawer", "className"),
        Output("registration-drawer-overlay", "className"),
        Output("reg-agent-name", "value"),
        Output("reg-agent-desc", "value"),
        Output("reg-agent-budget", "value"),
        Output("reg-agent-scopes", "value"),
    ],
    [
        Input("open-register-agent", "n_clicks"),
        Input("close-registration-drawer", "n_clicks"),
        Input("cancel-registration", "n_clicks"),
        Input("submit-registration", "n_clicks"),
    ],
    [State("registration-side-drawer", "className"), State("registration-error-msg", "children")],
    prevent_initial_call=True,
)
def toggle_registration_drawer(
    open_clicks, close_clicks, cancel_clicks, submit_clicks, current_class, error_msg
):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    # If submitting and there's an error (e.g. name missing), don't close
    if triggered_id == "submit-registration" and error_msg and "❌" in error_msg:
        return (
            current_class,
            "drawer-overlay open",
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )

    if triggered_id == "open-register-agent":
        return "side-drawer open", "drawer-overlay open", "", "", 1500, ["openai"]

    # Close for any other trigger (close, cancel, or successful submit)
    return (
        "side-drawer",
        "drawer-overlay",
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
    )


@app.callback(
    [
        Output("page-content", "children", allow_duplicate=True),
        Output("registration-error-msg", "children"),
    ],
    Input("submit-registration", "n_clicks"),
    [
        State("reg-agent-name", "value"),
        State("reg-agent-desc", "value"),
        State("reg-agent-budget", "value"),
        State("reg-agent-scopes", "value"),
    ],
    prevent_initial_call=True,
)
def handle_registration_submit(n_clicks, name, desc, budget, scopes):
    if not n_clicks:
        raise PreventUpdate

    if not name:
        return dash.no_update, "❌ Agent name is required"

    db = SessionLocal()
    try:
        # 1. Create Agent
        new_agent = Agent(
            name=name,
            description=desc or "",
            monthly_budget_usd=float(budget) if budget is not None else None,
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        # 2. Add Permissions/Scopes
        if scopes:
            for scope in scopes:
                db.add(AgentPermission(agent_id=new_agent.id, scope=scope))
            db.commit()

        db.close()
        # Return refreshed view
        agents_page = page_registry.get("agents")
        return agents_page().render() if agents_page else html.Div("Registry Error"), ""
    except Exception as e:
        db.rollback()
        db.close()
        return dash.no_update, f"❌ Error: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    app.run_server(debug=True, port=8000)
