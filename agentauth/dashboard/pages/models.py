from typing import Any

from dash import dcc, html

from ...core.database import SessionLocal
from ...core.models import ModelPricing
from ..base import BasePage
from . import page_registry


@page_registry.register("models")
class ModelsPage(BasePage):
    label = "Inventory"
    icon = "tags"
    section = "Models"
    priority = 1

    def render(self, **kwargs: Any) -> html.Div:
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
            className="animated-fade-in",
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
                                        html.Label(
                                            "Model Name (e.g., gpt-4o)", className="nav-label"
                                        ),
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


@page_registry.register("performance")
class PerformancePage(BasePage):
    label = "Performance"
    icon = "bolt"
    section = "Models"
    priority = 2

    def render(self, **kwargs: Any) -> html.Div:
        return html.Div(
            className="animated-fade-in",
            children=[
                html.H1("Model Performance"),
                html.P(
                    "Detailed latency and throughput metrics across all registered AI integrations.",
                    style={"color": "var(--text-muted)"},
                ),
                html.Div(
                    className="card",
                    style={
                        "height": "300px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                    },
                    children=[html.P("Metrics aggregation in progress...", className="pulsate")],
                ),
            ],
        )
