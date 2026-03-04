"""
config.py — Centralised settings loaded from .env via pydantic-settings.

Architecture decision: Using pydantic BaseSettings gives us:
  - Automatic type coercion & validation at startup
  - A single source of truth for every env var
  - Easy override in tests (pass env= dict to Settings())
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = "MemoCore"
    DEBUG: bool = False

    # ------------------------------------------------------------------ #
    # Security — only messages from this phone number are processed
    # ------------------------------------------------------------------ #
    ALLOWED_USER_PHONE: str  # e.g. "+1234567890"

    # ------------------------------------------------------------------ #
    # OpenRouter (DeepSeek)
    # ------------------------------------------------------------------ #
    OPENROUTER_API_KEY: str

    # ------------------------------------------------------------------ #
    # Database
    # Architecture decision: default to SQLite for frictionless local dev;
    # swap to a proper async PostgreSQL URL in production.
    # SQLite async driver: aiosqlite   PostgreSQL async driver: asyncpg
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "sqlite+aiosqlite:///./memocore.db"

    # ------------------------------------------------------------------ #
    # Scheduler
    # ------------------------------------------------------------------ #
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60  # how often to poll for upcoming events
    REMINDER_LEAD_TIME_MINUTES: int = 15       # remind N minutes before event

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
