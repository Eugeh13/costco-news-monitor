"""
Temporary SQLAlchemy stubs for DecisionLog and HumanFeedback.

These mirror exactly what fase-a/pipeline (claude-1) will create in:
  src/models/decision_log.py
  src/models/human_feedback.py

Once those are merged, delete this file and update imports to use the real models.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class _Base(DeclarativeBase):
    pass


class StageReached(str, enum.Enum):
    triaged = "triaged"
    classified = "classified"
    geolocated = "geolocated"
    deduped = "deduped"
    alerted = "alerted"
    dismissed = "dismissed"


class FinalDecision(str, enum.Enum):
    alert_sent = "alert_sent"
    dismissed_not_relevant = "dismissed_not_relevant"
    dismissed_too_far = "dismissed_too_far"
    dismissed_duplicate = "dismissed_duplicate"
    dismissed_low_severity = "dismissed_low_severity"
    error = "error"


class ShouldHaveBeen(str, enum.Enum):
    should_have_alerted = "should_have_alerted"
    should_have_dismissed = "should_have_dismissed"
    wrong_type = "wrong_type"
    wrong_severity = "wrong_severity"
    wrong_location = "wrong_location"


class DecisionLog(_Base):
    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    article_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    article_title: Mapped[str] = mapped_column(String(512), nullable=False)
    article_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    article_content_snippet: Mapped[Optional[str]] = mapped_column(Text)

    stage_reached: Mapped[str] = mapped_column(String(20), nullable=False)
    triage_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    triage_reasoning: Mapped[Optional[str]] = mapped_column(Text)

    classified_type: Mapped[Optional[str]] = mapped_column(String(100))
    classified_severity: Mapped[Optional[int]] = mapped_column(Integer)
    classified_reasoning: Mapped[Optional[str]] = mapped_column(Text)

    geo_address: Mapped[Optional[str]] = mapped_column(String(512))
    geo_lat: Mapped[Optional[float]] = mapped_column(Float)
    geo_lon: Mapped[Optional[float]] = mapped_column(Float)
    geo_closest_costco: Mapped[Optional[str]] = mapped_column(String(100))
    geo_distance_meters: Mapped[Optional[float]] = mapped_column(Float)
    within_radius: Mapped[Optional[bool]] = mapped_column(Boolean)

    is_duplicate: Mapped[Optional[bool]] = mapped_column(Boolean)
    final_decision: Mapped[str] = mapped_column(String(40), nullable=False)

    error_stage: Mapped[Optional[str]] = mapped_column(String(100))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    total_tokens_input: Mapped[Optional[int]] = mapped_column(Integer)
    total_tokens_output: Mapped[Optional[int]] = mapped_column(Integer)
    total_latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    feedback: Mapped[list["HumanFeedback"]] = relationship(
        "HumanFeedback", back_populates="decision_log", lazy="selectin"
    )


class HumanFeedback(_Base):
    __tablename__ = "human_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_log_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("decision_log.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    should_have_been: Mapped[Optional[str]] = mapped_column(String(40))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    decision_log: Mapped["DecisionLog"] = relationship(
        "DecisionLog", back_populates="feedback"
    )
