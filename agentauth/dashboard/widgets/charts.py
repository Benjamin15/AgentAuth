from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from ..base import BaseWidget
from . import widget_registry


@widget_registry.register("spend_dist")
class SpendDistWidget(BaseWidget):
    priority = 50
    group = "chart"

    def render(self, data: Any) -> html.Div:
        df = data.get("df", pd.DataFrame())
        agents = data.get("agents", [])
        agent_map = {a.id: a.name for a in agents}

        if df.empty:
            fig = go.Figure()
        else:
            df["agent_name"] = df["agent_id"].map(agent_map)
            spend_by_agent = df.groupby("agent_name")["cost"].sum().reset_index()
            spend_by_agent = spend_by_agent[spend_by_agent["cost"] > 0].sort_values(
                "cost", ascending=True
            )

            if spend_by_agent.empty:
                fig = go.Figure()
                fig.add_annotation(text="No spending data", showarrow=False)
            else:
                fig = px.bar(
                    spend_by_agent,
                    x="cost",
                    y="agent_name",
                    orientation="h",
                    template="plotly_white",
                    color="cost",
                    color_continuous_scale="Tealgrn",
                )
                fig.update_layout(
                    margin={"l": 10, "r": 40, "t": 10, "b": 10},
                    height=180,
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis={"showgrid": False, "showticklabels": False},
                    yaxis={"title": None, "tickfont": {"size": 11, "weight": "bold"}},
                    coloraxis_showscale=False,
                )

        return html.Div(
            className="card",
            children=[
                html.H3("Spend Distribution ($)"),
                dcc.Graph(figure=fig, config={"displayModeBar": False}),
            ],
        )


@widget_registry.register("error_dist")
class ErrorDistWidget(BaseWidget):
    priority = 60
    group = "chart"

    def render(self, data: Any) -> html.Div:
        df = data.get("df", pd.DataFrame())
        if df.empty:
            fig = go.Figure()
        else:
            df["hour"] = df["timestamp"].dt.floor("h")
            error_dist = df.groupby(["hour", "status"]).size().reset_index(name="count")
            fig = px.bar(
                error_dist,
                x="hour",
                y="count",
                color="status",
                template="plotly_white",
                barmode="stack",
                color_discrete_map={200: "#10b981", 401: "#f59e0b", 403: "#ef4444", 500: "#b91c1c"},
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin={"l": 30, "r": 10, "t": 5, "b": 20},
                height=180,
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 1},
            )

        return html.Div(
            className="card",
            children=[
                html.H3("Error Code Distribution"),
                dcc.Graph(figure=fig, config={"displayModeBar": False}),
            ],
        )


@widget_registry.register("latency_heat")
class LatencyHeatWidget(BaseWidget):
    priority = 70
    group = "card"

    def render(self, data: Any) -> html.Div:
        df = data.get("df", pd.DataFrame())
        agents = data.get("agents", [])
        if df.empty:
            fig = go.Figure()
        else:
            agent_map = {a.id: a.name for a in agents}
            df["agent_name"] = df["agent_id"].map(agent_map)
            df["hour"] = df["timestamp"].dt.floor("h")
            heatmap_data = df.groupby(["hour", "agent_name"])["latency"].mean().unstack().fillna(0)

            fig = go.Figure(
                data=go.Heatmap(
                    z=heatmap_data.values.T,
                    x=heatmap_data.index,
                    y=heatmap_data.columns,
                    colorscale="Viridis",
                )
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin={"l": 40, "r": 10, "t": 5, "b": 20},
                height=180,
            )

        return html.Div(
            className="card",
            style={"marginBottom": "20px"},
            children=[
                html.H3("Global Request Latency (Heatmap)"),
                dcc.Graph(figure=fig, config={"displayModeBar": False}),
            ],
        )
