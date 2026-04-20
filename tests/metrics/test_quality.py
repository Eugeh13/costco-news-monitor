"""Tests for src/metrics/quality.py."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.metrics import quality
from tests.metrics.stubs import DecisionLog, DecisionStage, FinalDecision, HumanFeedback


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


# ── precision / recall — tables absent ───────────────────────────────────────

async def test_precision_absent_table(session: AsyncSession) -> None:
    result = await quality.precision(session)
    assert result == 0.0


async def test_recall_absent_table(session: AsyncSession) -> None:
    result = await quality.recall(session)
    assert result == 0.0


async def test_accuracy_by_stage_absent_table(session: AsyncSession) -> None:
    result = await quality.accuracy_by_stage(session)
    assert result == {}


async def test_top_error_patterns_absent_table(session: AsyncSession) -> None:
    result = await quality.top_error_patterns(session)
    assert result == []


# ── with stub tables created ──────────────────────────────────────────────────

@pytest.fixture()
async def full_session() -> AsyncSession:
    """Session with both core models AND stub tables."""
    from src.models import incident as _  # noqa: F401  ensure Incident is in metadata
    from tests.metrics import stubs as _s  # noqa: F401  ensure stubs are in metadata

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


async def test_precision_with_data(full_session: AsyncSession) -> None:
    from src.models.incident import Incident, IncidentStatus, IncidentType, Severity

    inc = Incident(
        title="X",
        incident_type=IncidentType.incendio,
        severity=Severity.grave,
        status=IncidentStatus.alerted,
    )
    full_session.add(inc)
    await full_session.flush()

    # 3 correct, 1 wrong → precision = 0.75
    full_session.add_all([
        HumanFeedback(incident_id=inc.id, was_correct=True),
        HumanFeedback(incident_id=inc.id, was_correct=True),
        HumanFeedback(incident_id=inc.id, was_correct=True),
        HumanFeedback(incident_id=inc.id, was_correct=False, should_have_been="dismissed"),
    ])
    await full_session.commit()

    result = await quality.precision(full_session)
    assert abs(result - 0.75) < 0.01


async def test_recall_with_data(full_session: AsyncSession) -> None:
    from src.models.incident import Incident, IncidentStatus, IncidentType, Severity

    inc = Incident(
        title="Y",
        incident_type=IncidentType.seguridad,
        severity=Severity.critica,
        status=IncidentStatus.alerted,
    )
    full_session.add(inc)
    await full_session.flush()

    # 2 correct, 1 false negative (should have been alert_sent but wasn't)
    full_session.add_all([
        HumanFeedback(incident_id=inc.id, was_correct=True),
        HumanFeedback(incident_id=inc.id, was_correct=True),
        HumanFeedback(incident_id=inc.id, was_correct=False, should_have_been="alert_sent"),
    ])
    await full_session.commit()

    result = await quality.recall(full_session)
    # TP=2, FN=1 → recall = 2/3
    assert abs(result - 2 / 3) < 0.01
