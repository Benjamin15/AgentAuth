import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    client_id = Column(
        String, unique=True, index=True, default=lambda: f"aa_client_{uuid.uuid4().hex}"
    )
    client_secret = Column(String, default=lambda: f"aa_secret_{uuid.uuid4().hex}")
    is_frozen = Column(Boolean, default=False)
    monthly_budget_usd = Column(Float, nullable=True)  # Quota in USD
    created_at = Column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )

    permissions = relationship(
        "AgentPermission", back_populates="agent", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="agent", cascade="all, delete-orphan")
    tokens = relationship("AgentToken", back_populates="agent", cascade="all, delete-orphan")


class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    access_token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )

    agent = relationship("Agent", back_populates="tokens")


class AgentPermission(Base):
    __tablename__ = "agent_permissions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    scope = Column(String)  # e.g., 'openai:chat', 'gmail:read'

    agent = relationship("Agent", back_populates="permissions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    timestamp = Column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )
    target_service = Column(String)  # e.g., "OpenAI"
    request_details = Column(Text, nullable=True)
    response_status = Column(Integer)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, nullable=True)

    agent = relationship("Agent", back_populates="audit_logs")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # OpenAI, Anthropic, Gemini
    provider_key = Column(String, nullable=True)  # The encrypted real API Key
    is_active = Column(Boolean, default=True)


class ModelPricing(Base):
    __tablename__ = "model_pricing"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, index=True)  # gemini-1.5-flash, gpt-4
    input_1m_price = Column(Float, default=0.0)  # Price per 1,000,000 input tokens
    output_1m_price = Column(Float, default=0.0)  # Price per 1,000,000 output tokens


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class AlertRule(Base):
    """A budget-threshold alert rule, optionally scoped to a specific agent.

    If ``agent_id`` is NULL the rule applies globally (all agents).
    ``threshold_pct`` is the percentage of ``monthly_budget_usd`` that triggers
    the alert (e.g. 80, 90, 100).  ``channel`` selects the adapter used for
    delivery; ``destination`` holds the adapter-specific target (webhook URL,
    Slack webhook URL, …).
    """

    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # NULL = global
    threshold_pct = Column(Integer, default=80)  # 80 | 90 | 100
    channel = Column(String, default="log")  # "log" | "webhook" | "slack"
    destination = Column(String, nullable=True)  # URL or channel identifier
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )

    events = relationship("AlertEvent", back_populates="rule", cascade="all, delete-orphan")


class AlertEvent(Base):
    """An immutable record of an alert that was evaluated and dispatched.

    ``delivered`` reflects whether the adapter reported a successful delivery.
    """

    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    triggered_at = Column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )
    current_pct = Column(Float)  # Actual spend % at trigger time
    message = Column(Text)
    delivered = Column(Boolean, default=False)

    rule = relationship("AlertRule", back_populates="events")
