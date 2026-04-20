"""Tests for src/metrics/report.py."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.metrics.report import generate_markdown_report
from src.models.incident import Incident, IncidentStatus, IncidentType, Severity


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


async def test_generate_markdown_report_structure(session: AsyncSession) -> None:
    session.add_all([
        Incident(
            title="Inc A",
            incident_type=IncidentType.accidente_vial,
            severity=Severity.grave,
            status=IncidentStatus.alerted,
        ),
        Incident(
            title="Inc B",
            incident_type=IncidentType.incendio,
            severity=Severity.critica,
            status=IncidentStatus.dismissed,
        ),
    ])
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


async def test_generate_markdown_report_counts(session: AsyncSession) -> None:
    session.add_all([
        Incident(
            title="X",
            incident_type=IncidentType.seguridad,
            severity=Severity.moderada,
            status=IncidentStatus.alerted,
        )
    ])
    await session.commit()

    md = await generate_markdown_report(session)
    # Total incidents appears in executive summary
    assert "1 |" in md or "| 1 " in md


async def test_generate_markdown_report_empty_db(session: AsyncSession) -> None:
    """Should not raise even with zero rows in all tables."""
    md = await generate_markdown_report(session)
    assert isinstance(md, str)
    assert len(md) > 100
