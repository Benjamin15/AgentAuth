import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agentauth.core.database import Base, get_db
from agentauth.main import app

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
    monkeypatch.setattr("agentauth.api.router.SessionLocal", MockSessionLocal())
    monkeypatch.setattr("agentauth.core.database.SessionLocal", MockSessionLocal())

    yield

    db_session.close = original_close
