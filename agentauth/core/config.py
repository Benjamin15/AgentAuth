from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core settings
    PROJECT_NAME: str = "AgentAuth"
    DATABASE_URL: str = "sqlite:///./agentauth.db"

    # Security
    AGENTAUTH_JWT_SECRET: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Symmetric encryption (storage of keys)
    AGENTAUTH_MASTER_KEY: Optional[str] = None
    KEY_FILE_PATH: Path = Path(".agentauth_master.key")

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    @property
    def sqlite_db_path(self) -> str:
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "")
        return "agentauth.db"


settings = Settings()
