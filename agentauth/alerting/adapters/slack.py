import logging
from typing import Any

import requests

from ..base import AlertPayload, BaseAlertAdapter
from . import alert_registry

logger = logging.getLogger("agentauth.alerts")

# Colour coding by threshold level (Slack attachment colour field).
_THRESHOLD_COLOURS: dict[int, str] = {
    80: "#f59e0b",  # amber
    90: "#ef4444",  # red-orange
    100: "#b91c1c",  # deep red
}
_DEFAULT_COLOUR = "#ef4444"


@alert_registry.register("slack")
class SlackAlertAdapter(BaseAlertAdapter):
    """Delivers alert notifications as a rich Slack message via Incoming Webhook.

    The message uses Slack's *Block Kit* layout so that it renders as a
    formatted card in any Slack client.

    Args:
    ----
        webhook_url: The Slack Incoming Webhook URL (starts with
            ``https://hooks.slack.com/services/…``).
        timeout: HTTP request timeout in seconds (default: 5).

    """

    def __init__(self, webhook_url: str = "", timeout: int = 5, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.webhook_url = webhook_url
        self.timeout = timeout

    def _build_blocks(self, payload: AlertPayload) -> list[dict]:
        """Build a Slack Block Kit message body for the alert payload.

        Args:
        ----
            payload: Structured information about the triggered alert.

        Returns:
        -------
            A list of Slack Block Kit block objects.

        """
        colour = _THRESHOLD_COLOURS.get(payload.threshold_pct, _DEFAULT_COLOUR)
        emoji = (
            "🔴" if payload.threshold_pct >= 100 else "🟠" if payload.threshold_pct >= 90 else "🟡"
        )
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} AgentAuth Budget Alert"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Agent:*\n{payload.agent_name}"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n{payload.threshold_pct}%"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Spend:*\n${payload.current_spend:.4f}",
                    },
                    {"type": "mrkdwn", "text": f"*Budget:*\n${payload.budget_usd:.2f}"},
                ],
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Dashboard"},
                    "url": "http://localhost:8000/dashboard/",
                    "style": "danger" if payload.threshold_pct >= 100 else "primary",
                },
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"Spend is *{payload.current_pct:.1f}%* of the monthly cap "
                            f"| Rule #{payload.rule_id} | colour={colour}"
                        ),
                    }
                ],
            },
        ]

    async def send(self, payload: AlertPayload) -> bool:
        """Post a Block Kit card to the configured Slack Incoming Webhook.

        Args:
        ----
            payload: Structured information about the triggered alert.

        Returns:
        -------
            ``True`` if Slack acknowledged the message with HTTP 200,
            ``False`` otherwise.

        """
        if not self.webhook_url:
            logger.error("[ALERT][Slack] Cannot send: missing webhook_url")
            return False

        body = {"blocks": self._build_blocks(payload), "text": payload.subject}
        try:
            resp = requests.post(self.webhook_url, json=body, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[ALERT][Slack] Delivery failed: %s", exc)
            return False
