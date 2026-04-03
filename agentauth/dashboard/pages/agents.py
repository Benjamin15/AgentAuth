import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

from ...core.database import SessionLocal
from ...core.models import Agent, AuditLog
from ..base import BasePage
from ..utils import get_time_delta
from . import page_registry


@page_registry.register("agents")
class AgentsPage(BasePage):
    label = "Agents"
    icon = "robot"
    section = "Core"
    priority = 2

    def render(self, **kwargs: Any) -> html.Div:
        active_agent_id = kwargs.get("active_agent_id")
        time_range = kwargs.get("time_range", "24h")

        if active_agent_id:
            return self._render_stats(active_agent_id, time_range)
        return self._render_list()

    def _render_list(self) -> html.Div:
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
                            "+ Register New Agent",
                            id="open-register-agent",
                            className="btn-premium",
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
                    id="agents-container",
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
                html.Div(id="creation-status", style={"display": "none"}),
            ],
        )

    def _render_stats(self, agent_id: str, time_range: str = "24h") -> html.Div:
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
                        "← Back",
                        id={"type": "back-btn", "index": "agents"},
                        className="btn-premium",
                    ),
                    html.H1(f"Deep Inspection: {agent.name}"),
                    html.P("No data available."),
                ],
                className="animated-fade-in",
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
                                "color": "var(--success)"
                                if row["status"] == 200
                                else "var(--danger)",
                                "fontWeight": "bold",
                            },
                        ),
                        html.Td(f"{int(row['latency'])}ms"),
                        html.Td(f"{int(row['tokens']):,}" if row["tokens"] > 0 else "-"),
                    ],
                )
            )

        return html.Div(
            className="animated-fade-in",
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
                                html.Div(
                                    className="metric-value", children=f"{int(total_tokens):,}"
                                ),
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
