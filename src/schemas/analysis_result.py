from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisResultBase(BaseModel):
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw_response: str | None = None
    summary: str | None = None
    reasoning: str | None = None
    approximate_location: str | None = None
    exact_location_lat: float | None = None
    exact_location_lng: float | None = None
    geolocation_confidence: float | None = None


class AnalysisResultCreate(AnalysisResultBase):
    incident_id: int


class AnalysisResultUpdate(BaseModel):
    summary: str | None = None
    reasoning: str | None = None
    raw_response: str | None = None


class AnalysisResultRead(AnalysisResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    created_at: datetime
    updated_at: datetime
