from typing import Any

import pandas as pd
from dash import html

from ..base import BaseWidget
from . import widget_registry


@widget_registry.register("total_requests")
class TotalRequestsWidget(BaseWidget):
    priority = 10
    group = "metric"

    def render(self, data: Any) -> html.Div:
        df = data.get("df", pd.DataFrame())
        total_reqs = len(df)

        return html.Div(
            className="metric-card",
            children=[
                html.Span("Total Requests", className="metric-label"),
                html.Div(
                    className="metric-value",
                    children=[
                        f"{total_reqs:,}",
                        html.Span(
                            "↗ 5%", className="metric-trend", style={"color": "var(--success)"}
                        ),
                    ],
                ),
            ],
        )


@widget_registry.register("avg_latency")
class AverageLatencyWidget(BaseWidget):
    priority = 20
    group = "metric"

    def render(self, data: Any) -> html.Div:
        df = data.get("df", pd.DataFrame())
        avg_latency = df["latency"].mean() if not df.empty else 0

        return html.Div(
            className="metric-card",
            children=[
                html.Span("Avg Latency", className="metric-label"),
                html.Div(
                    className="metric-value",
                    children=[
                        f"{int(avg_latency)}ms",
                        html.Span(
                            "↘ 2%", className="metric-trend", style={"color": "var(--success)"}
                        ),
                    ],
                ),
            ],
        )


@widget_registry.register("active_agents")
class ActiveAgentsWidget(BaseWidget):
    priority = 30
    group = "metric"

    def render(self, data: Any) -> html.Div:
        agents = data.get("agents", [])
        active_count = len([a for a in agents if not a.is_frozen])

        return html.Div(
            className="metric-card",
            children=[
                html.Span("Active Agents", className="metric-label"),
                html.Div(
                    className="metric-value",
                    children=f"{active_count}/{len(agents)}",
                ),
            ],
        )


@widget_registry.register("monthly_spend")
class MonthlySpendWidget(BaseWidget):
    priority = 40
    group = "metric"

    def render(self, data: Any) -> html.Div:
        df = data.get("df", pd.DataFrame())
        total_spend = df["cost"].sum() if not df.empty else 0

        return html.Div(
            className="metric-card",
            children=[
                html.Span("Monthly Spend", className="metric-label"),
                html.Div(
                    className="metric-value",
                    children=[
                        f"${total_spend:.2f}",
                        html.Span(
                            "↑ 8%", className="metric-trend", style={"color": "var(--danger)"}
                        ),
                    ],
                ),
            ],
        )
