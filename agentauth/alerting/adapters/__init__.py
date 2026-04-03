"""Alerting adapters for AgentAuth.

This package uses a registry for automatic discovery of notification channels.
"""

from ...core.registry import Registry
from ..base import BaseAlertAdapter

alert_registry = Registry[BaseAlertAdapter]("alert_adapters")


def get_adapter(name: str) -> type[BaseAlertAdapter]:
    """Return the correct alert adapter class from the registry."""
    # Ensure all modules are loaded.
    alert_registry.discover("agentauth.alerting.adapters")

    cls = alert_registry.get(name)
    if cls:
        return cls

    # Fallback can be handled by the caller or here.
    # For compatibility with existing engine, we'll let the engine handle fallbacks.
    raise ValueError(f"No alert adapter registered for channel '{name}'")


__all__ = ["BaseAlertAdapter", "alert_registry", "get_adapter"]
