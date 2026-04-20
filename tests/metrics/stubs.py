"""Local stubs for DecisionLog and HumanFeedback.

These mirror the exact schema defined in FASE_A.md + claude-1's implementation.
Used ONLY in tests — never import from src/.
"""
from __future__ import annotations

import enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class StageReached(str, enum.Enum):
    scraped = "scraped"
    triage = "triage"
    deep_analysis = "deep_analysis"
    geolocation = "geolocation"
    dedup = "dedup"
    notification = "notification"
    error = "error"


class FinalDecision(str, enum.Enum):
    irrelevant = "irrelevant"
    duplicate = "duplicate"
    out_of_radius = "out_of_radius"
    no_geo = "no_geo"
    alerted = "alerted"
    error = "error"
    pending = "pending"


class ShouldHaveBeen(str, enum.Enum):
    alerted = "alerted"
    dismissed = "dismissed"
    escalated = "escalated"


class DecisionLog(Base):
    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    article_url: Mapped[str] = mapped_column(Text, nullable=False, default="http://example.com")
    article_title: Mapped[str] = mapped_column(Text, nullable=False, default="Test article")
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_reached: Mapped[str] = mapped_column(String(30), nullable=False)
    final_decision: Mapped[str] = mapped_column(String(30), nullable=False)
    triage_passed: Mapped[bool | None] = mapped_column(Boolean)
    incident_type: Mapped[str | None] = mapped_column(String(50))
    severity_score: Mapped[int | None] = mapped_column(Integer)
    geo_lat: Mapped[float | None] = mapped_column(Float)
    geo_lon: Mapped[float | None] = mapped_column(Float)
    geo_address: Mapped[str | None] = mapped_column(Text)
    nearest_costco: Mapped[str | None] = mapped_column(String(100))
    nearest_costco_dist_m: Mapped[float | None] = mapped_column(Float)
    total_tokens_input: Mapped[int | None] = mapped_column(Integer)
    total_tokens_output: Mapped[int | None] = mapped_column(Integer)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HumanFeedback(Base):
    __tablename__ = "human_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_log_id: Mapped[int] = mapped_column(
        ForeignKey("decision_log.id", ondelete="CASCADE"), nullable=False, index=True
    )
    should_have_been: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
