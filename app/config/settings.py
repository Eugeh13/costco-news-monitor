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

    # ── Database ──
    database_url: Optional[str] = None

    # ── Fuentes ──
    # GNews (lib) descarga con feedparser/urllib: falla SSL en local y no permite
    # inyectar sesión/User-Agent. Además es redundante: usa el mismo backend
    # (news.google.com/rss/search) que GoogleRSSSource, que ya funciona con
    # requests+UA. Desactivada por default; ver gnews_source.py.
    gnews_enabled: bool = False

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

    # ── Heartbeat diario (M1) ──
    # UN solo reporte de estado al día por Telegram (antes era un resumen por
    # ciclo sin alertas: decenas de "todo tranquilo" que entrenan a ignorar el
    # canal). Se envía en el primer ciclo a partir de esta hora (hora del centro);
    # marcador persistente YYYY-MM-DD para no reenviar tras un reinicio.
    daily_heartbeat_enabled: bool = True
    daily_heartbeat_hour: int = 8

    # ── Digest mensual de criminalidad (SESNSP) ──
    # El SESNSP publica el corte mensual ~día 20. El scheduler intenta el
    # digest a partir del día crime_digest_day a las 9:00 (hora del centro)
    # y reintenta en cada ciclo hasta lograrlo; un marcador persistente
    # (YYYY-MM, junto al archivo de FileStorage) evita reenvíos en el mes.
    crime_digest_enabled: bool = True  # Apagar para deshabilitar el digest mensual
    crime_digest_day: int = 25         # Día del mes a partir del cual se intenta

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

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
