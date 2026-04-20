from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def counts_by_stage(session: AsyncSession) -> dict[str, int]:
    """Incident count grouped by stage_reached from decision_log."""
    try:
        result = await session.execute(
            text(
                "SELECT stage_reached, COUNT(*) AS n "
                "FROM decision_log "
                "GROUP BY stage_reached"
            )
        )
        return {str(row.stage_reached): row.n for row in result}
    except Exception:
        return {}


async def counts_by_final_decision(session: AsyncSession) -> dict[str, int]:
    """Decision counts grouped by final_decision from decision_log.

    Returns empty dict when the table does not exist yet (pre-merge).
    """
    try:
        result = await session.execute(
            text(
                "SELECT final_decision, COUNT(*) AS n "
                "FROM decision_log "
                "GROUP BY final_decision"
            )
        )
        return {str(row.final_decision): row.n for row in result}
    except Exception:
        return {}


async def avg_latency_ms(session: AsyncSession) -> float:
    """Average total pipeline latency in milliseconds across all decision_log rows."""
    try:
        result = await session.execute(
            text("SELECT AVG(total_latency_ms) AS avg_lat FROM decision_log")
        )
        row = result.one_or_none()
        return float(row.avg_lat) if row and row.avg_lat is not None else 0.0
    except Exception:
        return 0.0


async def total_tokens_used(session: AsyncSession) -> dict[str, int]:
    """Total prompt + completion tokens from decision_log."""
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  COALESCE(SUM(total_tokens_input), 0)  AS prompt_total, "
                "  COALESCE(SUM(total_tokens_output), 0) AS completion_total "
                "FROM decision_log"
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
    """Articles processed per hour since `since` (defaults to last 24 h)."""
    if since is None:
        since = datetime.now(UTC) - timedelta(hours=24)

    try:
        result = await session.execute(
            text(
                "SELECT COUNT(*) AS n FROM decision_log "
                "WHERE created_at >= :since"
            ),
            {"since": since.isoformat()},
        )
        count = result.scalar_one()
        elapsed_hours = (datetime.now(UTC) - since).total_seconds() / 3600
        return count / elapsed_hours if elapsed_hours > 0 else 0.0
    except Exception:
        return 0.0


async def distribution_by_source(session: AsyncSession) -> dict[str, int]:
    """Article count grouped by source_name from decision_log."""
    try:
        result = await session.execute(
            text(
                "SELECT source_name, COUNT(*) AS n "
                "FROM decision_log "
                "GROUP BY source_name"
            )
        )
        return {str(row.source_name or "unknown"): row.n for row in result}
    except Exception:
        return {}


async def distribution_by_type(session: AsyncSession) -> dict[str, int]:
    """Article count grouped by incident_type from decision_log (classified articles only)."""
    try:
        result = await session.execute(
            text(
                "SELECT incident_type, COUNT(*) AS n "
                "FROM decision_log "
                "WHERE incident_type IS NOT NULL "
                "GROUP BY incident_type"
            )
        )
        return {str(row.incident_type): row.n for row in result}
    except Exception:
        return {}


async def distribution_by_severity(session: AsyncSession) -> dict[str, int]:
    """Article count grouped into severity bands based on severity_score (1-10)."""
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  CASE "
                "    WHEN severity_score >= 9 THEN 'critica' "
                "    WHEN severity_score >= 7 THEN 'grave' "
                "    WHEN severity_score >= 4 THEN 'moderada' "
                "    ELSE 'menor' "
                "  END AS band, "
                "  COUNT(*) AS n "
                "FROM decision_log "
                "WHERE severity_score IS NOT NULL "
                "GROUP BY band"
            )
        )
        return {str(row.band): row.n for row in result}
    except Exception:
        return {}
