"""
FastAPI application — REST API for the incidents dashboard.

Mounts all route modules and configures CORS for frontend access.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, incidents, locations, stats
from app.config.settings import settings
from app.domain.ports import NewsRepository

# ── App instance ─────────────────────────────────────────────

app = FastAPI(
    title="Costco News Monitor API",
    description="REST API for the Costco Monterrey incidents dashboard",
    version="2.0.0",
)

# CORS — allow dashboard frontend from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(incidents.router)
app.include_router(locations.router)
app.include_router(stats.router)


# ── Repository singleton (lazy init) ────────────────────────

_repository: Optional[NewsRepository] = None


def get_repository() -> Optional[NewsRepository]:
    """Get the DB repository (creates it on first call)."""
    global _repository

    if _repository is not None:
        return _repository

    if not settings.database_enabled:
        return None

    try:
        from app.infrastructure.persistence.postgres import PostgresRepository
        _repository = PostgresRepository(settings.database_url)
        return _repository
    except Exception as e:
        print(f"⚠️ DB init error: {e}")
        return None


# ── Startup event ────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    print("🚀 API starting up...")
    print(f"   AI: {settings.ai_provider} / {settings.default_ai_model}")
    print(f"   DB: {'✓' if settings.database_enabled else '✗'}")
    print(f"   Telegram: {'✓' if settings.telegram_enabled else '✗'}")
