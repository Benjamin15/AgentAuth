from typing import Any

from dash import dcc, html

from ...core.database import SessionLocal
from ...core.models import Agent, AlertEvent, AlertRule
from ..base import BasePage
from . import page_registry


@page_registry.register("alerts")
class AlertsPage(BasePage):
    label = "Alerts"
    icon = "bell"
    section = "Analytics"
    priority = 2

    def render(self, **kwargs: Any) -> html.Div:
        db = SessionLocal()
        agents = db.query(Agent).all()
        rules = db.query(AlertRule).order_by(AlertRule.created_at.desc()).all()
        events = db.query(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(20).all()
        db.close()

        agent_map: dict[int, str] = {int(a.id): str(a.name) for a in agents}

        # --- Rules table ---
        rule_rows = []
        for rule in rules:
            scope = agent_map.get(int(rule.agent_id), "Global") if rule.agent_id else "Global"
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
                                id={"type": "delete-alert-btn", "index": int(rule.id)},
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
            scope = agent_map.get(int(ev.agent_id), "Global") if ev.agent_id else "Global"
            delivered_icon = "✅" if ev.delivered else "❌"
            event_rows.append(
                html.Tr(
                    [
                        html.Td(
                            ev.triggered_at.strftime("%Y-%m-%d %H:%M") if ev.triggered_at else "—"
                        ),
                        html.Td(scope),
                        html.Td(f"{ev.current_pct:.1f}%" if ev.current_pct is not None else "—"),
                        html.Td(
                            str(ev.message),
                            style={"fontSize": "0.85rem", "color": "var(--text-muted)"},
                        ),
                        html.Td(
                            delivered_icon, style={"textAlign": "center", "fontSize": "1.1rem"}
                        ),
                    ]
                )
            )

        return html.Div(
            className="animated-fade-in",
            children=[
                html.H1("Real-time Alerting"),
                # Control Panel
                html.Div(
                    className="card",
                    style={"marginBottom": "20px"},
                    children=[
                        html.H3("Configure New Rule"),
                        html.Div(
                            style={"display": "flex", "gap": "15px", "flexWrap": "wrap"},
                            children=[
                                html.Div(
                                    style={"flex": "1", "minWidth": "200px"},
                                    children=[
                                        html.Label("Target Agent", className="nav-label"),
                                        html.Select(
                                            id="alert-agent-select",
                                            className="custom-dropdown",
                                            style={"width": "100%", "padding": "10px"},
                                            children=[
                                                html.Option("All Agents (Global)", value=""),
                                                *[
                                                    html.Option(str(a.name), value=str(a.id))
                                                    for a in agents
                                                ],
                                            ],
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={"flex": "1", "minWidth": "150px"},
                                    children=[
                                        html.Label("Threshold (%)", className="nav-label"),
                                        html.Select(
                                            id="alert-threshold-select",
                                            className="custom-dropdown",
                                            style={"width": "100%", "padding": "10px"},
                                            children=[
                                                html.Option("80% of Budget", value="80"),
                                                html.Option("90% of Budget", value="90"),
                                                html.Option("100% (Limit Reached)", value="100"),
                                            ],
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={"flex": "1", "minWidth": "150px"},
                                    children=[
                                        html.Label("Channel", className="nav-label"),
                                        html.Select(
                                            id="alert-channel-select",
                                            className="custom-dropdown",
                                            style={"width": "100%", "padding": "10px"},
                                            children=[
                                                html.Option("Internal Log", value="log"),
                                                html.Option("Webhook URL", value="webhook"),
                                                html.Option("Slack Connector", value="slack"),
                                            ],
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={"flex": "2", "minWidth": "300px"},
                                    children=[
                                        html.Label("Destination / Endpoint", className="nav-label"),
                                        dcc.Input(
                                            id="alert-destination-input",
                                            placeholder="https://hooks.slack.com/...",
                                            className="custom-dropdown",
                                            style={"width": "100%", "padding": "10px"},
                                        ),
                                    ],
                                ),
                                html.Button(
                                    "Save Rule",
                                    id="save-alert-btn",
                                    className="btn-premium",
                                    style={"alignSelf": "flex-end", "padding": "12px 24px"},
                                ),
                            ],
                        ),
                        html.Div(
                            id="alert-save-status",
                            style={"marginTop": "12px", "fontSize": "0.85rem"},
                        ),
                    ],
                ),
                # Rules table
                html.Div(
                    className="card",
                    style={"marginBottom": "20px"},
                    children=[
                        html.H3("Alert Rules"),
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
                            id="alert-delete-status",
                            style={"marginTop": "8px", "fontSize": "0.85rem"},
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
