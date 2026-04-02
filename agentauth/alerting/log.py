"""LogAlertAdapter — writes alerts to the Python standard logger.

This adapter is the default fallback when no external destination is
configured.  It is also the recommended adapter for local development and
integration testing because it requires no network credentials.
"""

import logging

from .base import AlertPayload, BaseAlertAdapter

logger = logging.getLogger("agentauth.alerts")


class LogAlertAdapter(BaseAlertAdapter):
    """
    Delivers alert notifications by writing to the Python logging system.

    The alert is logged at **WARNING** level so it is visible in default
    server output without requiring debug-level verbosity.
    """

    async def send(self, payload: AlertPayload) -> bool:
        """
        Log the alert payload and return ``True``.

        This adapter never fails — it always returns ``True`` because writing
        to a logger cannot realistically produce an unrecoverable error.

        Args:
            payload: Structured information about the triggered alert.

        Returns:
            Always ``True``.
        """
        logger.warning("[ALERT] %s\n%s", payload.subject, payload.body)
        return True
