"""Tests for DecisionLog and HumanFeedback models."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.models.decision_log import DecisionLog, FinalDecision, StageReached
from src.models.human_feedback import HumanFeedback, ShouldHaveBeen

import src.models  # noqa: F401 — registers all mappers


@pytest_asyncio.fixture(scope="module")
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _decision_log(run_id: str, url: str = "https://example.com/1") -> DecisionLog:
    return DecisionLog(
        run_id=run_id,
        article_url=url,
        article_title="Choque en Lázaro Cárdenas",
        source_name="Milenio Monterrey",
        stage_reached=StageReached.scraped.value,
        final_decision=FinalDecision.pending.value,
    )


# ── Enum value tests ──────────────────────────────────────────────────────────

def test_stage_reached_values() -> None:
    values = {s.value for s in StageReached}
    assert values == {"scraped", "triage", "deep_analysis", "geolocation", "dedup", "notification", "error"}


def test_final_decision_values() -> None:
    values = {d.value for d in FinalDecision}
    assert values == {"irrelevant", "duplicate", "out_of_radius", "no_geo", "alerted", "error", "pending"}


def test_should_have_been_values() -> None:
    values = {s.value for s in ShouldHaveBeen}
    assert values == {"alerted", "dismissed", "escalated"}


# ── Persistence tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_decision_log(session: AsyncSession) -> None:
    row = _decision_log("run-001")
    session.add(row)
    await session.flush()

    assert row.id is not None
    assert row.stage_reached == "scraped"
    assert row.final_decision == "pending"
    assert row.created_at is not None


@pytest.mark.asyncio
async def test_decision_log_nullable_fields(session: AsyncSession) -> None:
    row = _decision_log("run-002", url="https://example.com/2")
    session.add(row)
    await session.flush()

    assert row.triage_passed is None
    assert row.geo_lat is None
    assert row.severity_score is None
    assert row.error_message is None


@pytest.mark.asyncio
async def test_decision_log_full_fields(session: AsyncSession) -> None:
    row = DecisionLog(
        run_id="run-003",
        article_url="https://example.com/3",
        article_title="Incendio en bodega",
        source_name="Info7",
        stage_reached=StageReached.notification.value,
        final_decision=FinalDecision.alerted.value,
        triage_passed=True,
        incident_type="fire",
        severity_score=8,
        affects_operations=True,
        geo_lat=25.6457,
        geo_lon=-100.3072,
        geo_address="Av. Lázaro Cárdenas, San Pedro",
        nearest_costco="Costco Valle Oriente",
        nearest_costco_dist_m=820.5,
    )
    session.add(row)
    await session.flush()

    assert row.severity_score == 8
    assert row.final_decision == FinalDecision.alerted.value
    assert row.nearest_costco_dist_m == pytest.approx(820.5)


@pytest.mark.asyncio
async def test_human_feedback_relationship(session: AsyncSession) -> None:
    dl = _decision_log("run-004", url="https://example.com/4")
    session.add(dl)
    await session.flush()

    fb = HumanFeedback(
        decision_log_id=dl.id,
        should_have_been=ShouldHaveBeen.alerted.value,
    )
    session.add(fb)
    await session.flush()

    assert fb.id is not None
    assert fb.decision_log_id == dl.id


@pytest.mark.asyncio
async def test_human_feedback_cascade_delete(session: AsyncSession) -> None:
    dl = _decision_log("run-005", url="https://example.com/5")
    session.add(dl)
    await session.flush()

    fb = HumanFeedback(decision_log_id=dl.id, should_have_been=None)
    session.add(fb)
    await session.flush()
    fb_id = fb.id

    await session.delete(dl)
    await session.flush()

    from sqlalchemy import select
    result = await session.execute(select(HumanFeedback).where(HumanFeedback.id == fb_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_unique_constraint_run_url(session: AsyncSession) -> None:
    """Two rows with same (run_id, article_url) should violate unique constraint."""
    from sqlalchemy.exc import IntegrityError

    dl1 = _decision_log("run-006", url="https://example.com/dup")
    dl2 = _decision_log("run-006", url="https://example.com/dup")
    session.add(dl1)
    await session.flush()

    session.add(dl2)
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()
