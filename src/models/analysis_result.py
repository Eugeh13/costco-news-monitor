from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.incident import Incident


class AnalysisResult(Base, TimestampMixin):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)

    raw_response: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text)

    # ── Geolocation fields (T1.8) ─────────────────────────────────────────────
    approximate_location: Mapped[str | None] = mapped_column(String(200))
    exact_location_lat: Mapped[float | None] = mapped_column(Float)
    exact_location_lng: Mapped[float | None] = mapped_column(Float)
    geolocation_confidence: Mapped[float | None] = mapped_column(Float)

    incident: Mapped[Incident] = relationship("Incident", back_populates="analysis_result")
