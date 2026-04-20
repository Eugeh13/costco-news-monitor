"""Tests for src/metrics/quality.py."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.metrics import quality
from tests.metrics.stubs import Base, DecisionLog, FinalDecision, HumanFeedback, StageReached


@pytest.fixture()
async def session() -> AsyncSession:
    """Session with stub tables (decision_log + human_feedback) + core models."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


def _log(
    stage: str = StageReached.notification.value,
    decision: str = FinalDecision.alerted.value,
) -> DecisionLog:
    return DecisionLog(
        run_id="run-01",
        source_name="TestSource",
        stage_reached=stage,
        final_decision=decision,
    )


# ── tables absent (try/except fallbacks) ──────────────────────────────────────

async def test_precision_no_data(session: AsyncSession) -> None:
    result = await quality.precision(session)
    assert result == 0.0


async def test_recall_no_data(session: AsyncSession) -> None:
    result = await quality.recall(session)
    assert result == 0.0


async def test_accuracy_by_stage_no_data(session: AsyncSession) -> None:
    result = await quality.accuracy_by_stage(session)
    assert result == {}


async def test_top_error_patterns_no_data(session: AsyncSession) -> None:
    result = await quality.top_error_patterns(session)
    assert result == []


# ── precision with real data ──────────────────────────────────────────────────

async def test_precision_with_data(session: AsyncSession) -> None:
    log = _log()
    session.add(log)
    await session.flush()

    # 3 approved (should_have_been IS NULL), 1 flagged → precision = 0.75
    session.add_all([
        HumanFeedback(decision_log_id=log.id, should_have_been=None),
        HumanFeedback(decision_log_id=log.id, should_have_been=None),
        HumanFeedback(decision_log_id=log.id, should_have_been=None),
        HumanFeedback(decision_log_id=log.id, should_have_been="dismissed"),
    ])
    await session.commit()

    result = await quality.precision(session)
    assert abs(result - 0.75) < 0.01


# ── recall with real data ─────────────────────────────────────────────────────

async def test_recall_with_data(session: AsyncSession) -> None:
    alerted_log = _log(decision=FinalDecision.alerted.value)
    missed_log = _log(decision=FinalDecision.irrelevant.value)
    session.add_all([alerted_log, missed_log])
    await session.flush()

    # TP: alerted correctly (should_have_been IS NULL)
    session.add(HumanFeedback(decision_log_id=alerted_log.id, should_have_been=None))
    session.add(HumanFeedback(decision_log_id=alerted_log.id, should_have_been=None))
    # FN: should have alerted but was dismissed
    session.add(HumanFeedback(decision_log_id=missed_log.id, should_have_been="alerted"))
    await session.commit()

    result = await quality.recall(session)
    # TP=2, FN=1 → recall = 2/3
    assert abs(result - 2 / 3) < 0.01


# ── accuracy_by_stage ─────────────────────────────────────────────────────────

async def test_accuracy_by_stage_with_data(session: AsyncSession) -> None:
    log_triage = _log(stage=StageReached.triage.value)
    log_notif = _log(stage=StageReached.notification.value)
    session.add_all([log_triage, log_notif])
    await session.flush()

    session.add(HumanFeedback(decision_log_id=log_triage.id, should_have_been=None))  # correct
    session.add(HumanFeedback(decision_log_id=log_notif.id, should_have_been="dismissed"))  # wrong
    await session.commit()

    result = await quality.accuracy_by_stage(session)
    assert abs(result.get("triage", -1) - 1.0) < 0.01
    assert abs(result.get("notification", -1) - 0.0) < 0.01


# ── top_error_patterns ────────────────────────────────────────────────────────

async def test_top_error_patterns_with_data(session: AsyncSession) -> None:
    log1 = _log(decision=FinalDecision.irrelevant.value)
    log2 = _log(decision=FinalDecision.irrelevant.value)
    session.add_all([log1, log2])
    await session.flush()

    session.add(HumanFeedback(decision_log_id=log1.id, should_have_been="alerted"))
    session.add(HumanFeedback(decision_log_id=log2.id, should_have_been="alerted"))
    await session.commit()

    result = await quality.top_error_patterns(session)
    assert len(result) == 1
    assert result[0]["predicted"] == "irrelevant"
    assert result[0]["should_have_been"] == "alerted"
    assert result[0]["count"] == 2
