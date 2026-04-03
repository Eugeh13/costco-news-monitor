"""
Entry point — dependency wiring and single execution.

This is the ONLY place where concrete implementations are instantiated.
Everything else depends on abstractions (ports).
"""

from app.config.locations import get_active_locations
from app.config.settings import settings
from app.infrastructure.notifications.telegram import ConsoleNotifier, TelegramNotifier
from app.infrastructure.persistence.file_storage import FileStorage
from app.infrastructure.sources.deep_reader import MultiStrategyReader
from app.infrastructure.sources.gnews_source import GNewsSource
from app.infrastructure.sources.google_rss import GoogleRSSSource
from app.infrastructure.sources.rss_direct import RSSDirectSource
from app.services.content_hasher import ContentHasher
from app.services.deep_analysis import DeepAnalysisService
from app.services.geo_service import GeoService, NominatimGeocoder
from app.services.pipeline import MonitoringPipeline
from app.services.triage import TriageService


def build_pipeline() -> MonitoringPipeline:
    """Wire all dependencies and return a configured pipeline."""

    # ── AI Provider ──
    if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
        from app.infrastructure.ai.anthropic_provider import AnthropicProvider
        ai = AnthropicProvider(
            model=settings.default_ai_model,
            api_key=settings.anthropic_api_key,
        )
    else:
        from app.infrastructure.ai.openai_provider import OpenAIProvider
        ai = OpenAIProvider(
            model=settings.default_ai_model,
            api_key=settings.openai_api_key,
        )

    print(f"🤖 AI: {ai.provider_name()}")

    # ── News Sources ──
    sources = [
        GoogleRSSSource(),
        GNewsSource(),
        RSSDirectSource(),
    ]

    # ── Notifier ──
    if settings.telegram_enabled:
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )
        print("📱 Telegram: ✓")
    else:
        notifier = ConsoleNotifier()
        print("📱 Telegram: ✗ (usando consola)")

    # ── Repository ──
    repo = None
    if settings.database_enabled:
        from app.infrastructure.persistence.postgres import PostgresRepository
        repo = PostgresRepository(settings.database_url)
        print("💾 DB: ✓")
    else:
        print("💾 DB: ✗")

    # ── Geo Service ──
    active_locations = get_active_locations()
    geo = GeoService(
        geocoder=NominatimGeocoder(),
        locations=active_locations,
        radius_km=settings.radius_km,
    )
    print(f"📍 Costcos activos: {', '.join(l.nombre for l in active_locations)}")

    # ── Services ──
    reader = MultiStrategyReader()
    triage = TriageService(ai=ai, chunk_size=settings.triage_chunk_size)
    deep = DeepAnalysisService(ai=ai, reader=reader, geo=geo)
    file_storage = FileStorage(settings.processed_news_file)
    hasher = ContentHasher()

    return MonitoringPipeline(
        sources=sources,
        triage=triage,
        deep=deep,
        notifier=notifier,
        repository=repo,
        file_storage=file_storage,
        hasher=hasher,
        max_age_hours=settings.max_age_hours,
    )


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║  Costco News Monitor v2 — Clean Architecture                     ║
║  Monterrey, NL — Multi-source + AI Triage                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    pipeline = build_pipeline()
    pipeline.run_once()


if __name__ == "__main__":
    main()
