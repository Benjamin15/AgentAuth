import datetime
from typing import Any

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..core.database import SessionLocal
from ..core.models import (
    Agent,
    AgentPermission,
    AlertEvent,
    AlertRule,
    AuditLog,
    Integration,
    ModelPricing,
)
from .widgets import get_registered_widgets


# Utils
def get_time_delta(time_range: str):
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if time_range == "1h":
        return now - datetime.timedelta(hours=1)
    if time_range == "24h":
        return now - datetime.timedelta(days=1)
    if time_range == "7d":
        return now - datetime.timedelta(days=7)
    return None


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
    return html.Div(
        className="sidebar",
        children=[
            html.Div(
                className="sidebar-header",
                children=[html.Div(className="status-dot dot-active"), html.H2("AgentAuth")],
            ),
            html.Div(
                className="nav-section",
                children=[
                    html.Div("Core", className="nav-label"),
                    html.A("Dashboard", href="#", id="nav-dashboard", className="nav-link active"),
                    html.A("Agents", href="#", id="nav-agents", className="nav-link"),
                    html.A("Integrations", href="#", id="nav-integrations", className="nav-link"),
                    html.Div("Analytics", className="nav-label", style={"marginTop": "20px"}),
                    html.A("Audit Logs", href="#", id="nav-logs", className="nav-link"),
                    html.A("Alerts", href="#", id="nav-alerts", className="nav-link"),
                    html.A("Usage Reports", href="#", className="nav-link"),
                    html.Div("Models", className="nav-label", style={"marginTop": "20px"}),
                    html.A("Inventory", href="#", id="nav-inventory", className="nav-link"),
                    html.A("Performance", href="#", className="nav-link"),
                    html.A("Drift", href="#", className="nav-link"),
                    html.Div("Settings", className="nav-label", style={"marginTop": "20px"}),
                    html.A("General", href="#", className="nav-link"),
                    html.A("Security", href="#", className="nav-link"),
                ],
            ),
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


def get_dashboard_view(time_range: str = "24h") -> html.Div:
    """Render the main dashboard using dynamically discovered widgets."""
    db = SessionLocal()
    delta = get_time_delta(time_range)

    # 1. Fetch Data
    logs_query = db.query(AuditLog)
    if delta:
        logs_query = logs_query.filter(AuditLog.timestamp >= delta)
    logs = logs_query.all()

    agents = db.query(Agent).all()
    db.close()

    if not logs:
        return html.Div(
            className="animated",
            children=[
                html.H1("AI Observability Dashboard"),
                html.P(f"No data captured for the range '{time_range}'. Check proxy connections."),
            ],
        )

    # 2. Build Data Context for Widgets
    # We include both raw objects and a pandas DataFrame for convenience
    df = pd.DataFrame(
        [
            {
                "timestamp": entry.timestamp,
                "service": entry.target_service,
                "status": entry.response_status,
                "agent_id": entry.agent_id,
                "latency": entry.latency_ms or 0,
                "tokens": entry.total_tokens or 0,
                "cost": float(entry.cost_usd or 0.0),
            }
            for entry in logs
        ]
    )

    data = {"logs": logs, "agents": agents, "df": df}

    # 3. Resolve and Render Widgets
    try:
        widget_classes = get_registered_widgets()
        # Group widgets to maintain the premium layout structure
        metric_widgets = [cls().render(data) for cls in widget_classes if cls.group == "metric"]
        chart_widgets = [cls().render(data) for cls in widget_classes if cls.group == "chart"]
        card_widgets = [cls().render(data) for cls in widget_classes if cls.group == "card"]
    except Exception as exc:
        return html.Div(
            [
                html.H1("Dashboard Error"),
                html.P("Failed to load modular widgets:"),
                html.Pre(str(exc)),
            ]
        )

    return html.Div(
        className="animated",
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "30px",
                },
                children=[
                    html.H1("AI Observability Dashboard", style={"margin": "0"}),
                ],
            ),
            # Metrics Row (Top grid)
            html.Div(className="metrics-grid", children=metric_widgets),
            # Charts Row (Middle section)
            html.Div(className="chart-row", style={"marginBottom": "20px"}, children=chart_widgets),
            # Main Cards (Bottom section: Heatmaps, tables, etc.)
            html.Div(children=card_widgets),
        ],
    )


