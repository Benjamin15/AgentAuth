from typing import Any

from dash import html

from ...core.database import SessionLocal
from ...core.models import AuditLog
from ..base import BasePage
from . import page_registry


@page_registry.register("logs")
class LogsPage(BasePage):
    label = "Audit Logs"
    icon = "file-earmark-text"
    section = "Analytics"
    priority = 1

    def render(self, **kwargs: Any) -> html.Div:
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
            className="animated-fade-in",
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
