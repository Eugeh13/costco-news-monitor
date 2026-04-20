"""
DecisionLogger — persiste cada paso del pipeline en decision_log.

Patrón UPSERT: SELECT → INSERT o UPDATE por (run_id, article_url).
Compatible con PostgreSQL y SQLite.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.decision_log import DecisionLog, FinalDecision, StageReached
from src.scrapers.base import RawArticle

logger = structlog.get_logger(__name__)


def create_run() -> str:
    """Generate and return a new pipeline run ID (UUID4 string)."""
    return str(uuid.uuid4())


async def log_processed_article(
    session: AsyncSession,
    run_id: str,
    article: RawArticle,
    stage: StageReached,
    final_decision: FinalDecision = FinalDecision.pending,
    **fields: Any,
) -> DecisionLog:
    """
    UPSERT a DecisionLog row keyed on (run_id, article_url).

    Extra keyword arguments map directly to DecisionLog columns
    (e.g. triage_passed=True, severity_score=7, geo_lat=25.6).
    Unknown keys are silently ignored so callers don't need to be exhaustive.
    """
    stmt = select(DecisionLog).where(
        DecisionLog.run_id == run_id,
        DecisionLog.article_url == article.url,
    )
    result = await session.execute(stmt)
    row: DecisionLog | None = result.scalar_one_or_none()

    _allowed = {c.key for c in DecisionLog.__table__.columns}
    safe_fields = {k: v for k, v in fields.items() if k in _allowed}

    if row is None:
        row = DecisionLog(
            run_id=run_id,
            article_url=article.url,
            article_title=article.title,
            source_name=article.source_name,
            published_at=article.published_at,
            stage_reached=stage.value,
            final_decision=final_decision.value,
            **safe_fields,
        )
        session.add(row)
        logger.debug(
            "decision_log.insert run=%s url=%s stage=%s decision=%s",
            run_id, article.url, stage.value, final_decision.value,
        )
    else:
        row.stage_reached = stage.value
        row.final_decision = final_decision.value
        row.updated_at = datetime.utcnow()  # type: ignore[assignment]
        for k, v in safe_fields.items():
            setattr(row, k, v)
        logger.debug(
            "decision_log.update id=%d run=%s stage=%s decision=%s",
            row.id, run_id, stage.value, final_decision.value,
        )

    await session.flush()
    return row