def get_agents_view():
    import numpy as np

    db = SessionLocal()
    agent_data_list: list[dict[str, Any]] = []
    total_agents = 0
    active_in_hour = 0
    total_spend = 0.0
    success_rate = 100.0

    try:
        # 1. Fetch Agents and their permissions upfront
        agents = db.query(Agent).options(joinedload(Agent.permissions)).all()
        total_agents = len(agents)

        # 2. Global Metrics
        one_hour_ago = datetime.datetime.now(datetime.timezone.utc).replace(
            tzinfo=None
        ) - datetime.timedelta(hours=1)
        month_start = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(tzinfo=None)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )

        active_in_hour = (
            db.query(func.count(func.distinct(AuditLog.agent_id)))
            .filter(AuditLog.timestamp >= one_hour_ago)
            .scalar()
            or 0
        )

        from sqlalchemy import case  # Ensure case is imported

        monthly_stats = (
            db.query(
                func.count(AuditLog.id).label("req_count"),
                func.sum(AuditLog.total_tokens).label("tokens"),
                func.sum(case((AuditLog.response_status == 200, 1), else_=0)).label(
                    "success_count"
                ),
            )
            .filter(AuditLog.timestamp >= month_start)
            .first()
        )

        if monthly_stats and getattr(monthly_stats, "req_count", 0) > 0:
            total_spend = (monthly_stats.tokens or 0) * 0.0000003
            success_rate = (monthly_stats.success_count / monthly_stats.req_count) * 100

        # 3. Process agent data into vanilla dictionaries (Safe for Dash)
        for agent in agents:
            # Agent-specific log stats
            agent_stats = (
                db.query(func.sum(AuditLog.total_tokens).label("tokens"))
                .filter(AuditLog.agent_id == agent.id, AuditLog.timestamp >= month_start)
                .first()
            )
            agent_spend = (agent_stats.tokens or 0) * 0.0000003 if agent_stats else 0.0

            # Decouple relationship access
            scopes = [p.scope for p in agent.permissions]

            agent_data_list.append(
                {
                    "id": str(agent.id),
                    "name": str(agent.name),
                    "is_active": not bool(agent.is_frozen),
                    "monthly_budget": float(agent.monthly_budget_usd or 0.0),
                    "spend": float(agent_spend),
                    "scopes": scopes,
                }
            )

    except Exception as e:
        return html.Div([html.H3("Registry Data Error"), html.Pre(str(e))])
    finally:
        db.close()

    # 4. Generate UI from decoupled data
    agent_rows = []
    for data in agent_data_list:
        is_active: bool = bool(data["is_active"])
        name: str = str(data["name"])
        agent_id: str = str(data["id"])
        monthly_budget: float = float(data.get("monthly_budget", 0.0))
        spend: float = float(data.get("spend", 0.0))
        agent_scopes: list[str] = list(data.get("scopes", []))

        status_class = "badge-active" if is_active else "badge-inactive"
        status_text = "Active" if is_active else "Inactive"
        if monthly_budget > 0 and spend >= monthly_budget:
            status_class = "badge-limited"
            status_text = "Limited"

        budget_pct = min(100, (spend / monthly_budget * 100)) if monthly_budget > 0 else 0
        model_tags = [html.Span(s, className="model-tag") for s in agent_scopes[:2]]
        if len(agent_scopes) > 2:
            model_tags.append(html.Span(f"+{len(agent_scopes) - 2}", className="model-tag"))

        spark_data = np.random.randint(5, 15, 8)
        sparkline_fig = go.Figure(
            data=go.Scatter(
                y=spark_data,
                mode="lines",
                line={"color": "var(--accent-blue)", "width": 1.5},
                fill="tozeroy",
                fillcolor="rgba(59, 130, 246, 0.08)",
            )
        )
        sparkline_fig.update_layout(
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            height=24,
            width=90,
            xaxis={"visible": False},
            yaxis={"visible": False},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        agent_rows.append(
            html.Tr(
                className="registry-row clickable-row",
                id={"type": "agent-card", "index": agent_id},
                children=[
                    html.Td(
                        [
                            html.Strong(
                                name,
                                style={"display": "block", "color": "var(--accent-blue)"},
                            ),
                            html.Span(
                                f"ID: {agent_id}",
                                style={"fontSize": "0.7rem", "color": "var(--text-muted)"},
                            ),
                        ]
                    ),
                    html.Td(html.Span(status_text, className=f"badge-status {status_class}")),
                    html.Td(
                        f"sk-••••{agent_id[-4:]}",
                        style={"fontFamily": "monospace", "fontSize": "0.75rem"},
                    ),
                    html.Td(
                        [
                            html.Div(
                                style={
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "fontSize": "0.65rem",
                                    "marginBottom": "2px",
                                },
                                children=[
                                    html.Span(f"${spend:.2f}"),
                                    html.Span(
                                        f"/ {monthly_budget:.0f}",
                                        style={"color": "var(--text-muted)"},
                                    ),
                                ],
                            ),
                            html.Div(
                                className="budget-bar-table",
                                children=[
                                    html.Div(
                                        className="budget-bar-fill",
                                        style={
                                            "width": f"{budget_pct}%",
                                            "backgroundColor": "var(--danger)"
                                            if budget_pct > 90
                                            else "var(--accent-blue)",
                                        },
                                    )
                                ],
                            ),
                        ]
                    ),
                    html.Td(model_tags),
                    html.Td(
                        dcc.Graph(
                            figure=sparkline_fig,
                            config={"displayModeBar": False, "staticPlot": True},
                        ),
                        style={"width": "100px"},
                    ),
                ],
            )
        )

    return html.Div(
        className="animated-fade-in",
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-end",
                    "marginBottom": "24px",
                },
                children=[
                    html.Div(
                        [
                            html.H1("AI Agents Registry", style={"margin": "0"}),
                            html.P(
                                "Enterprise-grade registry of all active internal agent probes",
                                style={"color": "var(--text-muted)", "fontSize": "0.85rem"},
                            ),
                        ]
                    ),
                    html.Button(
                        "+ Register New Agent", id="open-register-agent", className="btn-premium"
                    ),
                ],
            ),
            # Aggregate Metrics Summary
            html.Div(
                className="metrics-grid",
                children=[
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Total Registry", className="metric-label"),
                            html.Div(className="metric-value", children=str(total_agents)),
                        ],
                    ),
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Active Probes (1h)", className="metric-label"),
                            html.Div(
                                className="metric-value",
                                children=[
                                    str(active_in_hour),
                                    html.Span(
                                        "↘ 2%",
                                        className="metric-trend",
                                        style={"color": "var(--success)"},
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Est. Monthly Spend", className="metric-label"),
                            html.Div(
                                className="metric-value",
                                children=[
                                    f"${total_spend:.2f}",
                                    html.Span(
                                        "↑ 8%",
                                        className="metric-trend",
                                        style={"color": "var(--danger)"},
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Global Efficiency", className="metric-label"),
                            html.Div(className="metric-value", children=f"{success_rate:.1f}%"),
                        ],
                    ),
                ],
            ),
            # Registry High-Density Table
            html.Div(
                id="agents-container",  # Restored for callback compatibility
                className="card",
                style={
                    "padding": "0",
                    "overflow": "hidden",
                    "border": "1px solid var(--card-border)",
                },
                children=[
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Agent Identity"),
                                        html.Th("Status"),
                                        html.Th("Master API Key"),
                                        html.Th("Monthly Quota ($)"),
                                        html.Th("Capability Scopes"),
                                        html.Th("Health (24h)"),
                                    ]
                                )
                            ),
                            html.Tbody(agent_rows),
                        ],
                    )
                ],
            ),
            html.Div(
                id="creation-status", style={"display": "none"}
            ),  # Restored for callback compatibility
        ],
    )


