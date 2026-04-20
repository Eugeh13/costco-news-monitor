from __future__ import annotations

from collections import Counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def precision(session: AsyncSession) -> float:
    """TP / (TP + FP) across all HumanFeedback rows.

    Returns 0.0 when the table does not exist (pre-merge).
    """
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  SUM(CASE WHEN was_correct THEN 1 ELSE 0 END)     AS tp, "
                "  SUM(CASE WHEN NOT was_correct THEN 1 ELSE 0 END) AS fp "
                "FROM human_feedbacks"
            )
        )
        row = result.one()
        tp, fp = int(row.tp or 0), int(row.fp or 0)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0
    except Exception:
        return 0.0


async def recall(session: AsyncSession) -> float:
    """TP / (TP + FN): incidents correctly alerted vs. all that should have been.

    FN = rows where was_correct=False AND should_have_been='alert_sent'.
    Returns 0.0 pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) AS tp, "
                "  SUM(CASE WHEN NOT was_correct "
                "       AND should_have_been = 'alert_sent' "
                "       THEN 1 ELSE 0 END) AS fn "
                "FROM human_feedbacks"
            )
        )
        row = result.one()
        tp, fn = int(row.tp or 0), int(row.fn or 0)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0
    except Exception:
        return 0.0


async def accuracy_by_stage(session: AsyncSession) -> dict[str, float]:
    """Fraction of correct decisions per pipeline stage from DecisionLog + HumanFeedback.

    Returns empty dict pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT d.stage, "
                "  AVG(CASE WHEN d.was_correct THEN 1.0 ELSE 0.0 END) AS acc "
                "FROM decision_logs d "
                "GROUP BY d.stage"
            )
        )
        return {str(row.stage): float(row.acc) for row in result}
    except Exception:
        return {}


async def top_error_patterns(
    session: AsyncSession,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Most frequent (predicted, should_have_been) error pairs from HumanFeedback.

    Returns [] pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT d.final_decision AS predicted, "
                "       h.should_have_been, "
                "       COUNT(*) AS n "
                "FROM human_feedbacks h "
                "JOIN decision_logs d ON d.incident_id = h.incident_id "
                "WHERE NOT h.was_correct "
                "GROUP BY d.final_decision, h.should_have_been "
                "ORDER BY n DESC "
                f"LIMIT {int(limit)}"
            )
        )
        return [
            {
                "predicted": row.predicted,
                "should_have_been": row.should_have_been,
                "count": row.n,
            }
            for row in result
        ]
    except Exception:
        return []
