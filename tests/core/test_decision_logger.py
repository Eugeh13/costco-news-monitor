"""Tests for src/core/decision_logger.py — uses SQLite in-memory."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.decision_logger import create_run, log_processed_article
from src.models.decision_log import DecisionLog, FinalDecision, StageReached
from src.scrapers.base import RawArticle

import src.models  # noqa: F401 — registers all mappers


def _article(url: str = "https://example.com/news/1", title: str = "Test article") -> RawArticle:
    return RawArticle(
        title=title,
        url=url,
        source_name="test_source",
        published_at=datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc),
        content_snippet="Some content snippet.",
    )


@pytest_asyncio.fixture(scope="module")
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def test_create_run_returns_uuid_string() -> None:
    run_id = create_run()
    assert isinstance(run_id, str)
    assert len(run_id) == 36
    assert run_id.count("-") == 4


def test_create_run_is_unique() -> None:
    assert create_run() != create_run()


@pytest.mark.asyncio
async def test_log_processed_article_insert(session: AsyncSession) -> None:
    run_id = create_run()
    article = _article()

    row = await log_processed_article(session, run_id, article, StageReached.scraped)
    await session.commit()

    assert row.id is not None
    assert row.run_id == run_id
    assert row.article_url == article.url
    assert row.stage_reached == StageReached.scraped.value
    assert row.final_decision == FinalDecision.pending.value


@pytest.mark.asyncio
async def test_log_processed_article_upsert(session: AsyncSession) -> None:
    """Calling log_processed_article twice with same (run_id, url) updates the row."""
    run_id = create_run()
    article = _article(url="https://example.com/upsert-test")

    row1 = await log_processed_article(session, run_id, article, StageReached.scraped)
    await session.commit()
    original_id = row1.id

    row2 = await log_processed_article(
        session, run_id, article,
        StageReached.triage,
        FinalDecision.irrelevant,
        triage_passed=False,
        triage_reason="Not relevant",
    )
    await session.commit()

    assert row2.id == original_id  # same row
    assert row2.stage_reached == StageReached.triage.value
    assert row2.final_decision == FinalDecision.irrelevant.value
    assert row2.triage_passed is False
    assert row2.triage_reason == "Not relevant"


@pytest.mark.asyncio
async def test_log_extra_fields_stored(session: AsyncSession) -> None:
    run_id = create_run()
    article = _article(url="https://example.com/geo-test")

    row = await log_processed_article(
        session, run_id, article,
        StageReached.geolocation,
        FinalDecision.pending,
        geo_lat=25.6457,
        geo_lon=-100.3072,
        geo_address="Av. Lázaro Cárdenas, San Pedro",
        nearest_costco="Costco Valle Oriente",
        nearest_costco_dist_m=450.0,
    )
    await session.commit()

    assert row.geo_lat == pytest.approx(25.6457)
    assert row.nearest_costco == "Costco Valle Oriente"
    assert row.nearest_costco_dist_m == pytest.approx(450.0)


@pytest.mark.asyncio
async def test_log_unknown_field_ignored(session: AsyncSession) -> None:
    """Unknown keyword arguments should not raise errors."""
    run_id = create_run()
    article = _article(url="https://example.com/unknown-fields")

    row = await log_processed_article(
        session, run_id, article,
        StageReached.error,
        FinalDecision.error,
        error_message="test error",
        nonexistent_field="should be ignored",  # type: ignore[call-arg]
    )
    await session.commit()
    assert row.error_message == "test error"


@pytest.mark.asyncio
async def test_different_runs_same_url_are_independent(session: AsyncSession) -> None:
    """Same article URL in two different runs = two separate rows."""
    article = _article(url="https://example.com/same-url")

    run_a = create_run()
    row_a = await log_processed_article(session, run_a, article, StageReached.scraped)
    await session.commit()

    run_b = create_run()
    row_b = await log_processed_article(session, run_b, article, StageReached.scraped)
    await session.commit()

    assert row_a.id != row_b.id
    assert row_a.run_id != row_b.run_id
