"""
Health check route — for Railway and monitoring.

A2: además del proceso FastAPI, verifica el latido del worker (scheduler).
Si el worker murió o está atorado, devuelve 503 para que Railway reinicie
el contenedor (antes el worker podía morir y /health seguía devolviendo 200).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas import HealthResponse
from app.config.settings import settings
from app.infrastructure import heartbeat

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Application health check (incluye estado del worker)."""
    db_status = "connected" if settings.database_enabled else "not_configured"
    worker_healthy, worker_status, worker_detail = heartbeat.check()

    payload = HealthResponse(
        status="ok" if worker_healthy else "degraded",
        timestamp=datetime.now().isoformat(),
        database=db_status,
        ai_provider=f"{settings.ai_provider} / {settings.default_ai_model}",
        worker=worker_status,
        worker_detail=worker_detail,
    )

    if not worker_healthy:
        # 503 → Railway marca el deploy como no saludable y lo reinicia
        return JSONResponse(status_code=503, content=payload.model_dump())

    return payload
