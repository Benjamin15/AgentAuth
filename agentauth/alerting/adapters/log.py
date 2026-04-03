import logging

from ..base import AlertPayload, BaseAlertAdapter
from . import alert_registry

logger = logging.getLogger("agentauth.alerts")


@alert_registry.register("log")
class LogAlertAdapter(BaseAlertAdapter):
    """Delivers alert notifications by writing to the Python logging system.

    The alert is logged at **WARNING** level so it is visible in default
    server output without requiring debug-level verbosity.
    """

    async def send(self, payload: AlertPayload) -> bool:
        """Log the alert payload and return ``True``.

        This adapter never fails — it always returns ``True`` because writing
        to a logger cannot realistically produce an unrecoverable error.

        Args:
        ----
            payload: Structured information about the triggered alert.

        Returns:
        -------
            Always ``True``.

        """
        logger.warning("[ALERT] %s\n%s", payload.subject, payload.body)
        return True
