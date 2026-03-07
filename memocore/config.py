"""
config.py — Centralised settings loaded from .env via pydantic-settings.

Architecture decision: Using pydantic BaseSettings gives us:
  - Automatic type coercion & validation at startup
  - A single source of truth for every env var
  - Easy override in tests (pass env= dict to Settings())
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MemoCore"
    DEBUG: bool = False

    ALLOWED_USER_PHONE: str
    DATABASE_URL: str

    GROQ_API_KEY: str
  
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60
    REMINDER_LEAD_TIME_MINUTES: int = 15

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
