"""Dashboard widgets for AgentAuth.

This package uses a registry for automatic discovery of UI components.
"""

from ...core.registry import Registry
from ..base import BaseWidget

widget_registry = Registry[BaseWidget]("dashboard_widgets")


def get_registered_widgets() -> list[type[BaseWidget]]:
    """Return all registered widget classes, sorted by their priority."""
    # Ensure all modules are loaded.
    widget_registry.discover("agentauth.dashboard.widgets")

    # Sort them by priority. Lower number = higher on the page.
    widgets = list(widget_registry.list_all().values())
    return sorted(widgets, key=lambda w: w.priority)


__all__ = ["BaseWidget", "widget_registry", "get_registered_widgets"]
