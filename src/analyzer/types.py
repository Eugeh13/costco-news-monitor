"""
Local Pydantic v2 types for the AI analysis layer.

Defined here — not imported from app/domain — so this module is independent
until Phase 2 connects it to persistence.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    ACCIDENT = "accident"
    FIRE = "fire"
    SHOOTING = "shooting"
    ROADBLOCK = "roadblock"
    FLOOD = "flood"
    OTHER = "other"


class IncidentInput(BaseModel):
    title: str
    content: str
    source: str
    published_at: Optional[datetime] = None
    url: Optional[str] = None


class IncidentClassification(BaseModel):
    incident_type: IncidentType
    severity: int = Field(ge=1, le=10)
    affects_operations: bool
    reasoning: str
    recommended_action: str


class GeoLocation(BaseModel):
    lat: float
    lon: float
    address: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
