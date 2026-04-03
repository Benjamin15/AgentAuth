"""AlertEngine — evaluates active alert rules and dispatches notifications.

The engine is the sole integration point between the proxy and the alerting
subsystem.  Call :func:`AlertEngine.evaluate` once per proxied request
(ideally as a fire-and-forget async task) for a given agent_id and let it
handle rule matching, deduplication, adapter selection, and event persistence.
"""

import asyncio
import datetime
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.models import Agent, AlertEvent, AlertRule, AuditLog
from .adapters import get_adapter as get_adapter_from_registry
from .base import AlertPayload, BaseAlertAdapter

logger = logging.getLogger("agentauth.alerts")

# Threshold levels checked in ascending order so each crossing is distinct.
TRACKED_THRESHOLDS = (80, 90, 100)


def get_adapter(channel: str, destination: Optional[str]) -> BaseAlertAdapter:
    """Return the correct :class:`BaseAlertAdapter` for a channel.

    Falls back to :class:`LogAlertAdapter` when the channel is unknown or the
    destination is not configured.
    """
    try:
        adapter_cls = get_adapter_from_registry(channel)
        if channel == "webhook":
            if destination:
                return adapter_cls(url=destination)  # type: ignore[call-arg]
            raise ValueError("Webhook destination missing")
        if channel == "slack":
            if destination:
                return adapter_cls(webhook_url=destination)  # type: ignore[call-arg]
            raise ValueError("Slack destination missing")

        return adapter_cls()
    except Exception:
        if channel != "log":
            logger.warning(
                "[AlertEngine] Unknown channel '%s' or missing destination — falling back to log.",
                channel,
            )
        # Import inside to avoid circularity if needed, though log should be safe
        try:
            log_cls = get_adapter_from_registry("log")
            return log_cls()
        except Exception:
            # Absolute fallback
            from .adapters.log import LogAlertAdapter

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
    async def evaluate(agent_id: int, db: Optional[Session] = None) -> None:
        """Evaluate all active rules for *agent* and dispatch any new alerts.

        If *db* is not provided, a new session is created. This is preferred
        when calling from a background task to avoid closed session errors.

        An alert is dispatched only once per calendar month per (rule, threshold)
        pair — the engine checks whether an ``AlertEvent`` already exists for
        the current month before firing.

        Args:
        ----
            agent_id: The ID of the :class:`~agentauth.core.models.Agent` whose spend is
                being evaluated.
            db: An active SQLAlchemy :class:`~sqlalchemy.orm.Session`.

        """
        internal_db = db or SessionLocal()
        try:
            agent = internal_db.get(Agent, agent_id)
            if not agent:
                logger.error("[AlertEngine] Agent #%s not found during evaluation", agent_id)
                return

            await AlertEngine._run(agent, internal_db)
        except Exception as exc:  # noqa: BLE001
            logger.error("[AlertEngine] Unexpected error during evaluation: %s", exc)
        finally:
            if db is None:
                internal_db.close()

    @staticmethod
    async def _run(agent: Agent, db: Session) -> None:
        """Implement the internal alerting logic."""
        if agent.monthly_budget_usd is None or agent.monthly_budget_usd <= 0:
            return  # No budget configured — nothing to alert on.

        # ---- 1. Calculate current monthly spend using SQL SUM ----
        first_of_month = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(tzinfo=None)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
        total_spent_query = (
            db.query(func.sum(AuditLog.cost_usd))
            .filter(AuditLog.agent_id == agent.id, AuditLog.timestamp >= first_of_month)
            .scalar()
        )
        current_spend = float(total_spent_query or 0.0)
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

        Includes a simple retry mechanism for transient network errors.
        """
        adapter = get_adapter(str(rule.channel), rule.destination)  # type: ignore[arg-type]

        delivered = False
        max_retries = 3
        for attempt in range(max_retries):
            try:
                delivered = await adapter.send(payload)
                if delivered:
                    break
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[AlertEngine] Alert delivery attempt %d failed for Rule #%s: %s",
                    attempt + 1,
                    rule.id,
                    exc,
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff (1s, 2s)

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
