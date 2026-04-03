"""
Health check route — for Railway and monitoring.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.config.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Application health check."""
    db_status = "connected" if settings.database_enabled else "not_configured"
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        database=db_status,
        ai_provider=f"{settings.ai_provider} / {settings.default_ai_model}",
    )
