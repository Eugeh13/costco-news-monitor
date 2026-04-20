"""
Test fixtures for dashboard routes.

Uses an in-memory SQLite DB seeded with stub models — no real pipeline needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.dashboard._model_stubs import (
    _Base,
    DecisionLog,
    HumanFeedback,
)

# ── In-memory SQLite engine ───────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(_Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with _test_session_factory() as session:
        yield session
        await session.rollback()


# ── App with overridden DB dependency ────────────────────────

@pytest_asyncio.fixture
async def client():
    from src.dashboard.main import app
    from src.dashboard.database import get_session

    async def _override_get_session():
        async with _test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Seed data helpers ─────────────────────────────────────────

_RUN_ID_A = str(uuid.uuid4())
_RUN_ID_B = str(uuid.uuid4())


def _make_log(
    *,
    run_id: str = _RUN_ID_A,
    source_name: str = "Milenio",
    article_title: str = "Choque en Carretera Nacional",
    article_url: str | None = None,
    stage_reached: str = "alerted",
    final_decision: str = "alert_sent",
    classified_severity: int | None = 8,
    geo_distance_meters: float | None = 1500.0,
    geo_closest_costco: str | None = "Carretera Nacional",
    within_radius: bool | None = True,
) -> DecisionLog:
    return DecisionLog(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        source_name=source_name,
        article_url=article_url or f"https://milenio.com/{uuid.uuid4()}",
        article_title=article_title,
        article_content_snippet="Tres personas resultaron heridas en un choque múltiple.",
        stage_reached=stage_reached,
        triage_passed=True,
        triage_reasoning="Contiene palabras clave de emergencia.",
        classified_type="accidente_vial",
        classified_severity=classified_severity,
        classified_reasoning="Choque múltiple con heridos.",
        geo_address="Carretera Nacional km 268, Monterrey",
        geo_lat=25.6026,
        geo_lon=-100.2640,
        geo_closest_costco=geo_closest_costco,
        geo_distance_meters=geo_distance_meters,
        within_radius=within_radius,
        is_duplicate=False,
        final_decision=final_decision,
        total_tokens_input=500,
        total_tokens_output=200,
        total_latency_ms=3200,
        telegram_sent=final_decision == "alert_sent",
    )


@pytest_asyncio.fixture
async def seed_logs(db_session: AsyncSession) -> list[DecisionLog]:
    logs = [
        _make_log(run_id=_RUN_ID_A, article_title="Choque en Carretera Nacional", final_decision="alert_sent"),
        _make_log(run_id=_RUN_ID_A, article_title="Incendio en bodega Escobedo", final_decision="alert_sent"),
        _make_log(run_id=_RUN_ID_A, article_title="Nota sin relevancia local", final_decision="dismissed_not_relevant", within_radius=False, geo_distance_meters=15000.0),
        _make_log(run_id=_RUN_ID_B, article_title="Balacera en Apodaca", final_decision="dismissed_too_far", within_radius=False, geo_distance_meters=8000.0),
        _make_log(run_id=_RUN_ID_B, article_title="Inundación en San Nicolás", source_name="Info7", final_decision="alert_sent"),
    ]
    for log in logs:
        db_session.add(log)
    await db_session.commit()
    for log in logs:
        await db_session.refresh(log)
    return logs
