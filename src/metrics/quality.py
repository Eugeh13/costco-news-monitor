from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# HumanFeedback has no `was_correct` boolean.
# Convention: should_have_been IS NULL  → operator approved the decision (correct)
#             should_have_been IS NOT NULL → operator flagged an error (incorrect)


async def precision(session: AsyncSession) -> float:
    """Fraction of reviewed decisions that were approved by the operator.

    approved / (approved + flagged). Returns 0.0 pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  SUM(CASE WHEN should_have_been IS NULL     THEN 1 ELSE 0 END) AS approved, "
                "  SUM(CASE WHEN should_have_been IS NOT NULL THEN 1 ELSE 0 END) AS flagged "
                "FROM human_feedback"
            )
        )
        row = result.one()
        approved, flagged = int(row.approved or 0), int(row.flagged or 0)
        total = approved + flagged
        return approved / total if total > 0 else 0.0
    except Exception:
        return 0.0


async def recall(session: AsyncSession) -> float:
    """Fraction of should-have-alerted cases that were correctly alerted.

    TP = alerted + approved (should_have_been IS NULL, final_decision='alerted')
    FN = flagged as should_have_been='alerted' but decision was something else.
    Returns 0.0 pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT "
                "  SUM(CASE WHEN d.final_decision = 'alerted' "
                "           AND h.should_have_been IS NULL "
                "       THEN 1 ELSE 0 END) AS tp, "
                "  SUM(CASE WHEN h.should_have_been = 'alerted' "
                "           AND d.final_decision != 'alerted' "
                "       THEN 1 ELSE 0 END) AS fn "
                "FROM human_feedback h "
                "JOIN decision_log d ON d.id = h.decision_log_id"
            )
        )
        row = result.one()
        tp, fn = int(row.tp or 0), int(row.fn or 0)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0
    except Exception:
        return 0.0


async def accuracy_by_stage(session: AsyncSession) -> dict[str, float]:
    """Fraction of approved decisions per pipeline stage_reached.

    Returns empty dict pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT d.stage_reached, "
                "  AVG(CASE WHEN h.should_have_been IS NULL THEN 1.0 ELSE 0.0 END) AS acc "
                "FROM decision_log d "
                "JOIN human_feedback h ON h.decision_log_id = d.id "
                "GROUP BY d.stage_reached"
            )
        )
        return {str(row.stage_reached): float(row.acc) for row in result}
    except Exception:
        return {}


async def top_error_patterns(
    session: AsyncSession,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Most frequent (final_decision, should_have_been) error pairs.

    Returns [] pre-merge.
    """
    try:
        result = await session.execute(
            text(
                "SELECT d.final_decision, "
                "       h.should_have_been, "
                "       COUNT(*) AS n "
                "FROM human_feedback h "
                "JOIN decision_log d ON d.id = h.decision_log_id "
                "WHERE h.should_have_been IS NOT NULL "
                "GROUP BY d.final_decision, h.should_have_been "
                "ORDER BY n DESC "
                f"LIMIT {int(limit)}"
            )
        )
        return [
            {
                "predicted": row.final_decision,
                "should_have_been": row.should_have_been,
                "count": row.n,
            }
            for row in result
        ]
    except Exception:
        return []