def get_agent_stats_view(agent_id, time_range="24h"):
    db = SessionLocal()
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        db.close()
        return html.Div("Agent not found.")

    delta = get_time_delta(time_range)
    query = db.query(AuditLog).filter(AuditLog.agent_id == agent_id)
    if delta:
        query = query.filter(AuditLog.timestamp >= delta)

    logs = query.order_by(AuditLog.timestamp.desc()).all()
    db.close()

    if not logs:
        return html.Div(
            [
                html.Button(
                    "← Back", id={"type": "back-btn", "index": "agents"}, className="btn-premium"
                ),
                html.H1(f"Deep Inspection: {agent.name}"),
                html.P("No data available."),
            ],
            className="animated",
        )

    df = pd.DataFrame(
        [
            {
                "timestamp": entry.timestamp,
                "status": entry.response_status,
                "latency": entry.latency_ms or 0,
                "tokens": entry.total_tokens or 0,
                "service": entry.target_service,
                "details": entry.request_details,
            }
            for entry in logs
        ]
    )

    total_tokens = df["tokens"].sum()

    # Log Rows
    log_rows = []
    for i, row in df.head(10).iterrows():
        log_rows.append(
            html.Tr(
                id={"type": "inspect-row", "index": i},
                n_clicks=0,
                className="clickable-row",
                children=[
                    html.Td(row["timestamp"].strftime("%H:%M:%S")),
                    html.Td(row["service"]),
                    html.Td(
                        row["status"],
                        style={
                            "color": "var(--success)" if row["status"] == 200 else "var(--danger)",
                            "fontWeight": "bold",
                        },
                    ),
                    html.Td(f"{int(row['latency'])}ms"),
                    html.Td(f"{int(row['tokens']):,}" if row["tokens"] > 0 else "-"),
                ],
            )
        )

    return html.Div(
        className="animated",
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "16px",
                    "marginBottom": "24px",
                },
                children=[
                    html.Button(
                        "←",
                        id={"type": "back-btn", "index": "agents"},
                        className="btn-premium",
                        style={"borderRadius": "50%", "width": "36px", "height": "36px"},
                    ),
                    html.H1(f"Deep Inspection: {agent.name}", style={"margin": "0"}),
                ],
            ),
            html.Div(
                className="metrics-grid",
                children=[
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Token Efficiency", className="metric-label"),
                            html.Div(className="metric-value", children=f"{int(total_tokens):,}"),
                        ],
                    ),
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Monthly Spend", className="metric-label"),
                            html.Div(
                                className="metric-value",
                                children=f"${df['tokens'].sum() * 0.0000003:.4f}"
                                if not df.empty
                                else "$0.00",
                            ),
                        ],
                    ),
                ],
            ),
            # Budget Progress Card (New)
            html.Div(
                className="card",
                style={"marginBottom": "20px"},
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "marginBottom": "10px",
                        },
                        children=[
                            html.H3("Budget Utilization", style={"margin": "0"}),
                            html.Span(
                                f"Limit: ${agent.monthly_budget_usd:.2f}"
                                if agent.monthly_budget_usd
                                else "No Limit",
                                style={"fontWeight": "600"},
                            ),
                        ],
                    ),
                    html.Div(
                        className="progress-container",
                        children=[
                            html.Div(
                                className="progress-bar"
                                + (
                                    " bg-danger"
                                    if (
                                        df["tokens"].sum()
                                        * 0.0000003
                                        / (agent.monthly_budget_usd or 1)
                                    )
                                    > 0.9
                                    else ""
                                ),
                                style={
                                    "width": f"{min(100, (df['tokens'].sum() * 0.0000003 / (agent.monthly_budget_usd or 0.01)) * 100)}%"
                                }
                                if agent.monthly_budget_usd
                                else {"width": "0%"},
                            )
                        ],
                    )
                    if agent.monthly_budget_usd
                    else html.P(
                        "Set a budget to track quotas.",
                        style={"fontSize": "0.85rem", "color": "var(--text-muted)"},
                    ),
                ],
            ),
            html.Div(
                className="card",
                children=[
                    html.H3("Recent Activity Logs"),
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Time"),
                                        html.Th("Service"),
                                        html.Th("Status"),
                                        html.Th("Latency"),
                                        html.Th("Tokens"),
                                    ]
                                )
                            ),
                            html.Tbody(log_rows),
                        ],
                    ),
                    html.Div(
                        id="json-inspector-panel",
                        style={"display": "none", "marginTop": "20px"},
                        children=[
                            html.H4("Audit Payload Details", style={"marginBottom": "12px"}),
                            html.Pre(id="json-content", className="inspector-panel"),
                        ],
                    ),
                ],
            ),
        ],
    )


