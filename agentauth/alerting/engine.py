"""AlertEngine — evaluates active alert rules and dispatches notifications.

The engine is the sole integration point between the proxy and the alerting
subsystem.  Call :func:`AlertEngine.evaluate` once per proxied request
(ideally as a fire-and-forget async task) and let it handle rule matching,
deduplication, adapter selection, and event persistence.
"""

import asyncio
import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..core.models import Agent, AlertEvent, AlertRule, AuditLog
from .base import AlertPayload, BaseAlertAdapter
from .log import LogAlertAdapter
from .slack import SlackAlertAdapter
from .webhook import WebhookAlertAdapter

logger = logging.getLogger("agentauth.alerts")

# Threshold levels checked in ascending order so each crossing is distinct.
TRACKED_THRESHOLDS = (80, 90, 100)


def get_adapter(channel: str, destination: Optional[str]) -> BaseAlertAdapter:
    """Return the correct :class:`BaseAlertAdapter` for a channel.

    Falls back to :class:`LogAlertAdapter` when the channel is unknown or the
    destination is not configured.

    Args:
    ----
        channel: One of ``"log"``, ``"webhook"``, or ``"slack"``.
        destination: Channel-specific target (URL for webhook / Slack).

    Returns:
    -------
        An instantiated, ready-to-use adapter.

    """
    if channel == "webhook" and destination:
        return WebhookAlertAdapter(url=destination)
    if channel == "slack" and destination:
        return SlackAlertAdapter(webhook_url=destination)
    if channel != "log":
        logger.warning(
            "[AlertEngine] Unknown channel '%s' or missing destination — falling back to log.",
            channel,
        )
    return LogAlertAdapter()


class AlertEngine:
    """Evaluates alert rules for a given agent and dispatches notifications.

    Usage::

        asyncio.create_task(AlertEngine.evaluate(agent, db))

    The engine is designed to be called in a **fire-and-forget** fashion from
    the proxy request handler.  All exceptions are swallowed so that a broken
    alert rule never disrupts API traffic.
    """

    @staticmethod
    async def evaluate(agent: Agent, db: Session) -> None:
        """Evaluate all active rules for *agent* and dispatch any new alerts.

        An alert is dispatched only once per calendar month per (rule, threshold)
        pair — the engine checks whether an ``AlertEvent`` already exists for
        the current month before firing.

        Args:
        ----
            agent: The :class:`~agentauth.core.models.Agent` whose spend is
                being evaluated.
            db: An active SQLAlchemy :class:`~sqlalchemy.orm.Session`.

        """
        try:
            await AlertEngine._run(agent, db)
        except Exception as exc:  # noqa: BLE001
            logger.error("[AlertEngine] Unexpected error during evaluation: %s", exc)

    @staticmethod
    async def _run(agent: Agent, db: Session) -> None:
        """Implement the internal alerting logic."""
        if agent.monthly_budget_usd is None or agent.monthly_budget_usd <= 0:
            return  # No budget configured — nothing to alert on.

        # ---- 1. Calculate current monthly spend ----
        first_of_month = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(tzinfo=None)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.agent_id == agent.id, AuditLog.timestamp >= first_of_month)
            .with_entities(AuditLog.cost_usd)
            .all()
        )
        current_spend = sum(float(row.cost_usd or 0) for row in logs)
        current_pct = (current_spend / agent.monthly_budget_usd) * 100

        # ---- 2. Fetch active rules for this agent (agent-specific + global) ----
        rules = (
            db.query(AlertRule)
            .filter(
                AlertRule.is_active.is_(True),
                (AlertRule.agent_id == agent.id) | (AlertRule.agent_id.is_(None)),
            )
            .all()
        )

        if not rules:
            return

        # ---- 3. Evaluate each rule ----
        tasks = []
        for rule in rules:
            if current_pct < rule.threshold_pct:
                continue  # Threshold not yet reached.

            # Deduplication: skip if already fired this month.
            already_fired = (
                db.query(AlertEvent)
                .filter(
                    AlertEvent.rule_id == rule.id,
                    AlertEvent.agent_id == agent.id,
                    AlertEvent.triggered_at >= first_of_month,
                )
                .first()
            )
            if already_fired:
                continue

            payload = AlertPayload(
                agent_id=int(agent.id),  # type: ignore[arg-type]
                agent_name=str(agent.name),
                threshold_pct=int(rule.threshold_pct),  # type: ignore[arg-type]
                current_pct=float(current_pct),
                current_spend=current_spend,
                budget_usd=float(agent.monthly_budget_usd),
                rule_id=int(rule.id),  # type: ignore[arg-type]
            )
            tasks.append(AlertEngine._fire(rule, payload, int(agent.id), db))  # type: ignore[arg-type]

        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    async def _fire(
        rule: AlertRule,
        payload: AlertPayload,
        agent_id: int,
        db: Session,
    ) -> None:
        """Deliver the alert via the configured adapter and persist the event.

        Args:
        ----
            rule: The :class:`~agentauth.core.models.AlertRule` being fired.
            payload: Pre-built alert payload.
            agent_id: ID of the agent the alert is scoped to.
            db: Active database session.

        """
        adapter = get_adapter(str(rule.channel), rule.destination)  # type: ignore[arg-type]
        delivered = await adapter.send(payload)

        event = AlertEvent(
            rule_id=rule.id,
            agent_id=agent_id,
            current_pct=payload.current_pct,
            message=payload.subject,
            delivered=delivered,
        )
        db.add(event)
        db.commit()

        status = "✅ delivered" if delivered else "❌ failed"
        logger.info(
            "[AlertEngine] Rule #%s fired for agent '%s' at %.1f%% — %s",
            rule.id,
            payload.agent_name,
            payload.current_pct,
            status,
        )
