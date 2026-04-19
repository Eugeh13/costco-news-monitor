from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.models import Alert, AnalysisResult, Incident, Source
from src.models.incident import IncidentStatus, IncidentType, Severity


@pytest_asyncio.fixture(scope="module")
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_source(session: AsyncSession) -> None:
    source = Source(name="Milenio Monterrey", type="rss", url="https://milenio.com/rss")
    session.add(source)
    await session.flush()
    assert source.id is not None
    assert source.active is True


@pytest.mark.asyncio
async def test_create_incident_with_source(session: AsyncSession) -> None:
    source = Source(name="El Horizonte", type="rss")
    session.add(source)
    await session.flush()

    incident = Incident(
        title="Choque en Lázaro Cárdenas",
        incident_type=IncidentType.accidente_vial,
        severity=Severity.grave,
        severity_score=7,
        source_id=source.id,
        status=IncidentStatus.pending_analysis,
    )
    session.add(incident)
    await session.flush()

    assert incident.id is not None
    assert incident.status is IncidentStatus.pending_analysis


@pytest.mark.asyncio
async def test_create_analysis_result(session: AsyncSession) -> None:
    incident = Incident(
        title="Incendio en bodega",
        incident_type=IncidentType.incendio,
        severity=Severity.critica,
        severity_score=9,
        status=IncidentStatus.pending_analysis,
    )
    session.add(incident)
    await session.flush()

    result = AnalysisResult(
        incident_id=incident.id,
        model="claude-haiku-4-5",
        prompt_tokens=200,
        completion_tokens=80,
        summary="Incendio grave detectado.",
    )
    session.add(result)
    await session.flush()

    assert result.id is not None
    assert result.incident_id == incident.id


@pytest.mark.asyncio
async def test_create_alert(session: AsyncSession) -> None:
    incident = Incident(
        title="Balacera zona norte",
        incident_type=IncidentType.seguridad,
        severity=Severity.critica,
        severity_score=10,
        status=IncidentStatus.analyzed,
    )
    session.add(incident)
    await session.flush()

    alert = Alert(
        incident_id=incident.id,
        message="🚨 ALERTA COSTCO MTY — Balacera zona norte",
        channel="telegram",
        status="sent",
    )
    session.add(alert)
    await session.flush()

    assert alert.id is not None
    assert alert.channel == "telegram"


@pytest.mark.asyncio
async def test_incident_status_enum_values() -> None:
    statuses = [s.value for s in IncidentStatus]
    assert "pending_analysis" in statuses
    assert "analyzed" in statuses
    assert "alerted" in statuses
    assert "dismissed" in statuses
