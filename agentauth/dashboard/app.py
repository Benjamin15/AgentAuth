import datetime

import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

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


# Utils
def get_time_delta(time_range: str):
    now = datetime.datetime.utcnow()
    if time_range == "1h":
        return now - datetime.timedelta(hours=1)
    if time_range == "24h":
        return now - datetime.timedelta(days=1)
    if time_range == "7d":
        return now - datetime.timedelta(days=7)
    return None


app = dash.Dash(__name__, requests_pathname_prefix="/dashboard/", suppress_callback_exceptions=True)


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


def get_dashboard_view(time_range="24h"):
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
        return html.Div([html.H1("Dashboard"), html.P(f"No data for range '{time_range}'.")])

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

    # 2. Metrics
    total_reqs = len(df)
    avg_latency = df["latency"].mean() if not df.empty else 0
    active_agents_count = len([a for a in agents if not a.is_frozen])
    total_spend = df["cost"].sum() if not df.empty else 0

    # 3. Stacked Bar: Error Code Distribution
    df["hour"] = df["timestamp"].dt.floor("h")
    error_dist = df.groupby(["hour", "status"]).size().reset_index(name="count")
    fig_errors = px.bar(
        error_dist,
        x="hour",
        y="count",
        color="status",
        template="plotly_white",
        barmode="stack",
        color_discrete_map={200: "#10b981", 401: "#f59e0b", 403: "#ef4444", 500: "#b91c1c"},
    )
    fig_errors.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 30, "r": 10, "t": 5, "b": 20},
        height=180,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )

    # 4. Latency Heatmap
    # Group by agent and hour for the heatmap
    agent_map = {a.id: a.name for a in agents}
    df["agent_name"] = df["agent_id"].map(agent_map)
    heatmap_data = df.groupby(["hour", "agent_name"])["latency"].mean().unstack().fillna(0)

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=heatmap_data.values.T,
            x=heatmap_data.index,
            y=heatmap_data.columns,
            colorscale="Viridis",
        )
    )
    fig_heat.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 10, "t": 5, "b": 20},
        height=180,
    )

    # 4.5 Spend Distribution: Donut Chart (Premium SaaS Style)
    spend_by_agent = df.groupby("agent_name")["cost"].sum().reset_index()
    spend_by_agent = spend_by_agent[spend_by_agent["cost"] > 0]

    # 4.5 Spend Distribution: Horizontal Bar Chart (Fixed Labels)
    spend_by_agent = df.groupby("agent_name")["cost"].sum().reset_index()
    spend_by_agent = spend_by_agent[spend_by_agent["cost"] > 0].sort_values("cost", ascending=True)

    if spend_by_agent.empty:
        fig_spend = go.Figure()
        fig_spend.add_annotation(
            text="No spending data yet",
            showarrow=False,
            font={"size": 14, "color": "var(--text-muted)"},
        )
    else:
        fig_spend = px.bar(
            spend_by_agent,
            x="cost",
            y="agent_name",
            orientation="h",
            template="plotly_white",
            color="cost",
            color_continuous_scale="Tealgrn",
        )
        fig_spend.update_traces(
            texttemplate="$%{x:.4f}",
            textposition="auto",
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>Spend: $%{x:.4f}",
        )

    fig_spend.update_layout(
        margin={"l": 10, "r": 40, "t": 10, "b": 10},
        height=180,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "title": None,
            "tickfont": {"size": 11, "color": "var(--text-main)", "weight": "bold"},
        },
        coloraxis_showscale=False,
    )

    # 5. Agent Status Table
    agent_rows = []
    for agent in agents[:10]:
        agent_logs = [entry for entry in logs if entry.agent_id == agent.id]
        total_a_reqs = len(agent_logs)
        a_errors = len([entry for entry in agent_logs if entry.response_status >= 400])
        err_rate = (a_errors / total_a_reqs * 100) if total_a_reqs > 0 else 0

        status_class = "status-active" if not agent.is_frozen else "status-error"
        status_dot = "dot-active" if not agent.is_frozen else "dot-error"
        status_text = "Active" if not agent.is_frozen else "Frozen"

        agent_rows.append(
            html.Tr(
                id={"type": "agent-row", "index": agent.id},
                n_clicks=0,
                className="clickable-row",
                children=[
                    html.Td(str(agent.name), style={"fontWeight": "600"}),
                    html.Td("v1.5-flash", style={"color": "var(--text-muted)"}),
                    html.Td("US-East", style={"color": "var(--text-muted)"}),
                    html.Td(
                        html.Div(
                            className=f"status-pill {status_class}",
                            children=[html.Div(className=f"status-dot {status_dot}"), status_text],
                        )
                    ),
                    html.Td(f"{total_a_reqs:,}"),
                    html.Td(
                        f"{err_rate:.1f}%",
                        style={"color": "var(--danger)" if err_rate > 5 else "inherit"},
                    ),
                ],
            )
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
            # Metrics Grid
            html.Div(
                className="metrics-grid",
                children=[
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Total Requests", className="metric-label"),
                            html.Div(
                                className="metric-value",
                                children=[
                                    f"{total_reqs:,}",
                                    html.Span(
                                        "↗ 5%",
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
                            html.Span("Average Latency", className="metric-label"),
                            html.Div(
                                className="metric-value",
                                children=[
                                    f"{int(avg_latency)}ms",
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
                            html.Span("Active Agents", className="metric-label"),
                            html.Div(
                                className="metric-value",
                                children=f"{active_agents_count}/{len(agents)}",
                            ),
                        ],
                    ),
                    html.Div(
                        className="metric-card",
                        children=[
                            html.Span("Total Monthly Spend", className="metric-label"),
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
                ],
            ),
            # Charts Row 1: Spend & Errors
            html.Div(
                className="chart-row",
                style={"marginBottom": "20px"},
                children=[
                    html.Div(
                        className="card",
                        children=[
                            html.H3("Spend Distribution ($)"),
                            dcc.Graph(figure=fig_spend, config={"displayModeBar": False}),
                        ],
                    ),
                    html.Div(
                        className="card",
                        children=[
                            html.H3("Error Code Distribution"),
                            dcc.Graph(figure=fig_errors, config={"displayModeBar": False}),
                        ],
                    ),
                ],
            ),
            # Charts Row 2: Latency Heatmap
            html.Div(
                className="card",
                style={"marginBottom": "20px"},
                children=[
                    html.H3("Global Request Latency (Heatmap)"),
                    dcc.Graph(figure=fig_heat, config={"displayModeBar": False}),
                ],
            ),
            # Status Table
            html.Div(
                className="card",
                children=[
                    html.H3("AI Agents Status & Performance"),
                    html.Table(
                        className="enterprise-table",
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Agent Name"),
                                        html.Th("Model"),
                                        html.Th("Region"),
                                        html.Th("Status"),
                                        html.Th("Requests"),
                                        html.Th("Error Rate"),
                                    ]
                                )
                            ),
                            html.Tbody(agent_rows),
                        ],
                    ),
                ],
            ),
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


def get_agents_view():
    db = SessionLocal()
    agents = db.query(Agent).all()
    integrations = db.query(Integration).filter(Integration.is_active).all()
    integration_options = [{"label": i.name.capitalize(), "value": i.name} for i in integrations]
    db.close()

    creation_form = html.Div(
        className="card",
        style={"border": "1px dashed var(--primary)", "marginBottom": "30px"},
        children=[
            html.H3("Add New Enterprise Agent"),
            html.Div(
                style={"display": "flex", "gap": "15px", "marginTop": "15px"},
                children=[
                    dcc.Input(
                        id="new-agent-name",
                        placeholder="Agent Name",
                        className="enterprise-input",
                        style={"flex": "1"},
                    ),
                    dcc.Input(
                        id="new-agent-desc",
                        placeholder="Description",
                        className="enterprise-input",
                        style={"flex": "2"},
                    ),
                    html.Button("Create Agent", id="create-agent-btn", className="btn-premium"),
                ],
            ),
            html.Div(id="creation-status", style={"marginTop": "10px", "fontSize": "0.85rem"}),
        ],
    )

    agent_cards = []
    for agent in agents:
        agent_cards.append(
            html.Div(
                className="card",
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between"},
                        children=[
                            html.Div(
                                [
                                    html.H3(str(agent.name)),
                                    html.P(
                                        str(agent.description),
                                        style={"color": "var(--text-muted)", "fontSize": "0.85rem"},
                                    ),
                                ]
                            ),
                        ],
                        id={"type": "agent-card", "index": agent.id},
                        className="clickable-row",
                        n_clicks=0,
                    ),
                    html.Div(
                        style={
                            "marginTop": "15px",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "10px",
                        },
                        children=[
                            html.Label(
                                "Monthly Budget ($):",
                                style={"fontSize": "0.8rem", "fontWeight": "600"},
                            ),
                            dcc.Input(
                                id={"type": "budget-input", "index": agent.id},
                                type="number",
                                value=agent.monthly_budget_usd,
                                placeholder="None",
                                className="enterprise-input",
                                style={"width": "100px", "padding": "4px 8px"},
                            ),
                            html.Button(
                                "Set",
                                id={"type": "set-budget-btn", "index": agent.id},
                                className="btn-premium",
                                style={"padding": "4px 12px"},
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "marginTop": "15px",
                            "paddingTop": "15px",
                            "borderTop": "1px solid var(--border-color)",
                        },
                        children=[
                            html.Label(
                                "Access Control (Scopes)",
                                className="nav-label",
                                style={"padding": "0", "marginBottom": "10px"},
                            ),
                            html.Div(
                                style={"display": "flex", "gap": "10px", "alignItems": "center"},
                                children=[
                                    dcc.Dropdown(
                                        id={"type": "perm-dropdown", "index": agent.id},
                                        options=integration_options,
                                        placeholder="Select scope...",
                                        style={"flex": "1", "fontSize": "0.85rem"},
                                    ),
                                    html.Button(
                                        "Grant",
                                        id={"type": "grant-btn", "index": agent.id},
                                        className="btn-premium",
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"marginTop": "12px"},
                                children=[
                                    html.Span(
                                        "Active Permissions: ",
                                        style={"fontSize": "0.8rem", "color": "var(--text-muted)"},
                                    ),
                                    html.Span(
                                        ", ".join([p.scope for p in agent.permissions])
                                        if agent.permissions
                                        else "None",
                                        style={"fontSize": "0.8rem", "fontWeight": "600"},
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "marginTop": "15px",
                            "fontSize": "0.75rem",
                            "color": "var(--text-muted)",
                            "fontFamily": "monospace",
                        },
                        children=[
                            html.Div(f"ClientID: {agent.client_id}"),
                        ],
                    ),
                ],
            )
        )

    return html.Div(
        className="animated",
        children=[
            html.H1("AI Agents Inventory"),
            creation_form,
            html.Div(agent_cards, id="agents-container"),
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


def get_integrations_view():
    return html.Div(
        className="animated",
        children=[
            html.H1("Integrations & Providers"),
            html.Div(
                className="card",
                children=[
                    html.H3("Google Gemini"),
                    html.P("Master API Key is configured.", style={"color": "var(--success)"}),
                    html.Button("Update Key", className="btn-premium"),
                ],
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

    Returns:
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
            dcc.Interval(id="dashboard-interval", interval=30 * 1000, n_intervals=0),
            dcc.Store(id="active-agent-id", data=None),
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
    return updated_view.children[1].children, status_msg


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
        n_clicks: Number of times the Save button was clicked.
        agent_value: String agent ID from the dropdown, or empty string for global.
        threshold: Integer threshold percentage (80 | 90 | 100).
        channel: Notification channel identifier (``"log"``, ``"webhook"``, ``"slack"``).
        destination: Destination URL; may be ``None`` for the ``"log"`` channel.

    Returns:
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
        n_clicks_list: List of click counts for each delete button (pattern-match).

    Returns:
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


if __name__ == "__main__":
    app.run_server(debug=True, port=8000)