def get_logs_view():
    db = SessionLocal()
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    db.close()

    rows = []
    for log_entry in logs:
        rows.append(
            html.Tr(
                [
                    html.Td(log_entry.timestamp.strftime("%Y-%m-%d %H:%M")),
                    html.Td(f"Agent #{log_entry.agent_id}"),
                    html.Td(str(log_entry.target_service)),
                    html.Td(int(log_entry.response_status)),
                    html.Td(f"{log_entry.latency_ms}ms" if log_entry.latency_ms else "-"),
                    html.Td(
                        (str(log_entry.request_details)[:50] + "...")
                        if log_entry.request_details
                        else "-"
                    ),
                ]
            )
        )

    return html.Div(
        className="animated",
        children=[
            html.H1("Global Audit Logs"),
            html.Div(
                className="card",
                children=[
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Timestamp"),
                                        html.Th("Agent"),
                                        html.Th("Service"),
                                        html.Th("Status"),
                                        html.Th("Latency"),
                                        html.Th("Snippet"),
                                    ]
                                )
                            ),
                            html.Tbody(rows),
                        ],
                    )
                ],
            ),
        ],
    )


SUPPORTED_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "desc": "GPT-4 & GPT-3.5",
        "type": "llm",
        "version": "v4.0.1",
        "region": "us-east-1",
    },
    "anthropic": {
        "name": "Anthropic",
        "desc": "Claude 3 Opus & Sonnet",
        "type": "llm",
        "version": "v3.0.0",
        "region": "us-west-2",
    },
    "gemini": {
        "name": "Google Gemini",
        "desc": "Gemini 1.5 Pro",
        "type": "llm",
        "version": "v1.5.0",
        "region": "global",
    },
    "cohere": {
        "name": "Cohere",
        "desc": "Command R+",
        "type": "llm",
        "version": "v2.1.0",
        "region": "us-central-1",
    },
    "mistral": {
        "name": "Mistral AI",
        "desc": "Mistral Large",
        "type": "llm",
        "version": "v1.0.0",
        "region": "eu-west-1",
    },
    "pinecone": {
        "name": "Pinecone",
        "desc": "Serverless vector DB",
        "type": "vector",
        "version": "v2.1.0 (Active)",
        "region": "us-east-1 (AWS)",
    },
}

