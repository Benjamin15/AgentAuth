"""Dashboard pages for AgentAuth.

This package uses a registry for automatic discovery of full-page views.
"""

from ...core.registry import Registry
from ..base import BasePage

page_registry = Registry[BasePage]("dashboard_pages")


def get_registered_pages() -> list[type[BasePage]]:
    """Return all registered page classes, sorted by their priority."""
    # Ensure all modules are loaded.
    page_registry.discover("agentauth.dashboard.pages")

    # Sort them by section (using a custom order) and then priority.
    section_order = {"Core": 1, "Analytics": 2, "Models": 3, "Settings": 4}
    pages = list(page_registry.list_all().values())
    return sorted(pages, key=lambda p: (section_order.get(p.section, 99), p.priority))


__all__ = ["BasePage", "page_registry", "get_registered_pages"]
