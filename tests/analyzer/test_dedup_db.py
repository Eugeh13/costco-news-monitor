"""Tests for the DB-backed dedup layer in src/analyzer/dedup.py."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.models  # noqa: F401 — registers all ORM mappers so Base.metadata is complete
from src.analyzer.dedup import _canonicalize_url, is_duplicate_db
from src.core.database import Base


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _insert_log(
    session: AsyncSession,
    url: str,
    title: str,
    created_at: datetime | None = None,
) -> None:
    ts = (created_at or datetime.now(UTC)).isoformat()
    await session.execute(
        text(
            "INSERT INTO decision_log "
            "(run_id, article_url, article_title, source_name, "
            " stage_reached, final_decision, telegram_sent, created_at, updated_at) "
            "VALUES (:run_id, :url, :title, :source, "
            " :stage, :decision, :sent, :ts, :ts)"
        ),
        {
            "run_id": "test-run",
            "url": url,
            "title": title,
            "source": "TestSource",
            "stage": "scraped",
            "decision": "pending",
            "sent": False,
            "ts": ts,
        },
    )
    await session.commit()


# ── URL canonicalization unit test ────────────────────────────────────────────

def test_canonicalize_url_strips_tracking_params():
    url = "https://example.com/article?id=123&utm_source=google&utm_medium=cpc"
    assert _canonicalize_url(url) == "https://example.com/article?id=123"


def test_canonicalize_url_preserves_non_tracking_params():
    url = "https://example.com/article?page=2&lang=es"
    assert _canonicalize_url(url) == url


def test_canonicalize_url_empty():
    assert _canonicalize_url("") == ""


# ── DB dedup tests ────────────────────────────────────────────────────────────

async def test_dedup_by_url_hash(session: AsyncSession) -> None:
    """Two articles with the same canonical URL: the second is rejected."""
    canonical = "https://milenio.com/nota/incendio-carretera"
    url_with_tracking = canonical + "?utm_source=twitter&utm_medium=social"

    await _insert_log(session, canonical, "Incendio en Carretera Nacional")

    # Incoming URL has tracking params but resolves to same canonical → duplicate
    result = await is_duplicate_db("Titular diferente", url_with_tracking, session)
    assert result is True


async def test_dedup_by_title_hash(session: AsyncSession) -> None:
    """Two articles with the same normalised title: the second is rejected."""
    url_a = "https://milenio.com/nota/1"
    url_b = "https://infobae.com/nota/2"
    title = "Incendio en bodega Carretera Nacional"

    await _insert_log(session, url_a, title)

    # Different URL, but normalised title is identical → duplicate
    result = await is_duplicate_db("el incendio en la bodega carretera nacional", url_b, session)
    assert result is True


async def test_dedup_respects_24h_window(session: AsyncSession) -> None:
    """A duplicate article older than 24 h is NOT considered a duplicate."""
    url = "https://example.com/old-article"
    title = "Bloqueo en Gonzalitos"
    old_time = datetime.now(UTC) - timedelta(hours=48)

    await _insert_log(session, url, title, created_at=old_time)

    result = await is_duplicate_db(title, url, session)
    assert result is False