# SVG paths for icons
PROVIDER_ICONS = {
    "openai": "M15.35 11c0 1.25-1.02 2.22-2.22 2.22s-2.22-1.02-2.22-2.22v-.41c0-1.25 1.02-2.22 2.22-2.22s2.22 1.02 2.22 2.22v.41zm-6.67 0c0 1.25-1.02 2.22-2.22 2.22s-2.22-1.02-2.22-2.22v-.41c0-1.25 1.02-2.22 2.22-2.22s2.22 1.02 2.22 2.22v.41zm6.67 4.44c0 1.25-1.02 2.22-2.22 2.22s-2.22-1.02-2.22-2.22v-.41c0-1.25 1.02-2.22 2.22-2.22s2.22 1.02 2.22 2.22v.41z",
    "anthropic": "M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z",
    "gemini": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z",
    "cohere": "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
    "mistral": "M12.89 3L5 21h3.39l1.61-4.67h4l1.61 4.67H19l-7.89-18h-1.22zM11 13l1-3 1 3h-2z",
    "pinecone": "M12 3L2 12h3v9h6v-6h2v6h6v-9h3L12 3z",
}


def get_icon(name, size=24):
    icon_map = {
        "openai": "bi bi-cpu-fill",
        "anthropic": "bi bi-robot",
        "gemini": "bi bi-stars",
        "cohere": "bi bi-box",
        "mistral": "bi bi-wind",
        "pinecone": "bi bi-database-fill",
    }
    icon_class = icon_map.get(name.lower(), "bi bi-gear-fill")
    return html.Div(
        style={
            "width": f"{size}px",
            "height": f"{size}px",
            "backgroundColor": "var(--bg-primary)",
            "borderRadius": "8px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "marginRight": "12px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
            "flexShrink": "0",
        },
        children=[
            html.I(
                className=icon_class,
                style={"fontSize": f"{int(size * 0.5)}px", "color": "var(--primary-color)"},
            )
        ],
    )


def get_integrations_view():
    db = SessionLocal()
    integrations = db.query(Integration).all()
    db.close()

    active_map = {i.name: i for i in integrations if i.is_active and i.provider_key}

    llm_items = []
    vector_items = []

    for key, info in SUPPORTED_PROVIDERS.items():
        is_active = key in active_map
        status_text = "Connected" if is_active else ("Setup" if key != "gemini" else "Inactive")
        status_bg = "#dcfce7" if is_active else ("#f3f4f6" if key != "gemini" else "#fee2e2")
        status_color = "#166534" if is_active else ("#4b5563" if key != "gemini" else "#991b1b")

        item_id = {"type": "integration-sidebar-item", "name": key}
        bg_color = "var(--bg-secondary)" if key == "openai" else "transparent"

        div = html.Div(
            id=item_id,
            className="integration-item",  # For hover in CSS if needed, but we use inline for now
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "12px",
                "backgroundColor": bg_color,
                "borderRadius": "12px",
                "marginBottom": "8px",
                "cursor": "pointer",
                "transition": "all 0.2s ease",
            },
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center"},
                    children=[
                        get_icon(key, size=32),
                        html.Div(
                            [
                                html.Strong(
                                    info["name"], style={"display": "block", "fontSize": "14px"}
                                ),
                                html.Span(
                                    info["desc"],
                                    style={"fontSize": "12px", "color": "var(--text-muted)"},
                                ),
                            ]
                        ),
                    ],
                ),
                html.Span(
                    status_text,
                    style={
                        "backgroundColor": status_bg,
                        "color": status_color,
                        "padding": "2px 10px",
                        "borderRadius": "20px",
                        "fontSize": "11px",
                        "fontWeight": "bold",
                    },
                ),
            ],
        )

        if info["type"] == "llm":
            llm_items.append(div)
        else:
            vector_items.append(div)

    return html.Div(
        className="animated-fade-in",
        style={
            "display": "flex",
            "height": "calc(100vh - 100px)",
            "gap": "20px",
            "padding": "10px",
        },
        children=[
            # Left Pane: Services Sidebar
            html.Div(
                style={
                    "width": "300px",
                    "borderRight": "1px solid var(--border-color)",
                    "paddingRight": "20px",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "24px",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "borderBottom": "1px solid var(--border-color)",
                            "paddingBottom": "12px",
                        },
                        children=[
                            html.H3(
                                "Services' Sidebar",
                                style={"margin": "0", "fontSize": "16px", "fontWeight": "700"},
                            ),
                            html.Span(
                                "280px", style={"color": "var(--text-muted)", "fontSize": "12px"}
                            ),
                        ],
                    ),
                    html.Div(
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "center",
                                    "marginBottom": "12px",
                                },
                                children=[
                                    html.H4(
                                        "LARGE LANGUAGE MODELS",
                                        style={
                                            "fontSize": "11px",
                                            "color": "var(--text-muted)",
                                            "letterSpacing": "1px",
                                            "margin": "0",
                                        },
                                    ),
                                    html.Span(
                                        "12 Active",
                                        style={"fontSize": "11px", "color": "var(--text-muted)"},
                                    ),
                                ],
                            ),
                            *llm_items,
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "center",
                                    "marginBottom": "12px",
                                    "marginTop": "10px",
                                },
                                children=[
                                    html.H4(
                                        "VECTOR DATABASES",
                                        style={
                                            "fontSize": "11px",
                                            "color": "var(--text-muted)",
                                            "letterSpacing": "1px",
                                            "margin": "0",
                                        },
                                    ),
                                    html.Span(
                                        "5 Active",
                                        style={"fontSize": "11px", "color": "var(--text-muted)"},
                                    ),
                                ],
                            ),
                            *vector_items,
                        ]
                    ),
                ],
            ),
            # Right Pane: Detailed Configuration Container
            html.Div(
                id="integration-details-pane",
                style={
                    "flex": "1",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "24px",
                    "padding": "0 20px",
                    "overflowY": "auto",
                },
                children=[],
            ),
        ],
    )


