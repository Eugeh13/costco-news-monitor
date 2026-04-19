from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.alert import Alert
    from src.models.analysis_result import AnalysisResult
    from src.models.source import Source


class IncidentStatus(str, enum.Enum):
    pending_analysis = "pending_analysis"
    analyzed = "analyzed"
    alerted = "alerted"
    dismissed = "dismissed"


class IncidentType(str, enum.Enum):
    accidente_vial = "accidente_vial"
    incendio = "incendio"
    seguridad = "seguridad"
    bloqueo = "bloqueo"
    desastre_natural = "desastre_natural"
    otro = "otro"


class Severity(str, enum.Enum):
    menor = "menor"      # 1-3
    moderada = "moderada"  # 4-6
    grave = "grave"      # 7-8
    critica = "critica"  # 9-10


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    incident_type: Mapped[IncidentType] = mapped_column(
        Enum(IncidentType, name="incidenttype"), nullable=False
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False
    )
    severity_score: Mapped[int | None] = mapped_column(Integer)  # 1-10 raw LLM score

    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    location_text: Mapped[str | None] = mapped_column(Text)

    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incidentstatus"),
        nullable=False,
        default=IncidentStatus.pending_analysis,
        index=True,
    )

    source: Mapped[Source | None] = relationship("Source", back_populates="incidents")
    analysis_result: Mapped[AnalysisResult | None] = relationship(
        "AnalysisResult", back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[list[Alert]] = relationship(
        "Alert", back_populates="incident", cascade="all, delete-orphan"
    )
