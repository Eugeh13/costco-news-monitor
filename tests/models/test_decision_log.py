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
        geo_lat=25.639695,
        geo_lon=-100.317631,
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


# ── New fields (Op C hotfix) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_fields_default_to_none_or_false(session: AsyncSession) -> None:
    """All 8 new fields should have correct defaults when not supplied."""
    row = _decision_log("run-101", url="https://example.com/new-defaults")
    session.add(row)
    await session.flush()

    assert row.article_content_snippet is None
    assert row.within_radius is None
    assert row.is_duplicate is None
    assert row.total_tokens_input is None
    assert row.total_tokens_output is None
    assert row.total_latency_ms is None
    assert row.telegram_sent is False
    assert row.error_stage is None


@pytest.mark.asyncio
async def test_article_content_snippet_stored(session: AsyncSession) -> None:
    row = DecisionLog(
        run_id="run-102",
        article_url="https://example.com/snippet",
        article_title="Incendio en Monterrey",
        source_name="Milenio",
        stage_reached=StageReached.triage.value,
        final_decision=FinalDecision.pending.value,
        article_content_snippet="Bomberos atendieron llamado en zona norte...",
    )
    session.add(row)
    await session.flush()
    assert row.article_content_snippet == "Bomberos atendieron llamado en zona norte..."


@pytest.mark.asyncio
async def test_within_radius_and_is_duplicate(session: AsyncSession) -> None:
    row = DecisionLog(
        run_id="run-103",
        article_url="https://example.com/radius",
        article_title="Bloqueo Lázaro Cárdenas",
        source_name="Info7",
        stage_reached=StageReached.geolocation.value,
        final_decision=FinalDecision.alerted.value,
        within_radius=True,
        is_duplicate=False,
    )
    session.add(row)
    await session.flush()
    assert row.within_radius is True
    assert row.is_duplicate is False


@pytest.mark.asyncio
async def test_token_and_latency_tracking(session: AsyncSession) -> None:
    row = DecisionLog(
        run_id="run-104",
        article_url="https://example.com/tokens",
        article_title="Balacera zona sur",
        source_name="El Horizonte",
        stage_reached=StageReached.notification.value,
        final_decision=FinalDecision.alerted.value,
        total_tokens_input=842,
        total_tokens_output=310,
        total_latency_ms=3750,
    )
    session.add(row)
    await session.flush()
    assert row.total_tokens_input == 842
    assert row.total_tokens_output == 310
    assert row.total_latency_ms == 3750


@pytest.mark.asyncio
async def test_telegram_sent_explicit_true(session: AsyncSession) -> None:
    row = DecisionLog(
        run_id="run-105",
        article_url="https://example.com/tg-sent",
        article_title="Accidente autopista",
        source_name="Protección Civil NL",
        stage_reached=StageReached.notification.value,
        final_decision=FinalDecision.alerted.value,
        telegram_sent=True,
    )
    session.add(row)
    await session.flush()
    assert row.telegram_sent is True


@pytest.mark.asyncio
async def test_error_stage_stored(session: AsyncSession) -> None:
    row = DecisionLog(
        run_id="run-106",
        article_url="https://example.com/error-stage",
        article_title="Noticia con error",
        source_name="RSS Directo",
        stage_reached=StageReached.error.value,
        final_decision=FinalDecision.error.value,
        error_message="Nominatim timeout after 3 retries",
        error_stage="geolocation",
    )
    session.add(row)
    await session.flush()
    assert row.error_stage == "geolocation"
    assert row.error_message is not None


@pytest.mark.asyncio
async def test_all_8_new_fields_together(session: AsyncSession) -> None:
    """Integration: store all 8 new fields in a single row."""
    row = DecisionLog(
        run_id="run-107",
        article_url="https://example.com/all-new-fields",
        article_title="Tromba en Valle Oriente",
        source_name="Milenio Monterrey",
        stage_reached=StageReached.notification.value,
        final_decision=FinalDecision.alerted.value,
        article_content_snippet="Fuerte tromba azotó la zona...",
        within_radius=True,
        is_duplicate=False,
        total_tokens_input=1024,
        total_tokens_output=256,
        total_latency_ms=2100,
        telegram_sent=True,
        error_stage=None,
    )
    session.add(row)
    await session.flush()

    assert row.article_content_snippet == "Fuerte tromba azotó la zona..."
    assert row.within_radius is True
    assert row.is_duplicate is False
    assert row.total_tokens_input == 1024
    assert row.total_tokens_output == 256
    assert row.total_latency_ms == 2100
    assert row.telegram_sent is True
    assert row.error_stage is None