def get_inventory_view():
    db = SessionLocal()
    models = db.query(ModelPricing).order_by(ModelPricing.model_name).all()
    db.close()

    rows = []
    for m in models:
        rows.append(
            html.Tr(
                [
                    html.Td(str(m.model_name), style={"fontWeight": "bold"}),
                    html.Td(f"${m.input_1m_price:.4f}"),
                    html.Td(f"${m.output_1m_price:.4f}"),
                ]
            )
        )

    return html.Div(
        className="animated",
        children=[
            html.H1("Model Registry"),
            # Add Model Form
            html.Div(
                className="card",
                style={"marginBottom": "20px"},
                children=[
                    html.H3("Add or Update Model Pricing"),
                    html.Div(
                        style={"display": "flex", "gap": "15px", "alignItems": "flex-end"},
                        children=[
                            html.Div(
                                style={"flex": "1"},
                                children=[
                                    html.Label("Model Name (e.g., gpt-4o)", className="nav-label"),
                                    dcc.Input(
                                        id="new-model-name",
                                        type="text",
                                        className="custom-dropdown",
                                        style={"width": "100%", "padding": "10px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": "1"},
                                children=[
                                    html.Label("Input Price / 1M ($)", className="nav-label"),
                                    dcc.Input(
                                        id="new-model-in-price",
                                        type="number",
                                        min="0",
                                        step="0.0001",
                                        className="custom-dropdown",
                                        style={"width": "100%", "padding": "10px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": "1"},
                                children=[
                                    html.Label("Output Price / 1M ($)", className="nav-label"),
                                    dcc.Input(
                                        id="new-model-out-price",
                                        type="number",
                                        min="0",
                                        step="0.0001",
                                        className="custom-dropdown",
                                        style={"width": "100%", "padding": "10px"},
                                    ),
                                ],
                            ),
                            html.Button(
                                "Save Pricing",
                                id="save-model-btn",
                                n_clicks=0,
                                className="btn-premium",
                                style={"padding": "12px 24px"},
                            ),
                        ],
                    ),
                    html.Div(
                        id="model-save-status",
                        style={"marginTop": "15px", "color": "var(--success)"},
                    ),
                ],
            ),
            # Models Table
            html.Div(
                className="card",
                children=[
                    html.H3("Registered Models"),
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Model Name"),
                                        html.Th("Input Price / 1M tokens"),
                                        html.Th("Output Price / 1M tokens"),
                                    ]
                                )
                            ),
                            html.Tbody(rows),
                        ],
                    ),
                ],
            ),
        ],
    )


