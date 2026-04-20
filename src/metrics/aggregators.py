from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import Incident, IncidentType, Severity


async def counts_by_stage(session: AsyncSession) -> dict[str, int]:
    """Returns incident count grouped by status (pipeline stage)."""
    rows = await session.execute(
        select(Incident.status, func.count().label("n"))
        .group_by(Incident.status)
    )
    return {str(row.status.value): row.n for row in rows}


async def counts_by_final_decision(session: AsyncSession) -> dict[str, int]:
    """Returns decision counts grouped by final_decision from DecisionLog.

    Falls back to empty dict when the table does not exist yet (pre-merge).
    """
    try:
        result = await session.execute(
            text(
                "SELECT final_decision, COUNT(*) AS n "
                "FROM decision_logs "
                "GROUP BY final_decision"
            )
        )
        return {str(row.final_decision): row.n for row in result}
    except Exception:
        return {}


async def avg_latency_ms(session: AsyncSession) -> float:
    """Average pipeline latency in milliseconds across all DecisionLog rows."""
    try:
        result = await session.execute(
            text("SELECT AVG(latency_ms) AS avg_lat FROM decision_logs")
        )
        row = result.one_or_none()
        return float(row.avg_lat) if row and row.avg_lat is not None else 0.0
    except Exception:
        return 0.0


async def total_tokens_used(session: AsyncSession) -> dict[str, int]:
    """Total prompt + completion tokens from DecisionLog."""
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  COALESCE(SUM(input_tokens), 0)  AS prompt_total, "
                "  COALESCE(SUM(output_tokens), 0) AS completion_total "
                "FROM decision_logs"
            )
        )
        row = result.one()
        return {
            "prompt": int(row.prompt_total),
            "completion": int(row.completion_total),
            "total": int(row.prompt_total) + int(row.completion_total),
        }
    except Exception:
        return {"prompt": 0, "completion": 0, "total": 0}


async def throughput_per_hour(
    session: AsyncSession,
    since: datetime | None = None,
) -> float:
    """Incidents processed per hour since `since` (defaults to last 24 h)."""
    if since is None:
        since = datetime.now(UTC) - timedelta(hours=24)

    result = await session.execute(
        select(func.count()).where(Incident.created_at >= since)
    )
    count = result.scalar_one()
    elapsed_hours = (datetime.now(UTC) - since).total_seconds() / 3600
    return count / elapsed_hours if elapsed_hours > 0 else 0.0


async def distribution_by_source(session: AsyncSession) -> dict[str, int]:
    """Incident count grouped by source name."""
    rows = await session.execute(
        text(
            "SELECT s.name AS source_name, COUNT(*) AS n "
            "FROM incidents i "
            "LEFT JOIN sources s ON s.id = i.source_id "
            "GROUP BY s.name"
        )
    )
    return {str(row.source_name or "unknown"): row.n for row in rows}


async def distribution_by_type(session: AsyncSession) -> dict[str, int]:
    """Incident count grouped by incident_type."""
    rows = await session.execute(
        select(Incident.incident_type, func.count().label("n"))
        .group_by(Incident.incident_type)
    )
    return {str(row.incident_type.value): row.n for row in rows}


async def distribution_by_severity(session: AsyncSession) -> dict[str, int]:
    """Incident count grouped by severity level."""
    rows = await session.execute(
        select(Incident.severity, func.count().label("n"))
        .group_by(Incident.severity)
    )
    return {str(row.severity.value): row.n for row in rows}
