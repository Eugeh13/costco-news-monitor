"""Tests for src/metrics/aggregators.py using in-memory SQLite."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.models.incident import Incident, IncidentStatus, IncidentType, Severity
from src.models.source import Source
from src.metrics import aggregators
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


def _incident(
    source_id: int | None = None,
    incident_type: IncidentType = IncidentType.accidente_vial,
    severity: Severity = Severity.moderada,
    status: IncidentStatus = IncidentStatus.pending_analysis,
    offset_hours: int = 0,
) -> Incident:
    return Incident(
        title="Test incident",
        incident_type=incident_type,
        severity=severity,
        status=status,
        source_id=source_id,
        created_at=datetime.now(UTC) - timedelta(hours=offset_hours),
    )


# ── counts_by_stage ───────────────────────────────────────────────────────────

async def test_counts_by_stage_empty(session: AsyncSession) -> None:
    result = await aggregators.counts_by_stage(session)
    assert result == {}


async def test_counts_by_stage_groups_correctly(session: AsyncSession) -> None:
    session.add_all([
        _incident(status=IncidentStatus.pending_analysis),
        _incident(status=IncidentStatus.pending_analysis),
        _incident(status=IncidentStatus.analyzed),
        _incident(status=IncidentStatus.alerted),
    ])
    await session.commit()

    result = await aggregators.counts_by_stage(session)
    assert result["pending_analysis"] == 2
    assert result["analyzed"] == 1
    assert result["alerted"] == 1


# ── distribution_by_type ──────────────────────────────────────────────────────

async def test_distribution_by_type(session: AsyncSession) -> None:
    session.add_all([
        _incident(incident_type=IncidentType.incendio),
        _incident(incident_type=IncidentType.incendio),
        _incident(incident_type=IncidentType.seguridad),
    ])
    await session.commit()

    result = await aggregators.distribution_by_type(session)
    assert result["incendio"] == 2
    assert result["seguridad"] == 1


# ── distribution_by_severity ──────────────────────────────────────────────────

async def test_distribution_by_severity(session: AsyncSession) -> None:
    session.add_all([
        _incident(severity=Severity.critica),
        _incident(severity=Severity.critica),
        _incident(severity=Severity.menor),
    ])
    await session.commit()

    result = await aggregators.distribution_by_severity(session)
    assert result["critica"] == 2
    assert result["menor"] == 1


# ── throughput_per_hour ───────────────────────────────────────────────────────

async def test_throughput_per_hour_recent(session: AsyncSession) -> None:
    # 4 incidents created recently (within last 24 h)
    session.add_all([_incident(offset_hours=i) for i in range(4)])
    await session.commit()

    tph = await aggregators.throughput_per_hour(session)
    assert tph > 0


async def test_throughput_per_hour_no_recent(session: AsyncSession) -> None:
    # All incidents are 48 h old — outside default 24 h window
    session.add_all([_incident(offset_hours=48) for _ in range(3)])
    await session.commit()

    since = datetime.now(UTC) - timedelta(hours=1)
    tph = await aggregators.throughput_per_hour(session, since=since)
    assert tph == 0.0


# ── distribution_by_source ────────────────────────────────────────────────────

async def test_distribution_by_source(session: AsyncSession) -> None:
    src = Source(name="Twitter", type="twitter")
    session.add(src)
    await session.flush()

    session.add_all([
        _incident(source_id=src.id),
        _incident(source_id=src.id),
        _incident(source_id=None),
    ])
    await session.commit()

    result = await aggregators.distribution_by_source(session)
    assert result.get("Twitter") == 2
    assert result.get("unknown") == 1


# ── counts_by_final_decision (table absent → empty dict) ─────────────────────

async def test_counts_by_final_decision_absent_table(session: AsyncSession) -> None:
    # decision_logs table not created in this fixture → should return {}
    result = await aggregators.counts_by_final_decision(session)
    assert isinstance(result, dict)


# ── avg_latency_ms (table absent → 0.0) ──────────────────────────────────────

async def test_avg_latency_ms_absent_table(session: AsyncSession) -> None:
    result = await aggregators.avg_latency_ms(session)
    assert result == 0.0


# ── total_tokens_used (table absent → zeros) ──────────────────────────────────

async def test_total_tokens_used_absent_table(session: AsyncSession) -> None:
    result = await aggregators.total_tokens_used(session)
    assert result == {"prompt": 0, "completion": 0, "total": 0}
