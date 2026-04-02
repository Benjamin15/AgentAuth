"""Alerting subsystem for AgentAuth.

Exports the public surface used by the rest of the application:

- ``AlertPayload`` – data class passed to every adapter.
- ``BaseAlertAdapter`` – abstract base for notification adapters.
- ``AlertEngine`` – evaluates active rules and dispatches notifications.
- ``get_adapter`` – factory that returns the correct adapter for a channel name.
"""

from .base import AlertPayload, BaseAlertAdapter
from .engine import AlertEngine, get_adapter

__all__ = ["AlertPayload", "BaseAlertAdapter", "AlertEngine", "get_adapter"]
