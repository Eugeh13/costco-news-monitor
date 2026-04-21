"""
Dashboard FastAPI application — Fase A observabilidad.

Run: uvicorn src.dashboard.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text

from src.dashboard.database import get_engine
from src.models.decision_log import DecisionLog

log = structlog.get_logger()

_HERE = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(_HERE / "templates"))


@asynccontextmanager
async def _lifespan(app: FastAPI):
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(select(func.count()).select_from(DecisionLog))  # type: ignore[arg-type]
            count = result.scalar_one_or_none() or 0
    except Exception:
        count = "?"

    log.info(
        "dashboard_ready",
        url="http://localhost:8000",
        decision_logs=count,
    )
    print(f"\n  Dashboard: http://localhost:8000  ({count} decision_logs)\n")
    yield


app = FastAPI(
    title="Costco News Monitor — Dashboard",
    description="Revisión de decisiones del motor de noticias",
    version="0.1.0",
    lifespan=_lifespan,
)

# Static files
app.mount(
    "/static",
    StaticFiles(directory=str(_HERE / "static")),
    name="static",
)

# Routes
from src.dashboard.routes import router  # noqa: E402 — import after app creation
from src.dashboard.api import router as api_router  # noqa: E402
app.include_router(router)
app.include_router(api_router)
