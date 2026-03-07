from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Application
    APP_NAME: str = "MemoCore"
    DEBUG: bool = False

    # Security
    ALLOWED_USER_PHONE: str

    # WhatsApp Cloud API
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str

    # AI
    GROQ_API_KEY: str

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./memocore.db"

    # Scheduler
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60
    REMINDER_LEAD_TIME_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
