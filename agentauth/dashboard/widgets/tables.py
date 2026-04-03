from typing import Any

from dash import html

from ..base import BaseWidget
from . import widget_registry


@widget_registry.register("agent_status_table")
class AgentStatusTableWidget(BaseWidget):
    priority = 80
    group = "card"

    def render(self, data: Any) -> html.Div:
        logs = data.get("logs", [])
        agents = data.get("agents", [])

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
                                children=[
                                    html.Div(className=f"status-dot {status_dot}"),
                                    status_text,
                                ],
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
        )
