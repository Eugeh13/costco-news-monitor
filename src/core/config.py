from __future__ import annotations

from enum import StrEnum

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    dev = "dev"
    prod = "prod"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: PostgresDsn = Field(
        description="PostgreSQL async DSN — must use postgresql+asyncpg:// scheme"
    )
    anthropic_api_key: str = Field(description="Anthropic API key")
    telegram_bot_token: str = Field(description="Telegram bot token")
    telegram_chat_id: str = Field(description="Telegram chat ID for alerts")
    log_level: LogLevel = LogLevel.INFO
    environment: Environment = Environment.dev

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_async_scheme(cls, v: str) -> str:
        """Ensure DSN uses asyncpg driver even if user provides plain postgresql://."""
        v = str(v)
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @property
    def is_prod(self) -> bool:
        return self.environment is Environment.prod


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
