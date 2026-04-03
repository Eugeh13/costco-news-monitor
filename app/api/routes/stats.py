"""
Stats route — aggregate statistics for the dashboard.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.schemas import StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
):
    """Get aggregate incident statistics."""
    from app.api.main import get_repository

    repo = get_repository()
    if not repo:
        return StatsResponse(
            hours=hours,
            total_incidents=0,
            by_category={},
            by_severity={},
            by_costco={},
        )

    return StatsResponse(**repo.get_stats(hours=hours))
