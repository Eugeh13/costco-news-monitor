"""
API response schemas — Pydantic models for API responses.

Separate from domain models because API schemas can evolve
independently (e.g., adding pagination, HATEOAS links).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    """Single incident in the API response."""
    id: int
    titulo: str
    descripcion: Optional[str] = None
    url: Optional[str] = None
    fuente: str
    categoria: str
    severidad: int
    ubicacion_texto: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    costco_nombre: Optional[str] = None
    costco_distancia_km: Optional[float] = None
    victimas: int = 0
    impacto_trafico: Optional[str] = None
    servicios_emergencia: bool = False
    fecha_deteccion: Optional[datetime] = None
    alerta_enviada: bool = False


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""
    total: int
    items: list[IncidentResponse]


class LocationResponse(BaseModel):
    """Costco location for the map."""
    nombre: str
    lat: float
    lon: float
    direccion: str
    activo: bool


class StatsResponse(BaseModel):
    """Dashboard statistics."""
    hours: int
    total_incidents: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_costco: dict[str, int]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    database: str
    ai_provider: str
