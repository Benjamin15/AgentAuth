from typing import Any

from dash import html

from ...core.database import SessionLocal
from ...core.models import Integration
from ..base import BasePage
from ..utils import SUPPORTED_PROVIDERS, get_icon
from . import page_registry


@page_registry.register("integrations")
class IntegrationsPage(BasePage):
    label = "Integrations"
    icon = "puzzle"
    section = "Core"
    priority = 3

    def render(self, **kwargs: Any) -> html.Div:
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
            # Note: The active background color will be handled by the update_active_integration callback
            bg_color = "transparent"

            div = html.Div(
                id=item_id,
                className="integration-item",
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
                                    "280px",
                                    style={"color": "var(--text-muted)", "fontSize": "12px"},
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
                                            style={
                                                "fontSize": "11px",
                                                "color": "var(--text-muted)",
                                            },
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
                                            style={
                                                "fontSize": "11px",
                                                "color": "var(--text-muted)",
                                            },
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
