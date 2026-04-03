import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agentauth.core.database import get_db
from agentauth.core.models import Base
from agentauth.main import app


def get_token(client, agent):
    """Generate an OAuth token for an agent."""
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": agent.client_id,
            "client_secret": agent.client_secret,
        },
    )
    return response.json()["access_token"]


# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_db_sessions(monkeypatch, db_session):
    # Mock SessionLocal to return our test db_session but ignore close()
    class MockSessionLocal:
        def __call__(self):
            return db_session

        def __getattr__(self, name):
            return getattr(db_session, name)

    # We need to make sure close() doesn't actually close the shared session
    original_close = db_session.close
    db_session.close = lambda: None

    monkeypatch.setattr("agentauth.dashboard.app.SessionLocal", MockSessionLocal())
    monkeypatch.setattr("agentauth.dashboard.auth_ui.SessionLocal", MockSessionLocal())
    monkeypatch.setattr("agentauth.api.router.SessionLocal", MockSessionLocal())
    monkeypatch.setattr("agentauth.core.database.SessionLocal", MockSessionLocal())

    # Also patch all modular pages to ensure they use the test session
    for page in ["dashboard", "agents", "integrations", "logs", "alerts", "models"]:
        try:
            monkeypatch.setattr(
                f"agentauth.dashboard.pages.{page}.SessionLocal", MockSessionLocal()
            )
        except (AttributeError, ImportError):
            pass

    yield

    db_session.close = original_close
