"""
Domain models — Pydantic v2 models shared across the entire application.

These models define the core data structures. No business logic, no I/O.
Every layer depends on these models; these models depend on nothing.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class IncidentCategory(str, Enum):
    """Categories of high-impact events near Costco locations."""
    ACCIDENTE_VIAL = "accidente_vial"
    INCENDIO = "incendio"
    SEGURIDAD = "seguridad"
    BLOQUEO = "bloqueo"
    DESASTRE_NATURAL = "desastre_natural"
    OTRO = "otro"


class TrafficImpact(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class TriageDecision(str, Enum):
    CANDIDATE = "candidata"
    DISCARDED = "descartada"
    UNKNOWN = "desconocido"


# ============================================================
# News Domain
# ============================================================

class NewsItem(BaseModel):
    """A single news article from any source."""
    titulo: str
    contenido: str = ""
    url: Optional[str] = None
    fuente: str = "desconocido"
    fecha_pub: Optional[datetime] = None
    source_type: str = "unknown"  # google_rss, gnews, rss_directo, crawl4ai

    # Enrichment (set by pipeline, not by source)
    keyword_hint: Optional[str] = None

    def to_dict(self) -> dict:
        """Backward-compatible dict export for AI prompts."""
        return {
            "titulo": self.titulo,
            "contenido": self.contenido[:500],
            "url": self.url or "",
            "fuente": self.fuente,
            "fecha_pub": self.fecha_pub.isoformat() if self.fecha_pub else None,
        }


class TriageResult(BaseModel):
    """Result of batch triage for a single news item."""
    index: int = 0
    decision: TriageDecision = TriageDecision.UNKNOWN
    estimated_category: str = "desconocido"
    estimated_severity: int = Field(default=5, ge=1, le=10)
    location_hint: str = "no_especifica"
    reason: str = ""

    @property
    def is_candidate(self) -> bool:
        return self.decision in (TriageDecision.CANDIDATE, TriageDecision.UNKNOWN)


# ============================================================
# Analysis Domain
# ============================================================

class LocationInfo(BaseModel):
    """Location extracted from AI analysis."""
    extracted: str = ""
    normalized: str = ""
    is_specific: bool = False


class AnalysisResult(BaseModel):
    """Result of deep AI analysis on a candidate article."""
    is_relevant: bool = False
    category: IncidentCategory = IncidentCategory.OTRO
    severity: int = Field(default=5, ge=1, le=10)
    summary: str = ""
    exclusion_reason: str = ""
    location: LocationInfo = Field(default_factory=LocationInfo)
    victims: int = 0
    traffic_impact: TrafficImpact = TrafficImpact.UNKNOWN
    emergency_services: bool = False


# ============================================================
# Geo Domain
# ============================================================

class Coordinates(BaseModel):
    """A geographic point."""
    lat: float
    lon: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.lat, self.lon)


class CostcoLocation(BaseModel):
    """A Costco store with its monitoring zone."""
    nombre: str
    coords: Coordinates
    direccion: str
    activo: bool = True
    vialidades_clave: list[str] = Field(default_factory=list)


class ProximityResult(BaseModel):
    """Result of proximity check against Costco locations."""
    is_within_radius: bool = False
    costco_nombre: str = ""
    costco_direccion: str = ""
    distancia_km: float = 0.0
    event_coords: Optional[Coordinates] = None
    matched_via: str = ""  # "geocoding", "vialidad", "keyword"


# ============================================================
# Alert / Incident Domain
# ============================================================

class Alert(BaseModel):
    """A fully resolved alert ready for notification and storage."""
    news: NewsItem
    analysis: AnalysisResult
    proximity: ProximityResult
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def severity_emoji(self) -> str:
        s = self.analysis.severity
        if s >= 9:
            return "🚨🚨"
        if s >= 7:
            return "🚨"
        if s >= 5:
            return "⚠️"
        return "ℹ️"

    @property
    def category_label(self) -> str:
        labels = {
            IncidentCategory.ACCIDENTE_VIAL: "Accidente Vial",
            IncidentCategory.INCENDIO: "Incendio",
            IncidentCategory.SEGURIDAD: "Situación de Seguridad",
            IncidentCategory.BLOQUEO: "Bloqueo de Vialidad",
            IncidentCategory.DESASTRE_NATURAL: "Desastre Natural",
            IncidentCategory.OTRO: "Otro",
        }
        return labels.get(self.analysis.category, "Otro")
