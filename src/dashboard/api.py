"""
REST API endpoints for the Costco News Monitor dashboard.

GET /api/incidents — filtered, paginated list with stats.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from src.dashboard.database import DbSession
from src.models.decision_log import DecisionLog

router = APIRouter(prefix="/api", tags=["api"])

# ── Branch → nearest_costco mapping ──────────────────────────────────────────

_BRANCH_MAP: dict[str, str] = {
    "carretera_nacional": "Costco Carretera Nacional",
    "cumbres": "Costco Cumbres",
    "valle_oriente": "Costco Valle Oriente",
}

_SINCE_HOURS: dict[str, int] = {
    "1h": 1,
    "6h": 6,
    "24h": 24,
    "72h": 72,
}


# ── Response schemas ──────────────────────────────────────────────────────────


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    article_url: str
    article_title: str
    source_name: str
    published_at: Optional[datetime]
    incident_type: str
    severity_score: Optional[int]
    affects_operations: Optional[bool]
    geo_lat: Optional[float]
    geo_lon: Optional[float]
    geo_address: Optional[str]
    nearest_costco: Optional[str]
    distance_km: Optional[float]
    within_radius: Optional[bool]
    cost_estimated_usd: Optional[float]
    final_decision: str
    created_at: datetime


class BranchStats(BaseModel):
    carretera_nacional: int = 0
    cumbres: int = 0
    valle_oriente: int = 0


class IncidentStats(BaseModel):
    avg_severity: Optional[float]
    by_branch: BranchStats
    total_cost_usd: float


class IncidentsResponse(BaseModel):
    count: int
    generated_at: datetime
    filters_applied: dict[str, Any]
    incidents: list[IncidentOut]
    stats: IncidentStats


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get("/incidents", response_model=IncidentsResponse)
async def get_incidents(
    session: DbSession,
    since: str = Query(default="24h", pattern="^(1h|6h|24h|72h)$"),
    severity_min: int = Query(default=0, ge=0, le=10),
    branch: str = Query(default="all", pattern="^(carretera_nacional|cumbres|valle_oriente|all)$"),
    within_radius_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
) -> IncidentsResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_SINCE_HOURS[since])

    stmt = (
        select(DecisionLog)
        .where(DecisionLog.incident_type.is_not(None))
        .where(DecisionLog.created_at >= cutoff)
    )

    if severity_min > 0:
        stmt = stmt.where(DecisionLog.severity_score >= severity_min)

    if branch != "all":
        stmt = stmt.where(DecisionLog.nearest_costco == _BRANCH_MAP[branch])

    if within_radius_only:
        stmt = stmt.where(DecisionLog.within_radius.is_(True))

    stmt = stmt.order_by(DecisionLog.created_at.desc()).limit(limit)

    result = await session.execute(stmt)
    rows: list[DecisionLog] = list(result.scalars().all())

    # ── Build stats with SQL aggregates ──────────────────────────────────────
    stats_stmt = (
        select(
            func.avg(DecisionLog.severity_score).label("avg_severity"),
            func.coalesce(func.sum(DecisionLog.cost_estimated_usd), 0.0).label("total_cost_usd"),
        )
        .where(DecisionLog.incident_type.is_not(None))
        .where(DecisionLog.created_at >= cutoff)
    )
    if severity_min > 0:
        stats_stmt = stats_stmt.where(DecisionLog.severity_score >= severity_min)
    if branch != "all":
        stats_stmt = stats_stmt.where(DecisionLog.nearest_costco == _BRANCH_MAP[branch])
    if within_radius_only:
        stats_stmt = stats_stmt.where(DecisionLog.within_radius.is_(True))

    stats_row = (await session.execute(stats_stmt)).one()

    branch_counts: dict[str, int] = {}
    for key, store_name in _BRANCH_MAP.items():
        branch_stmt = (
            select(func.count())
            .select_from(DecisionLog)
            .where(DecisionLog.incident_type.is_not(None))
            .where(DecisionLog.created_at >= cutoff)
            .where(DecisionLog.nearest_costco == store_name)
        )
        if severity_min > 0:
            branch_stmt = branch_stmt.where(DecisionLog.severity_score >= severity_min)
        if within_radius_only:
            branch_stmt = branch_stmt.where(DecisionLog.within_radius.is_(True))
        branch_counts[key] = (await session.execute(branch_stmt)).scalar_one_or_none() or 0

    # ── Serialize incidents ───────────────────────────────────────────────────
    incidents_out = [
        IncidentOut(
            id=str(row.id),
            article_url=row.article_url,
            article_title=row.article_title,
            source_name=row.source_name,
            published_at=row.published_at,
            incident_type=row.incident_type,  # type: ignore[arg-type]
            severity_score=row.severity_score,
            affects_operations=row.affects_operations,
            geo_lat=row.geo_lat,
            geo_lon=row.geo_lon,
            geo_address=row.geo_address,
            nearest_costco=row.nearest_costco,
            distance_km=(
                round(row.nearest_costco_dist_m / 1000, 3)
                if row.nearest_costco_dist_m is not None
                else None
            ),
            within_radius=row.within_radius,
            cost_estimated_usd=row.cost_estimated_usd,
            final_decision=row.final_decision,
            created_at=row.created_at,
        )
        for row in rows
    ]

    avg_sev = float(stats_row.avg_severity) if stats_row.avg_severity is not None else None

    return IncidentsResponse(
        count=len(incidents_out),
        generated_at=datetime.now(timezone.utc),
        filters_applied={
            "since": since,
            "severity_min": severity_min,
            "branch": branch,
            "within_radius_only": within_radius_only,
            "limit": limit,
        },
        incidents=incidents_out,
        stats=IncidentStats(
            avg_severity=avg_sev,
            by_branch=BranchStats(**branch_counts),
            total_cost_usd=float(stats_row.total_cost_usd or 0.0),
        ),
    )
