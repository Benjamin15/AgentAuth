import logging
from typing import Any

import requests

from ..base import AlertPayload, BaseAlertAdapter
from . import alert_registry

logger = logging.getLogger("agentauth.alerts")


@alert_registry.register("webhook")
class WebhookAlertAdapter(BaseAlertAdapter):
    """Delivers alert notifications as a JSON POST to an arbitrary HTTP endpoint.

    Args:
    ----
        url: The full URL to POST the alert payload to.
        timeout: HTTP request timeout in seconds (default: 5).
        extra_headers: Optional additional HTTP headers (e.g. auth tokens).

    """

    def __init__(
        self,
        url: str = "",
        timeout: int = 5,
        extra_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json", **(extra_headers or {})}

    async def send(self, payload: AlertPayload) -> bool:
        """POST the alert payload to the configured webhook URL.

        Args:
        ----
            payload: Structured information about the triggered alert.

        Returns:
        -------
            ``True`` if the server responded with a 2xx status code,
            ``False`` otherwise.

        """
        if not self.url:
            logger.error("[ALERT][Webhook] Cannot send: missing url")
            return False

        body: dict[str, Any] = {
            "event": "budget_alert",
            "subject": payload.subject,
            "agent_id": payload.agent_id,
            "agent_name": payload.agent_name,
            "threshold_pct": payload.threshold_pct,
            "current_pct": round(payload.current_pct, 2),
            "current_spend_usd": round(payload.current_spend, 4),
            "budget_usd": payload.budget_usd,
            "rule_id": payload.rule_id,
        }
        try:
            resp = requests.post(self.url, json=body, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[ALERT][Webhook] Delivery failed to %s: %s", self.url, exc)
            return False
