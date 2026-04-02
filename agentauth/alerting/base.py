"""Base adapter contract and shared data structures for the alerting system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class AlertPayload:
    """
    All the information an adapter needs to format and deliver an alert.

    Attributes:
        agent_id: Database ID of the agent that triggered the alert.
            ``None`` for globally-scoped rules.
        agent_name: Human-readable name of the agent.
        threshold_pct: The threshold (e.g. 80, 90, 100) that was crossed.
        current_pct: The actual spend percentage at evaluation time.
        current_spend: Accumulated spend in USD this calendar month.
        budget_usd: Configured monthly budget cap in USD.
        rule_id: Primary key of the ``AlertRule`` that generated this payload.
    """

    agent_id: Optional[int]
    agent_name: str
    threshold_pct: int
    current_pct: float
    current_spend: float
    budget_usd: float
    rule_id: int

    @property
    def subject(self) -> str:
        """Short one-line summary suitable for notification titles."""
        return (
            f"[AgentAuth] Budget alert: {self.agent_name} reached {self.threshold_pct}% "
            f"(${self.current_spend:.2f} / ${self.budget_usd:.2f})"
        )

    @property
    def body(self) -> str:
        """Multi-line message body with details."""
        return (
            f"Agent '{self.agent_name}' has consumed {self.current_pct:.1f}% of its monthly "
            f"budget.\n\n"
            f"  Spend:  ${self.current_spend:.4f}\n"
            f"  Budget: ${self.budget_usd:.2f}\n"
            f"  Rule:   #{self.rule_id} (threshold {self.threshold_pct}%)\n\n"
            "Review the AgentAuth dashboard for details."
        )


class BaseAlertAdapter(ABC):
    """
    Strategy interface for alert notification channels.

    Concrete subclasses **must** implement :meth:`send` and return ``True``
    when the notification was delivered successfully, ``False`` otherwise.
    Implementations should never raise — swallow exceptions and return
    ``False`` instead so the engine can record a failed delivery without
    crashing the proxy request.
    """

    @abstractmethod
    async def send(self, payload: AlertPayload) -> bool:
        """
        Deliver an alert notification.

        Args:
            payload: Structured information about the triggered alert.

        Returns:
            ``True`` if the notification was delivered, ``False`` on failure.
        """
