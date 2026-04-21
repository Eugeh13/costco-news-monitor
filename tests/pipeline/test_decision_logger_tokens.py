"""
Integration tests: TokenAccumulator + log_processed_article token persistence.

Verifies that every terminal exit path in the pipeline correctly persists
token usage and cost fields to the decision_log table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.decision_logger import create_run, log_processed_article
from src.core.token_counter import TokenAccumulator
from src.models.decision_log import FinalDecision, StageReached
from src.scrapers.base import RawArticle

import src.models  # noqa: F401 — registers all mappers


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _article(url: str | None = None) -> RawArticle:
    import uuid
    return RawArticle(
        title="Choque en Lázaro Cárdenas km 800",
        url=url or f"https://milenio.com/{uuid.uuid4()}",
        source_name="Milenio",
        published_at=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        content_snippet="Accidente con múltiples heridos.",
    )


def _fake_response(
    *,
    input_tokens: int = 200,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> MagicMock:
    """Build a minimal Anthropic response mock with usage attributes."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = cache_read
    usage.cache_creation_input_tokens = cache_creation
    resp = MagicMock()
    resp.usage = usage
    return resp


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logger_persists_tokens_on_alerted_record(session: AsyncSession) -> None:
    """Token fields are written when final_decision=alerted."""
    run_id = create_run()
    article = _article()
    acc = TokenAccumulator()
    acc.add_response(_fake_response(input_tokens=300, output_tokens=80))

    row = await log_processed_article(
        session, run_id, article,
        StageReached.notification,
        FinalDecision.alerted,
        total_tokens_input=acc.input_tokens,
        total_tokens_output=acc.output_tokens,
        total_tokens_cache_read=acc.cache_read_tokens,
        total_tokens_cache_creation=acc.cache_creation_tokens,
        cost_estimated_usd=acc.cost_usd,
    )
    await session.commit()

    assert row.total_tokens_input == 300
    assert row.total_tokens_output == 80
    assert row.total_tokens_cache_read == 0
    assert row.total_tokens_cache_creation == 0
    assert row.cost_estimated_usd == pytest.approx(acc.cost_usd, rel=1e-6)


@pytest.mark.asyncio
async def test_logger_persists_tokens_on_classified_record(session: AsyncSession) -> None:
    """Classified articles that end out_of_radius must also have tokens saved.

    This is the primary regression test for the bug: 17/28 classified records
    were out_of_radius with NULL total_tokens_input.
    """
    run_id = create_run()
    article = _article()
    acc = TokenAccumulator()
    acc.add_response(_fake_response(input_tokens=500, output_tokens=120, cache_read=450))

    row = await log_processed_article(
        session, run_id, article,
        StageReached.geolocation,
        FinalDecision.out_of_radius,
        geo_lat=25.68,
        geo_lon=-100.31,
        nearest_costco="Costco Cumbres",
        nearest_costco_dist_m=4800.0,
        total_tokens_input=acc.input_tokens,
        total_tokens_output=acc.output_tokens,
        total_tokens_cache_read=acc.cache_read_tokens,
        total_tokens_cache_creation=acc.cache_creation_tokens,
        cost_estimated_usd=acc.cost_usd,
    )
    await session.commit()

    assert row.final_decision == FinalDecision.out_of_radius.value
    assert row.total_tokens_input == 500
    assert row.total_tokens_output == 120
    assert row.total_tokens_cache_read == 450
    assert row.cost_estimated_usd is not None
    assert row.cost_estimated_usd > 0


@pytest.mark.asyncio
async def test_logger_persists_tokens_on_triage_failed_record(session: AsyncSession) -> None:
    """Triage-failed (irrelevant) articles have triage tokens persisted."""
    run_id = create_run()
    article = _article()
    acc = TokenAccumulator()
    acc.add_response(_fake_response(input_tokens=150, output_tokens=20))

    row = await log_processed_article(
        session, run_id, article,
        StageReached.triage,
        FinalDecision.irrelevant,
        triage_passed=False,
        total_tokens_input=acc.input_tokens,
        total_tokens_output=acc.output_tokens,
        total_tokens_cache_read=acc.cache_read_tokens,
        total_tokens_cache_creation=acc.cache_creation_tokens,
        cost_estimated_usd=acc.cost_usd,
    )
    await session.commit()

    assert row.final_decision == FinalDecision.irrelevant.value
    assert row.triage_passed is False
    assert row.total_tokens_input == 150
    assert row.total_tokens_output == 20
    assert row.cost_estimated_usd is not None


@pytest.mark.asyncio
async def test_cost_estimated_calculated_correctly(session: AsyncSession) -> None:
    """cost_usd formula: input*1e-6 + cache_read*0.1e-6 + cache_creation*1.25e-6 + output*5e-6."""
    acc = TokenAccumulator()
    acc.add_response(_fake_response(
        input_tokens=1_000_000,
        output_tokens=200_000,
        cache_read=500_000,
        cache_creation=100_000,
    ))
    # Expected:
    # input:          1_000_000 * 1e-6    = 1.000
    # cache_read:       500_000 * 0.1e-6  = 0.050
    # cache_creation:   100_000 * 1.25e-6 = 0.125
    # output:           200_000 * 5e-6    = 1.000
    # total = 2.175
    expected = 1.0 + 0.05 + 0.125 + 1.0
    assert acc.cost_usd == pytest.approx(expected, rel=1e-9)

    # Persist and verify DB stores it faithfully
    run_id = create_run()
    article = _article()
    row = await log_processed_article(
        session, run_id, article,
        StageReached.notification,
        FinalDecision.alerted,
        cost_estimated_usd=acc.cost_usd,
    )
    await session.commit()
    assert row.cost_estimated_usd == pytest.approx(expected, rel=1e-6)


@pytest.mark.asyncio
async def test_cache_tokens_counted_separately(session: AsyncSession) -> None:
    """Cache read and cache creation tokens are tracked independently per call."""
    acc = TokenAccumulator()

    # First call: cache creation (cold)
    acc.add_response(_fake_response(input_tokens=100, output_tokens=30, cache_creation=900))
    assert acc.cache_creation_tokens == 900
    assert acc.cache_read_tokens == 0

    # Second call: cache hit (warm)
    acc.add_response(_fake_response(input_tokens=50, output_tokens=30, cache_read=900))
    assert acc.cache_read_tokens == 900
    assert acc.cache_creation_tokens == 900  # unchanged from first call

    # Total input is the sum of both calls
    assert acc.input_tokens == 150
    assert acc.output_tokens == 60

    # Persist and verify both fields stored
    run_id = create_run()
    article = _article()
    row = await log_processed_article(
        session, run_id, article,
        StageReached.geolocation,
        FinalDecision.pending,
        total_tokens_cache_read=acc.cache_read_tokens,
        total_tokens_cache_creation=acc.cache_creation_tokens,
    )
    await session.commit()
    assert row.total_tokens_cache_read == 900
    assert row.total_tokens_cache_creation == 900
