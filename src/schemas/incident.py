from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.incident import IncidentStatus, IncidentType, Severity


class IncidentBase(BaseModel):
    title: str
    description: str | None = None
    url: str | None = None
    incident_type: IncidentType
    severity: Severity
    severity_score: int | None = Field(default=None, ge=1, le=10)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    location_text: str | None = None


class IncidentCreate(IncidentBase):
    source_id: int | None = None
    content_hash: str | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    incident_type: IncidentType | None = None
    severity: Severity | None = None
    severity_score: int | None = Field(default=None, ge=1, le=10)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    location_text: str | None = None
    status: IncidentStatus | None = None


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int | None
    content_hash: str | None
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
