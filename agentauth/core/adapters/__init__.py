"""Integration adapters for AgentAuth.

This package uses a registry for automatic discovery of LLM/provider adapters.
"""

from ..registry import Registry
from .base import BaseAdapter

adapter_registry = Registry[BaseAdapter]("integration_adapters")


def get_adapter(name: str) -> type[BaseAdapter]:
    """Return the correct adapter class from the registry."""
    # Ensure all modules are loaded.
    adapter_registry.discover("agentauth.core.adapters")

    cls = adapter_registry.get(name)
    if cls:
        return cls

    # Fallback could be handled here or by caller.
    raise ValueError(f"No adapter registered for provider '{name}'")


__all__ = ["BaseAdapter", "adapter_registry", "get_adapter"]
