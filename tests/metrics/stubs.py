"""Local stubs for DecisionLog and HumanFeedback.

These mirror the shape that claude-1/fase-a/pipeline will create.
Used ONLY in tests — never import from src/.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DecisionStage(str, enum.Enum):
    triage = "triage"
    classification = "classification"
    geo = "geo"
    dedup = "dedup"
    notification = "notification"


class FinalDecision(str, enum.Enum):
    alert_sent = "alert_sent"
    dismissed = "dismissed"
    passed = "passed"


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[DecisionStage] = mapped_column(
        Enum(DecisionStage, name="decisionstage"), nullable=False
    )
    final_decision: Mapped[FinalDecision] = mapped_column(
        Enum(FinalDecision, name="finaldecision"), nullable=False
    )
    run_id: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    was_correct: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HumanFeedback(Base):
    __tablename__ = "human_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    should_have_been: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
