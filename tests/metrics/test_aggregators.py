"""Tests for src/metrics/aggregators.py using in-memory SQLite."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.metrics import aggregators
from tests.metrics.stubs import DecisionLog, FinalDecision, StageReached


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


def _log(
    source_name: str = "TestSource",
    stage: str = StageReached.triage.value,
    decision: str = FinalDecision.alerted.value,
    incident_type: str | None = None,
    severity_score: int | None = None,
    total_tokens_input: int | None = None,
    total_tokens_output: int | None = None,
    total_latency_ms: int | None = None,
    within_radius: bool | None = None,
    is_duplicate: bool | None = None,
    telegram_sent: bool = False,
) -> DecisionLog:
    return DecisionLog(
        run_id="run-test-01",
        source_name=source_name,
        stage_reached=stage,
        final_decision=decision,
        incident_type=incident_type,
        severity_score=severity_score,
        total_tokens_input=total_tokens_input,
        total_tokens_output=total_tokens_output,
        total_latency_ms=total_latency_ms,
        within_radius=within_radius,
        is_duplicate=is_duplicate,
        telegram_sent=telegram_sent,
    )


# ── counts_by_stage ───────────────────────────────────────────────────────────

async def test_counts_by_stage_empty(session: AsyncSession) -> None:
    result = await aggregators.counts_by_stage(session)
    assert result == {}


async def test_counts_by_stage_groups_correctly(session: AsyncSession) -> None:
    session.add_all([
        _log(stage=StageReached.triage.value),
        _log(stage=StageReached.triage.value),
        _log(stage=StageReached.geolocation.value),
        _log(stage=StageReached.notification.value),
    ])
    await session.commit()

    result = await aggregators.counts_by_stage(session)
    assert result["triage"] == 2
    assert result["geolocation"] == 1
    assert result["notification"] == 1


# ── counts_by_final_decision ──────────────────────────────────────────────────

async def test_counts_by_final_decision(session: AsyncSession) -> None:
    session.add_all([
        _log(decision=FinalDecision.alerted.value),
        _log(decision=FinalDecision.alerted.value),
        _log(decision=FinalDecision.irrelevant.value),
        _log(decision=FinalDecision.duplicate.value),
    ])
    await session.commit()

    result = await aggregators.counts_by_final_decision(session)
    assert result["alerted"] == 2
    assert result["irrelevant"] == 1
    assert result["duplicate"] == 1


# ── distribution_by_type ──────────────────────────────────────────────────────

async def test_distribution_by_type(session: AsyncSession) -> None:
    session.add_all([
        _log(incident_type="incendio"),
        _log(incident_type="incendio"),
        _log(incident_type="seguridad"),
        _log(incident_type=None),  # unclassified — should be excluded
    ])
    await session.commit()

    result = await aggregators.distribution_by_type(session)
    assert result["incendio"] == 2
    assert result["seguridad"] == 1
    assert "None" not in result


# ── distribution_by_severity ──────────────────────────────────────────────────

async def test_distribution_by_severity(session: AsyncSession) -> None:
    session.add_all([
        _log(severity_score=9),
        _log(severity_score=10),
        _log(severity_score=5),
        _log(severity_score=2),
        _log(severity_score=None),  # excluded
    ])
    await session.commit()

    result = await aggregators.distribution_by_severity(session)
    assert result.get("critica") == 2
    assert result.get("moderada") == 1
    assert result.get("menor") == 1


# ── throughput_per_hour ───────────────────────────────────────────────────────

async def test_throughput_per_hour_with_data(session: AsyncSession) -> None:
    session.add_all([_log() for _ in range(4)])
    await session.commit()

    # All 4 rows have created_at = now (server default), within last 24 h
    tph = await aggregators.throughput_per_hour(session)
    assert tph > 0


async def test_throughput_per_hour_empty(session: AsyncSession) -> None:
    since = datetime.now(UTC) - timedelta(hours=1)
    tph = await aggregators.throughput_per_hour(session, since=since)
    assert tph == 0.0


# ── distribution_by_source ────────────────────────────────────────────────────

async def test_distribution_by_source(session: AsyncSession) -> None:
    session.add_all([
        _log(source_name="Twitter"),
        _log(source_name="Twitter"),
        _log(source_name="GNews"),
    ])
    await session.commit()

    result = await aggregators.distribution_by_source(session)
    assert result["Twitter"] == 2
    assert result["GNews"] == 1


# ── avg_latency_ms ────────────────────────────────────────────────────────────

async def test_avg_latency_ms(session: AsyncSession) -> None:
    session.add_all([
        _log(total_latency_ms=1000),
        _log(total_latency_ms=2000),
    ])
    await session.commit()

    result = await aggregators.avg_latency_ms(session)
    assert abs(result - 1500.0) < 0.1


async def test_avg_latency_ms_no_data(session: AsyncSession) -> None:
    result = await aggregators.avg_latency_ms(session)
    assert result == 0.0


# ── total_tokens_used ─────────────────────────────────────────────────────────

async def test_total_tokens_used(session: AsyncSession) -> None:
    session.add_all([
        _log(total_tokens_input=500, total_tokens_output=100),
        _log(total_tokens_input=300, total_tokens_output=80),
    ])
    await session.commit()

    result = await aggregators.total_tokens_used(session)
    assert result["prompt"] == 800
    assert result["completion"] == 180
    assert result["total"] == 980


async def test_total_tokens_used_no_data(session: AsyncSession) -> None:
    result = await aggregators.total_tokens_used(session)
    assert result == {"prompt": 0, "completion": 0, "total": 0}


# ── counts_within_vs_outside_radius ───────────────────────────────────────────

async def test_counts_within_vs_outside_radius(session: AsyncSession) -> None:
    session.add_all([
        _log(within_radius=True),
        _log(within_radius=True),
        _log(within_radius=False),
        _log(within_radius=None),  # no geo — excluded
    ])
    await session.commit()

    result = await aggregators.counts_within_vs_outside_radius(session)
    assert result["within"] == 2
    assert result["outside"] == 1


async def test_counts_within_vs_outside_radius_empty(session: AsyncSession) -> None:
    result = await aggregators.counts_within_vs_outside_radius(session)
    assert result == {"within": 0, "outside": 0}


# ── duplicate_rate ────────────────────────────────────────────────────────────

async def test_duplicate_rate(session: AsyncSession) -> None:
    session.add_all([
        _log(is_duplicate=True),
        _log(is_duplicate=False),
        _log(is_duplicate=False),
        _log(is_duplicate=None),  # not yet deduped — excluded
    ])
    await session.commit()

    result = await aggregators.duplicate_rate(session)
    assert abs(result - 1 / 3) < 0.01


async def test_duplicate_rate_no_data(session: AsyncSession) -> None:
    result = await aggregators.duplicate_rate(session)
    assert result == 0.0


# ── alerts_actually_sent ──────────────────────────────────────────────────────

async def test_alerts_actually_sent(session: AsyncSession) -> None:
    session.add_all([
        _log(telegram_sent=True),
        _log(telegram_sent=True),
        _log(telegram_sent=False),
    ])
    await session.commit()

    result = await aggregators.alerts_actually_sent(session)
    assert result == 2


async def test_alerts_actually_sent_none(session: AsyncSession) -> None:
    result = await aggregators.alerts_actually_sent(session)
    assert result == 0
