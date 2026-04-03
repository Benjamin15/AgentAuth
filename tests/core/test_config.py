from agentauth.core.config import Settings


def test_settings_initialization():
    # Pass values directly to test override logic
    s = Settings(PORT=9000, HOST="0.0.0.0")
    assert s.PORT == 9000
    assert s.HOST == "0.0.0.0"


def test_settings_defaults():
    s = Settings()
    assert s.PROJECT_NAME == "AgentAuth"


def test_sqlite_db_path_property():
    s = Settings()
    s.DATABASE_URL = "sqlite:///test.db"
    assert s.sqlite_db_path == "test.db"

    s.DATABASE_URL = "postgresql://user:pass@host/db"
    assert s.sqlite_db_path == "agentauth.db"
