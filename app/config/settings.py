"""
Application settings loaded from environment variables with Pydantic validation.

Single source of truth for all configuration. No more scattered os.getenv() calls.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings, validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── AI Provider ──
    ai_provider: str = "openai"
    ai_model: Optional[str] = None  # Falls back to provider default
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # ── Telegram ──
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # ── Twitter/X (cookie-based, no API key needed) ──
    twitter_auth_token: Optional[str] = None
    twitter_ct0: Optional[str] = None

    # ── Database ──
    database_url: Optional[str] = None

    # ── Monitoring ──
    radius_km: float = 5.0
    max_age_hours: int = 1
    triage_chunk_size: int = 25
    processed_news_file: str = "processed_news.txt"

    # ── Scheduler ──
    min_poll_interval_minutes: int = 5
    max_poll_interval_minutes: int = 15
    night_pause_start: int = 23  # Hour (CST)
    night_pause_end: int = 6    # Hour (CST)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def twitter_enabled(self) -> bool:
        return bool(self.twitter_auth_token and self.twitter_ct0)

    @property
    def database_enabled(self) -> bool:
        return bool(self.database_url)

    @property
    def default_ai_model(self) -> str:
        if self.ai_model:
            return self.ai_model
        if self.ai_provider == "anthropic":
            return "claude-haiku-4-5-20251001"
        return "gpt-5-mini"


# Singleton — created once, imported everywhere
settings = Settings()
