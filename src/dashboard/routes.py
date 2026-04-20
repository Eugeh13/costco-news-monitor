"""
Dashboard routes.

GET  /                      — paginated decision_log list with filters
GET  /log/{id}              — detail + feedback form
POST /log/{id}/feedback     — save HumanFeedback
GET  /runs                  — pipeline run summaries
GET  /health
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Integer, desc, func, not_, select

from src.dashboard.database import DbSession
from src.dashboard.main import TEMPLATES
from src.models.decision_log import DecisionLog, FinalDecision, StageReached
from src.models.human_feedback import HumanFeedback, ShouldHaveBeen

router = APIRouter()

PAGE_SIZE = 30


# ── Helpers ───────────────────────────────────────────────────

def _dist_str(meters: Optional[float]) -> str:
    if meters is None:
        return "—"
    if meters < 1000:
        return f"{meters:.0f}m"
    return f"{meters / 1000:.1f}km"


def _sev_class(severity: Optional[int]) -> str:
    if severity is None:
        return ""
    if severity >= 8:
        return "sev-high"
    if severity >= 5:
        return "sev-mid"
    return "sev-low"


def _decision_class(decision: str) -> str:
    if decision == "alerted":
        return "dec-alert"
    if decision == "error":
        return "dec-error"
    return "dec-dismissed"


# ── GET / ─────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: DbSession,
    page: int = Query(1, ge=1),
    run_id: Optional[str] = Query(None),
    final_decision: list[str] = Query(default=[]),
    only_unreviewed: bool = Query(False),
):
    offset = (page - 1) * PAGE_SIZE

    stmt = select(DecisionLog).order_by(desc(DecisionLog.created_at))

    if run_id:
        stmt = stmt.where(DecisionLog.run_id == run_id)
    if final_decision:
        stmt = stmt.where(DecisionLog.final_decision.in_(final_decision))
    if only_unreviewed:
        reviewed_ids = select(HumanFeedback.decision_log_id)
        stmt = stmt.where(not_(DecisionLog.id.in_(reviewed_ids)))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(stmt.offset(offset).limit(PAGE_SIZE))
    logs = result.scalars().all()

    # Runs dropdown — last 10 distinct run_ids
    runs_result = await db.execute(
        select(DecisionLog.run_id, func.min(DecisionLog.created_at).label("started_at"))
        .group_by(DecisionLog.run_id)
        .order_by(desc("started_at"))
        .limit(10)
    )
    runs = runs_result.all()

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "logs": logs,
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "run_id": run_id,
            "selected_decisions": final_decision,
            "only_unreviewed": only_unreviewed,
            "runs": runs,
            "all_decisions": [d.value for d in FinalDecision],
            "dist_str": _dist_str,
            "sev_class": _sev_class,
            "decision_class": _decision_class,
        },
    )


# ── GET /log/{id} ─────────────────────────────────────────────

@router.get("/log/{log_id}", response_class=HTMLResponse)
async def log_detail(request: Request, log_id: int, db: DbSession):
    result = await db.execute(
        select(DecisionLog).where(DecisionLog.id == log_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return HTMLResponse("<h1>Not found</h1>", status_code=404)

    # Next unreviewed log id for keyboard navigation
    reviewed_ids = select(HumanFeedback.decision_log_id)
    next_result = await db.execute(
        select(DecisionLog.id)
        .where(DecisionLog.id > log_id)
        .where(not_(DecisionLog.id.in_(reviewed_ids)))
        .order_by(DecisionLog.id)
        .limit(1)
    )
    next_id = next_result.scalar_one_or_none()

    prev_result = await db.execute(
        select(DecisionLog.id)
        .where(DecisionLog.id < log_id)
        .order_by(desc(DecisionLog.id))
        .limit(1)
    )
    prev_id = prev_result.scalar_one_or_none()

    existing_feedback = entry.human_feedbacks[0] if entry.human_feedbacks else None

    return TEMPLATES.TemplateResponse(
        request,
        "detail.html",
        {
            "entry": entry,
            "next_id": next_id,
            "prev_id": prev_id,
            "existing_feedback": existing_feedback,
            "should_have_options": [s.value for s in ShouldHaveBeen],
            "dist_str": _dist_str,
            "sev_class": _sev_class,
            "decision_class": _decision_class,
        },
    )


# ── POST /log/{id}/feedback ───────────────────────────────────

@router.post("/log/{log_id}/feedback")
async def save_feedback(
    log_id: int,
    db: DbSession,
    should_have_been: Annotated[Optional[str], Form()] = None,
    next_id: Annotated[Optional[int], Form()] = None,
):
    result = await db.execute(select(DecisionLog).where(DecisionLog.id == log_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return HTMLResponse("<h1>Not found</h1>", status_code=404)

    # Upsert: if feedback exists, update it
    if entry.human_feedbacks:
        fb = entry.human_feedbacks[0]
        fb.should_have_been = should_have_been or None
    else:
        fb = HumanFeedback(
            decision_log_id=log_id,
            should_have_been=should_have_been or None,
        )
        db.add(fb)

    await db.flush()

    redirect_to = f"/log/{next_id}" if next_id else "/"
    return RedirectResponse(redirect_to, status_code=303)


# ── GET /runs ─────────────────────────────────────────────────

@router.get("/runs", response_class=HTMLResponse)
async def runs(request: Request, db: DbSession):
    result = await db.execute(
        select(
            DecisionLog.run_id,
            func.min(DecisionLog.created_at).label("started_at"),
            func.max(DecisionLog.created_at).label("ended_at"),
            func.count(DecisionLog.id).label("total"),
            func.sum(
                func.cast(DecisionLog.final_decision == "alerted", Integer)
            ).label("alerts"),
            func.sum(
                func.cast(DecisionLog.final_decision == "error", Integer)
            ).label("errors"),
        )
        .group_by(DecisionLog.run_id)
        .order_by(desc("started_at"))
    )
    run_rows = result.all()

    return TEMPLATES.TemplateResponse(
        request,
        "runs.html",
        {"run_rows": run_rows},
    )


# ── GET /health ───────────────────────────────────────────────

@router.get("/health")
async def health(db: DbSession):
    result = await db.execute(select(func.count()).select_from(DecisionLog))
    count = result.scalar_one_or_none() or 0
    return {"status": "ok", "decision_log_count": count}
