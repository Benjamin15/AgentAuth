import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    api_key = Column(String, unique=True, index=True, default=lambda: f"aa_live_{uuid.uuid4().hex}")
    is_frozen = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    permissions = relationship("AgentPermission", back_populates="agent")
    audit_logs = relationship("AuditLog", back_populates="agent")


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
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    target_service = Column(String)  # e.g., "OpenAI"
    request_details = Column(Text, nullable=True)
    response_status = Column(Integer)

    agent = relationship("Agent", back_populates="audit_logs")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # OpenAI, Anthropic, Gemini
    provider_key = Column(String, nullable=True)  # The real API Key stored securely
    is_active = Column(Boolean, default=True)
