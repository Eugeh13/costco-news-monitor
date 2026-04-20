from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func  # noqa: F401
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.human_feedback import HumanFeedback


class StageReached(str, enum.Enum):
    scraped = "scraped"
    triage = "triage"
    deep_analysis = "deep_analysis"
    geolocation = "geolocation"
    dedup = "dedup"
    notification = "notification"
    error = "error"


class FinalDecision(str, enum.Enum):
    irrelevant = "irrelevant"        # triage filtered it out
    duplicate = "duplicate"          # dedup rejected it
    out_of_radius = "out_of_radius"  # no Costco within 3 km
    no_geo = "no_geo"                # could not geolocate
    alerted = "alerted"              # alert sent (or dry-run)
    error = "error"                  # unhandled exception
    pending = "pending"              # still in-flight


class DecisionLog(Base, TimestampMixin):
    __tablename__ = "decision_log"
    __table_args__ = (
        UniqueConstraint("run_id", "article_url", name="uq_decision_log_run_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # ── Run identity ──────────────────────────────────────────────────────────
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # ── Article metadata ──────────────────────────────────────────────────────
    article_url: Mapped[str] = mapped_column(Text, nullable=False)
    article_title: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    article_content_snippet: Mapped[str | None] = mapped_column(Text)

    # ── Pipeline tracking ─────────────────────────────────────────────────────
    stage_reached: Mapped[str] = mapped_column(
        String(30), nullable=False, default=StageReached.scraped.value
    )
    final_decision: Mapped[str] = mapped_column(
        String(30), nullable=False, default=FinalDecision.pending.value
    )

    # ── Triage ────────────────────────────────────────────────────────────────
    triage_passed: Mapped[bool | None] = mapped_column(Boolean)
    triage_reason: Mapped[str | None] = mapped_column(Text)

    # ── Deep analysis ─────────────────────────────────────────────────────────
    incident_type: Mapped[str | None] = mapped_column(String(50))
    severity_score: Mapped[int | None] = mapped_column(Integer)
    affects_operations: Mapped[bool | None] = mapped_column(Boolean)
    ai_reasoning: Mapped[str | None] = mapped_column(Text)

    # ── Geolocation ───────────────────────────────────────────────────────────
    geo_lat: Mapped[float | None] = mapped_column(Float)
    geo_lon: Mapped[float | None] = mapped_column(Float)
    geo_address: Mapped[str | None] = mapped_column(Text)
    nearest_costco: Mapped[str | None] = mapped_column(String(100))
    nearest_costco_dist_m: Mapped[float | None] = mapped_column(Float)
    within_radius: Mapped[bool | None] = mapped_column(Boolean)

    # ── Dedup ─────────────────────────────────────────────────────────────────
    is_duplicate: Mapped[bool | None] = mapped_column(Boolean)

    # ── Notification ──────────────────────────────────────────────────────────
    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Performance / cost tracking ───────────────────────────────────────────
    total_tokens_input: Mapped[int | None] = mapped_column(Integer)
    total_tokens_output: Mapped[int | None] = mapped_column(Integer)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer)

    # ── Error ─────────────────────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text)
    error_stage: Mapped[str | None] = mapped_column(String(100))

    # ── Relationships ─────────────────────────────────────────────────────────
    human_feedbacks: Mapped[list[HumanFeedback]] = relationship(
        "HumanFeedback",
        back_populates="decision_log",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
