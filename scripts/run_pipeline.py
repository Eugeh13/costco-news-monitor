#!/usr/bin/env python3
"""
Pipeline CLI — ejecuta un ciclo completo de monitoreo y guarda decisiones en DB.

Uso:
    python scripts/run_pipeline.py [--db sqlite+aiosqlite:///./costco_motor.db]

Variables de entorno (leídas de .env si existe):
    DATABASE_URL      — cadena de conexión SQLAlchemy async (default: SQLite local)
    ANTHROPIC_API_KEY — requerido para triage / deep_analysis; sin él se salta IA
    TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID — opcionales en dry-run
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# ── Bootstrap: añadir raíz del proyecto al path ───────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Cargar .env antes de importar cualquier módulo del proyecto ───────────────
def _load_dotenv(path: Path = ROOT / ".env") -> None:
    try:
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                val = val.strip().strip("\"'")
                os.environ.setdefault(key.strip(), val)
    except FileNotFoundError:
        pass

_load_dotenv()

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.analyzer.classifier import Classifier
from src.analyzer.dedup import is_duplicate, is_duplicate_db, reset_cache
from src.analyzer.geolocator import (
    distance_to_costcos,
    geocode,
    geolocate_incident,
    is_within_radius,
)
from src.analyzer.types import IncidentInput
from src.core.decision_logger import create_run, log_processed_article
from src.core.database import Base
from src.core.token_counter import TokenAccumulator
from src.models.decision_log import FinalDecision, StageReached
from src.notifier.telegram import TelegramClient
from src.scrapers import ALL_SCRAPERS, RawArticle

# ── Logging ───────────────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger("pipeline")

# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_DB = "sqlite+aiosqlite:///./costco_motor.db"
_ALERT_THRESHOLD_SEVERITY = 5
_ALERT_RADIUS_M = 3_000.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tok(acc: TokenAccumulator) -> dict:
    """Return token/cost fields for log_processed_article **kwargs spread."""
    return {
        "total_tokens_input": acc.input_tokens,
        "total_tokens_output": acc.output_tokens,
        "total_tokens_cache_read": acc.cache_read_tokens,
        "total_tokens_cache_creation": acc.cache_creation_tokens,
        "cost_estimated_usd": acc.cost_usd,
    }


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", _DEFAULT_DB)
    # Coerce legacy postgres:// schemes
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def _ensure_schema(engine) -> None:  # type: ignore[type-arg]
    """Create tables if they don't exist (SQLite dev mode)."""
    import src.models  # noqa: F401 — registers all mappers
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _process_article(
    article: RawArticle,
    *,
    run_id: str,
    session,
    classifier: Classifier | None,
    telegram: TelegramClient | None,
    stats: dict,
) -> None:
    """Full pipeline for a single article; logs every stage to decision_log."""
    url = article.url
    accumulator = TokenAccumulator()

    # ── Stage: scraped ────────────────────────────────────────────────────────
    await log_processed_article(
        session, run_id, article, StageReached.scraped
    )
    await session.commit()
    stats["scraped"] += 1

    try:
        # ── Dedup check (before any AI call) ─────────────────────────────────
        await log_processed_article(
            session, run_id, article, StageReached.dedup
        )
        if is_duplicate(article.title, url) or await is_duplicate_db(article.title, url, session, exclude_run_id=run_id):
            await log_processed_article(
                session, run_id, article,
                StageReached.dedup,
                FinalDecision.duplicate,
                **_tok(accumulator),
            )
            await session.commit()
            stats["duplicate"] += 1
            log.info("dedup.duplicate", url=url)
            return

        # ── Triage ────────────────────────────────────────────────────────────
        await log_processed_article(
            session, run_id, article, StageReached.triage
        )
        await session.commit()

        if classifier is None:
            log.warning("triage.skipped — no ANTHROPIC_API_KEY", url=url)
            await log_processed_article(
                session, run_id, article,
                StageReached.triage,
                FinalDecision.pending,
                triage_passed=None,
                triage_reason="ANTHROPIC_API_KEY not set",
                **_tok(accumulator),
            )
            await session.commit()
            stats["no_api_key"] += 1
            return

        incident_input = IncidentInput(
            title=article.title,
            content=article.content_snippet or article.title,
            source=article.source_name,
            published_at=article.published_at,
            url=url,
        )

        triage_ok = await classifier.triage(incident_input, accumulator=accumulator)
        await log_processed_article(
            session, run_id, article,
            StageReached.triage,
            FinalDecision.pending if triage_ok else FinalDecision.irrelevant,
            triage_passed=triage_ok,
            **_tok(accumulator),
        )
        await session.commit()

        if not triage_ok:
            stats["irrelevant"] += 1
            log.info("triage.irrelevant", url=url)
            return

        # ── Deep analysis ─────────────────────────────────────────────────────
        await log_processed_article(
            session, run_id, article, StageReached.deep_analysis
        )
        await session.commit()

        classification = await classifier.deep_analyze(incident_input, accumulator=accumulator)
        if classification is None:
            await log_processed_article(
                session, run_id, article,
                StageReached.deep_analysis,
                FinalDecision.error,
                error_message="deep_analyze returned None",
                **_tok(accumulator),
            )
            await session.commit()
            stats["error"] += 1
            return

        await log_processed_article(
            session, run_id, article,
            StageReached.deep_analysis,
            FinalDecision.pending,
            incident_type=classification.incident_type.value,
            severity_score=classification.severity,
            affects_operations=classification.affects_operations,
            ai_reasoning=classification.reasoning,
        )
        await session.commit()

        # ── Geolocation ───────────────────────────────────────────────────────
        await log_processed_article(
            session, run_id, article, StageReached.geolocation
        )
        await session.commit()

        text = f"{article.title} {article.content_snippet}"
        geo_result = await geolocate_incident(text, accumulator=accumulator)
        place_names: list[str] = []
        if geo_result:
            if geo_result.exact_address:
                place_names.append(geo_result.exact_address)
            if geo_result.neighborhood:
                addr = f"{geo_result.neighborhood}, {geo_result.city}"
                if addr not in place_names:
                    place_names.append(addr)
            if not place_names:
                place_names.append(geo_result.city)

        geo = None
        distances: dict[str, float] = {}

        for place in place_names:
            geo = await geocode(place)
            if geo:
                distances = distance_to_costcos(geo.lat, geo.lon)
                break

        _geo_extra: dict = {}
        if geo_result:
            _geo_extra = {
                "approximate_location": geo_result.neighborhood or geo_result.city,
                "exact_location_lat": geo_result.latitude,
                "exact_location_lng": geo_result.longitude,
                "geolocation_confidence": geo_result.confidence,
            }

        if geo is None:
            await log_processed_article(
                session, run_id, article,
                StageReached.geolocation,
                FinalDecision.no_geo,
                **_geo_extra,
                **_tok(accumulator),
            )
            await session.commit()
            stats["no_geo"] += 1
            log.info("geo.no_result", url=url, places=place_names)
            return

        if not is_within_radius(geo.lat, geo.lon, _ALERT_RADIUS_M):
            nearest_name, nearest_dist = min(distances.items(), key=lambda kv: kv[1])
            await log_processed_article(
                session, run_id, article,
                StageReached.geolocation,
                FinalDecision.out_of_radius,
                geo_lat=geo.lat,
                geo_lon=geo.lon,
                geo_address=geo.address,
                nearest_costco=nearest_name,
                nearest_costco_dist_m=nearest_dist,
                **_geo_extra,
                **_tok(accumulator),
            )
            await session.commit()
            stats["out_of_radius"] += 1
            log.info("geo.out_of_radius", url=url, nearest_km=f"{nearest_dist/1000:.1f}")
            return

        nearest_name, nearest_dist = min(distances.items(), key=lambda kv: kv[1])
        await log_processed_article(
            session, run_id, article,
            StageReached.geolocation,
            FinalDecision.pending,
            geo_lat=geo.lat,
            geo_lon=geo.lon,
            geo_address=geo.address,
            nearest_costco=nearest_name,
            nearest_costco_dist_m=nearest_dist,
            **_geo_extra,
        )
        await session.commit()

        # ── Severity threshold ────────────────────────────────────────────────
        if classification.severity < _ALERT_THRESHOLD_SEVERITY:
            await log_processed_article(
                session, run_id, article,
                StageReached.notification,
                FinalDecision.irrelevant,
                **_tok(accumulator),
            )
            await session.commit()
            stats["below_threshold"] += 1
            log.info(
                "severity.below_threshold",
                severity=classification.severity,
                url=url,
            )
            return

        # ── Notification (dry_run=True) ───────────────────────────────────────
        await log_processed_article(
            session, run_id, article, StageReached.notification
        )

        if telegram:
            await telegram.send_alert(
                classification,
                geo,
                distances,
                source_url=url,
                dry_run=True,
            )

        await log_processed_article(
            session, run_id, article,
            StageReached.notification,
            FinalDecision.alerted,
            **_tok(accumulator),
        )
        await session.commit()
        stats["alerted"] += 1
        log.info(
            "alert.sent_dry_run",
            url=url,
            severity=classification.severity,
            nearest=f"{nearest_dist/1000:.1f}km",
        )

    except Exception as exc:  # noqa: BLE001
        log.error("pipeline.article_error", url=url, error=str(exc))
        try:
            await log_processed_article(
                session, run_id, article,
                StageReached.error,
                FinalDecision.error,
                error_message=str(exc)[:1000],
                **_tok(accumulator),
            )
            await session.commit()
        except Exception:
            pass
        stats["error"] += 1


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    db_url = _get_database_url()
    log.info("pipeline.start", db=db_url.split("///")[-1])

    engine = create_async_engine(db_url, echo=False)
    await _ensure_schema(engine)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Build classifier if API key available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    classifier: Classifier | None = Classifier(api_key=api_key) if api_key else None
    if not classifier:
        log.warning("pipeline.no_classifier — ANTHROPIC_API_KEY not set, AI stages skipped")

    # Build Telegram client if tokens available (dry_run anyway)
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID")
    telegram: TelegramClient | None = (
        TelegramClient(tg_token, tg_chat) if (tg_token and tg_chat) else None
    )

    run_id = create_run()
    log.info("pipeline.run_id", run_id=run_id)

    stats: dict[str, int] = defaultdict(int)
    reset_cache()

    t0 = time.monotonic()

    async with session_factory() as session:
        for scraper in ALL_SCRAPERS:
            log.info("scraper.start", name=scraper.source_name)
            try:
                articles, elapsed = await scraper._timed_fetch()
                stats["scrapers_ok"] += 1
            except Exception as exc:  # noqa: BLE001
                log.error("scraper.error", name=scraper.source_name, error=str(exc))
                stats["scrapers_error"] += 1
                continue

            for article in articles:
                await _process_article(
                    article,
                    run_id=run_id,
                    session=session,
                    classifier=classifier,
                    telegram=telegram,
                    stats=stats,
                )

    elapsed_total = time.monotonic() - t0

    if telegram and hasattr(telegram, "_http"):
        await telegram._http.aclose()
    await engine.dispose()

    # ── Summary ───────────────────────────────────────────────────────────────
    total = stats["scraped"]
    print("\n" + "═" * 60)
    print(f"  Pipeline run: {run_id}")
    print(f"  Elapsed:      {elapsed_total:.1f}s")
    print(f"  Scrapers:     {stats['scrapers_ok']} OK / {stats['scrapers_error']} error")
    print(f"  Articles:     {total} procesados")
    print()
    print("  Distribución por stage/decisión:")
    for key in ("alerted", "irrelevant", "duplicate", "out_of_radius", "no_geo",
                "below_threshold", "no_api_key", "error"):
        n = stats[key]
        if n:
            print(f"    {key:<20} {n:>4}")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
