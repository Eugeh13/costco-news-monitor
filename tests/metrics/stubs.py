"""Local stubs for DecisionLog and HumanFeedback.

Match the REAL model in src/models/decision_log.py (v2-rewrite) plus the 8 fields
that claude-1 adds in hotfix/model-fields. Field names here MUST equal SQLAlchemy
column names — used ONLY in tests, never imported from src/.
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
    """Mirrors src/models/decision_log.py — real fields + 8 added by hotfix/model-fields."""

    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # ── Article metadata ──────────────────────────────────────────────────────
    article_url: Mapped[str] = mapped_column(Text, nullable=False, default="http://example.com")
    article_title: Mapped[str] = mapped_column(Text, nullable=False, default="Test article")
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    published_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    article_content_snippet: Mapped[str | None] = mapped_column(Text)  # hotfix/model-fields

    # ── Pipeline tracking ─────────────────────────────────────────────────────
    stage_reached: Mapped[str] = mapped_column(String(30), nullable=False)
    final_decision: Mapped[str] = mapped_column(String(30), nullable=False)

    # ── Triage ────────────────────────────────────────────────────────────────
    triage_passed: Mapped[bool | None] = mapped_column(Boolean)
    triage_reason: Mapped[str | None] = mapped_column(Text)         # real name (not triage_reasoning)

    # ── Deep analysis ─────────────────────────────────────────────────────────
    incident_type: Mapped[str | None] = mapped_column(String(50))   # real name (not classified_type)
    severity_score: Mapped[int | None] = mapped_column(Integer)      # real name (not classified_severity)
    affects_operations: Mapped[bool | None] = mapped_column(Boolean)
    ai_reasoning: Mapped[str | None] = mapped_column(Text)           # real name (not classified_reasoning)

    # ── Geolocation ───────────────────────────────────────────────────────────
    geo_lat: Mapped[float | None] = mapped_column(Float)
    geo_lon: Mapped[float | None] = mapped_column(Float)
    geo_address: Mapped[str | None] = mapped_column(Text)
    nearest_costco: Mapped[str | None] = mapped_column(String(100))      # real (not geo_closest_costco)
    nearest_costco_dist_m: Mapped[float | None] = mapped_column(Float)   # real (not geo_distance_meters)
    within_radius: Mapped[bool | None] = mapped_column(Boolean)          # hotfix/model-fields

    # ── Dedup ─────────────────────────────────────────────────────────────────
    is_duplicate: Mapped[bool | None] = mapped_column(Boolean)           # hotfix/model-fields

    # ── Tokens & latency (hotfix/model-fields) ────────────────────────────────
    total_tokens_input: Mapped[int | None] = mapped_column(Integer)
    total_tokens_output: Mapped[int | None] = mapped_column(Integer)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer)

    # ── Notification (hotfix/model-fields) ───────────────────────────────────
    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Error ─────────────────────────────────────────────────────────────────
    error_stage: Mapped[str | None] = mapped_column(String(100))     # hotfix/model-fields
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HumanFeedback(Base):
    """Mirrors src/models/human_feedback.py — no was_correct (not in real model)."""

    __tablename__ = "human_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_log_id: Mapped[int] = mapped_column(
        ForeignKey("decision_log.id", ondelete="CASCADE"), nullable=False, index=True
    )
    should_have_been: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
