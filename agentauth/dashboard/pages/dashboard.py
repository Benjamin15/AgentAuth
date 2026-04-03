from typing import Any

import pandas as pd
from dash import html

from ...core.database import SessionLocal
from ...core.models import Agent, AuditLog
from ..base import BasePage
from ..utils import get_time_delta
from ..widgets import get_registered_widgets
from . import page_registry


@page_registry.register("dashboard")
class DashboardPage(BasePage):
    label = "Dashboard"
    icon = "house-door"
    section = "Core"
    priority = 1

    def render(self, **kwargs: Any) -> html.Div:
        time_range = kwargs.get("time_range", "24h")
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
                className="animated-fade-in",
                children=[
                    html.H1("AI Observability Dashboard"),
                    html.P(f"No data for range '{time_range}'"),
                ],
            )

        # 2. Build Data Context for Widgets
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
            className="animated-fade-in",
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
                html.Div(
                    className="chart-row", style={"marginBottom": "20px"}, children=chart_widgets
                ),
                # Main Cards (Bottom section: Heatmaps, tables, etc.)
                html.Div(children=card_widgets),
            ],
        )
