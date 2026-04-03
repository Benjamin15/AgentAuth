from sqlalchemy.orm import Session

from agentauth.core.database import Base, SessionLocal, engine, get_db
from agentauth.core.models import Agent


def test_database_get_db_generator():
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    # Cleanup
    try:
        next(db_gen)
    except StopIteration:
        pass


def test_session_local_instantiation():
    db = SessionLocal()
    assert isinstance(db, Session)
    db.close()


def test_engine_initialization():
    assert engine is not None
    assert "sqlite" in str(engine.url)


def test_metadata_tables():
    assert "agents" in Base.metadata.tables
    assert "audit_logs" in Base.metadata.tables
    assert "integrations" in Base.metadata.tables


def test_session_query_simple(db_session):
    agent = Agent(name="DBSessBot")
    db_session.add(agent)
    db_session.commit()
    # Query back using the session fixture
    found = db_session.get(Agent, agent.id)
    assert found.name == "DBSessBot"