def get_alerts_view() -> html.Div:
    """Render the Alert Rules management view.

    Displays all active ``AlertRule`` records in a table and provides a form
    to create new rules or delete existing ones.  Also shows the last 20
    ``AlertEvent`` records so admins can confirm notification delivery.

    Returns
    -------
        A Dash ``html.Div`` containing the full alerts management UI.

    """
    db = SessionLocal()
    agents = db.query(Agent).all()
    rules = db.query(AlertRule).order_by(AlertRule.created_at.desc()).all()
    events = db.query(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(20).all()
    db.close()

    agent_map: dict[int, str] = {int(a.id): str(a.name) for a in agents}  # type: ignore[arg-type]

    # --- Rules table ---
    rule_rows = []
    for rule in rules:
        scope = agent_map.get(int(rule.agent_id), "Global") if rule.agent_id else "Global"  # type: ignore[arg-type]
        status_class = "status-active" if rule.is_active else "status-error"
        rule_rows.append(
            html.Tr(
                [
                    html.Td(str(rule.id), style={"color": "var(--text-muted)"}),
                    html.Td(scope, style={"fontWeight": "600"}),
                    html.Td(f"{rule.threshold_pct}%"),
                    html.Td(str(rule.channel).capitalize()),
                    html.Td(
                        str(rule.destination or "—"),
                        style={
                            "fontSize": "0.8rem",
                            "color": "var(--text-muted)",
                            "wordBreak": "break-all",
                        },
                    ),
                    html.Td(
                        html.Div(
                            className=f"status-pill {status_class}",
                            children=["Active" if rule.is_active else "Inactive"],
                        )
                    ),
                    html.Td(
                        html.Button(
                            "Delete",
                            id={"type": "delete-alert-btn", "index": int(rule.id)},  # type: ignore[arg-type]
                            n_clicks=0,
                            className="btn-premium",
                            style={"padding": "4px 10px", "fontSize": "0.75rem"},
                        )
                    ),
                ]
            )
        )

    # --- Events table ---
    event_rows = []
    for ev in events:
        scope = agent_map.get(int(ev.agent_id), "Global") if ev.agent_id else "Global"  # type: ignore[arg-type]
        delivered_icon = "✅" if ev.delivered else "❌"
        event_rows.append(
            html.Tr(
                [
                    html.Td(ev.triggered_at.strftime("%Y-%m-%d %H:%M") if ev.triggered_at else "—"),
                    html.Td(scope),
                    html.Td(f"{ev.current_pct:.1f}%"),
                    html.Td(str(ev.message or "—"), style={"fontSize": "0.8rem"}),
                    html.Td(delivered_icon, style={"textAlign": "center"}),
                ]
            )
        )

    agent_options = [{"label": "Global (all agents)", "value": ""}] + [
        {"label": str(a.name), "value": str(a.id)} for a in agents
    ]

    return html.Div(
        className="animated",
        children=[
            html.H1("Alert Rules"),
            # New rule form
            html.Div(
                className="card",
                style={"marginBottom": "20px", "border": "1px dashed var(--primary)"},
                children=[
                    html.H3("Create New Alert Rule"),
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "15px",
                            "alignItems": "flex-end",
                            "flexWrap": "wrap",
                        },
                        children=[
                            html.Div(
                                style={"flex": "1", "minWidth": "160px"},
                                children=[
                                    html.Label("Agent (optional)", className="nav-label"),
                                    dcc.Dropdown(
                                        id="alert-agent-select",
                                        options=agent_options,
                                        value="",
                                        clearable=False,
                                        style={"fontSize": "0.85rem"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": "1", "minWidth": "140px"},
                                children=[
                                    html.Label("Threshold (%)", className="nav-label"),
                                    dcc.Dropdown(
                                        id="alert-threshold-select",
                                        options=[
                                            {"label": "80% — Warning", "value": 80},
                                            {"label": "90% — Critical", "value": 90},
                                            {"label": "100% — Hard limit", "value": 100},
                                        ],
                                        value=80,
                                        clearable=False,
                                        style={"fontSize": "0.85rem"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": "1", "minWidth": "140px"},
                                children=[
                                    html.Label("Channel", className="nav-label"),
                                    dcc.Dropdown(
                                        id="alert-channel-select",
                                        options=[
                                            {"label": "📋 Log (server)", "value": "log"},
                                            {"label": "🔗 Webhook", "value": "webhook"},
                                            {"label": "💬 Slack", "value": "slack"},
                                        ],
                                        value="log",
                                        clearable=False,
                                        style={"fontSize": "0.85rem"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": "2", "minWidth": "200px"},
                                children=[
                                    html.Label(
                                        "Destination URL (webhook / Slack)", className="nav-label"
                                    ),
                                    dcc.Input(
                                        id="alert-destination-input",
                                        type="url",
                                        placeholder="https://hooks.slack.com/services/…",
                                        className="enterprise-input",
                                        style={"width": "100%"},
                                    ),
                                ],
                            ),
                            html.Button(
                                "Save Rule",
                                id="save-alert-btn",
                                n_clicks=0,
                                className="btn-premium",
                                style={"padding": "10px 24px"},
                            ),
                        ],
                    ),
                    html.Div(
                        id="alert-save-status", style={"marginTop": "12px", "fontSize": "0.85rem"}
                    ),
                ],
            ),
            # Rules table
            html.Div(
                className="card",
                style={"marginBottom": "20px"},
                children=[
                    html.H3("Active Rules"),
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("#"),
                                        html.Th("Scope"),
                                        html.Th("Threshold"),
                                        html.Th("Channel"),
                                        html.Th("Destination"),
                                        html.Th("Status"),
                                        html.Th("Actions"),
                                    ]
                                )
                            ),
                            html.Tbody(
                                rule_rows
                                if rule_rows
                                else [
                                    html.Tr(
                                        [
                                            html.Td(
                                                "No rules configured yet.",
                                                colSpan=7,
                                                style={
                                                    "textAlign": "center",
                                                    "color": "var(--text-muted)",
                                                },
                                            )
                                        ]
                                    )
                                ]
                            ),
                        ],
                    ),
                    html.Div(
                        id="alert-delete-status", style={"marginTop": "8px", "fontSize": "0.85rem"}
                    ),
                ],
            ),
            # Event history
            html.Div(
                className="card",
                children=[
                    html.H3("Recent Alert Events"),
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Triggered At"),
                                        html.Th("Agent"),
                                        html.Th("Spend %"),
                                        html.Th("Message"),
                                        html.Th("Delivered"),
                                    ]
                                )
                            ),
                            html.Tbody(
                                event_rows
                                if event_rows
                                else [
                                    html.Tr(
                                        [
                                            html.Td(
                                                "No events yet.",
                                                colSpan=5,
                                                style={
                                                    "textAlign": "center",
                                                    "color": "var(--text-muted)",
                                                },
                                            )
                                        ]
                                    )
                                ]
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def serve_layout():
    return html.Div(
        className="app-container",
        children=[
            get_sidebar(),
            html.Div(
                className="main-wrapper",
                children=[
                    get_top_header(),
                    html.Div(
                        id="page-content", className="main-content", children=get_dashboard_view()
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
    if not triggered_id or triggered_id == "nav-dashboard" or triggered_id == "global-time-filter":
        if active_agent_id:
            return get_agent_stats_view(active_agent_id, time_range), active_agent_id
        return get_dashboard_view(time_range), None

    if isinstance(triggered_id, dict):
        if triggered_id.get("type") in ["stats-btn", "agent-row", "agent-card"]:
            agent_id = triggered_id["index"]
            return get_agent_stats_view(agent_id, time_range), agent_id
        if triggered_id.get("type") == "back-btn" and triggered_id.get("index") == "agents":
            return get_agents_view(), None
        return get_dashboard_view(time_range), None

    # Handle sidebar links
    if "nav-logs" in triggered_prop_id:
        return get_logs_view(), None
    if "nav-integrations" in triggered_prop_id:
        return get_integrations_view(), None
    if "nav-agents" in triggered_prop_id:
        return get_agents_view(), None
    if "nav-inventory" in triggered_prop_id:
        return get_inventory_view(), None
    if "nav-alerts" in triggered_prop_id:
        return get_alerts_view(), None

    return get_dashboard_view(time_range), None


@app.callback(
    Output("page-content", "children"),
    Output("active-agent-id", "data"),
    Input("nav-dashboard", "n_clicks"),
    Input("nav-agents", "n_clicks"),
    Input("nav-integrations", "n_clicks"),
    Input("nav-logs", "n_clicks"),
    Input("nav-inventory", "n_clicks"),
    Input("nav-alerts", "n_clicks"),
    Input({"type": "back-btn", "index": ALL}, "n_clicks"),
    Input({"type": "stats-btn", "index": ALL}, "n_clicks"),
    Input({"type": "agent-row", "index": ALL}, "n_clicks"),
    Input({"type": "agent-card", "index": ALL}, "n_clicks"),
    Input("global-time-filter", "value"),
    State("active-agent-id", "data"),
    prevent_initial_call=False,
)
def render_page(
    dash_clicks,
    agents_clicks,
    int_clicks,
    logs_clicks,
    inv_clicks,
    alerts_clicks,
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
    updated_view = get_agents_view()
    # Corrected indexing: 0: Header, 1: Metrics, 2: AgentsTable/Card, 3: CreationStatus
    return updated_view.children[2].children, status_msg


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
        return get_agents_view(), ""
    except Exception as e:
        db.rollback()
        db.close()
        return dash.no_update, f"❌ Error: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    app.run_server(debug=True, port=8000)
