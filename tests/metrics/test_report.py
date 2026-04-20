"""Tests for src/metrics/report.py."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.metrics.report import generate_markdown_report
from tests.metrics.stubs import Base, DecisionLog, FinalDecision, StageReached


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
    stage: str = StageReached.notification.value,
    decision: str = FinalDecision.alerted.value,
    source_name: str = "Twitter",
    incident_type: str | None = "accidente_vial",
    severity_score: int | None = 7,
) -> DecisionLog:
    return DecisionLog(
        run_id="run-01",
        source_name=source_name,
        stage_reached=stage,
        final_decision=decision,
        incident_type=incident_type,
        severity_score=severity_score,
    )


async def test_generate_markdown_report_sections(session: AsyncSession) -> None:
    session.add_all([_log(), _log(decision=FinalDecision.irrelevant.value)])
    await session.commit()

    md = await generate_markdown_report(session)

    assert "# Reporte de Calidad" in md
    assert "## 1. Resumen Ejecutivo" in md
    assert "## 2. Distribución por Etapa" in md
    assert "## 3. Decisiones Finales" in md
    assert "## 4. Calidad por Etapa" in md
    assert "## 5. Distribución de Incidentes" in md
    assert "## 6. Patrones de Error" in md
    assert "## 7. Consumo de Tokens" in md


async def test_generate_markdown_report_stage_data(session: AsyncSession) -> None:
    session.add_all([
        _log(stage=StageReached.triage.value),
        _log(stage=StageReached.triage.value),
        _log(stage=StageReached.notification.value),
    ])
    await session.commit()

    md = await generate_markdown_report(session)
    assert "triage" in md
    assert "notification" in md


async def test_generate_markdown_report_empty_db(session: AsyncSession) -> None:
    """Should not raise even with zero rows in all tables."""
    md = await generate_markdown_report(session)
    assert isinstance(md, str)
    assert len(md) > 100
