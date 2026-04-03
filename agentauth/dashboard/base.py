from abc import ABC, abstractmethod
from typing import Any


class BaseWidget(ABC):
    """Base class for all modular dashboard components.

    Each widget is responsible for its own layout and rendering logic.
    A widget can be a simple metric card, a complex chart, or a table.
    """

    # Human-readable title for the widget (used in UI if needed).
    title: str = ""

    # Sorting priority (lower numbers appear first on the dashboard).
    priority: int = 100

    # Layout group ("metric", "chart", or "table")
    group: str = "metric"

    @abstractmethod
    def render(self, data: Any) -> Any:
        """Render the widget using the provided data dictionary.

        Args:
        ----
            data: A dictionary containing pre-fetched models, logs, and stats.

        Returns:
        -------
            A Dash component (usually html.Div or dcc.Graph).

        """
        pass

    def __repr__(self) -> str:
        """Return a string representation of the widget."""
        return f"<{self.__class__.__name__} priority={self.priority}>"


class BasePage(ABC):
    """Base class for all modular dashboard pages.

    Each page is responsible for its own layout and high-level logic.
    A page can be the main dashboard, the agents registry, settings, etc.
    """

    # User-visible label (e.g. "Dashboard", "Agents")
    label: str = ""

    # Bootstrap Icon name (e.g. "house-door", "robot")
    icon: str = "circle"

    # Sidebar section ("Core", "Analytics", "Models", "Settings")
    section: str = "Core"

    # Sorting priority within the section (lower number = higher position).
    priority: int = 100

    @abstractmethod
    def render(self, **kwargs: Any) -> Any:
        """Render the full page layout using Dash components.

        Args:
        ----
            **kwargs: Contextual arguments (time_range, active_agent_id, etc.).

        Returns:
        -------
            A Dash layout component (usually html.Div).

        """
        pass
