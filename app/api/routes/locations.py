"""
Locations route — Costco store locations for the dashboard map.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import LocationResponse
from app.config.locations import get_all_locations

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationResponse])
async def list_locations():
    """Return all Costco locations (active and inactive)."""
    return [
        LocationResponse(
            nombre=loc.nombre,
            lat=loc.coords.lat,
            lon=loc.coords.lon,
            direccion=loc.direccion,
            activo=loc.activo,
        )
        for loc in get_all_locations()
    ]
