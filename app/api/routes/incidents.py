"""
Incidents route — CRUD for incidents (alerts stored in DB).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.api.schemas import IncidentListResponse, IncidentResponse

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    costco: Optional[str] = Query(default=None, description="Filter by Costco name"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
):
    """List recent incidents with optional filters."""
    from app.api.main import get_repository

    repo = get_repository()
    if not repo:
        return IncidentListResponse(total=0, items=[])

    rows = repo.get_incidents(hours=hours, category=category, costco=costco, limit=limit)

    items = []
    for row in rows:
        items.append(IncidentResponse(
            id=row.get("id", 0),
            titulo=row.get("titulo", ""),
            descripcion=row.get("descripcion"),
            url=row.get("url"),
            fuente=row.get("fuente", ""),
            categoria=row.get("categoria", "otro"),
            severidad=row.get("severidad", 0),
            ubicacion_texto=row.get("ubicacion_texto"),
            latitud=row.get("latitud"),
            longitud=row.get("longitud"),
            costco_nombre=row.get("costco_nombre"),
            costco_distancia_km=row.get("costco_distancia_km"),
            victimas=row.get("victimas", 0),
            impacto_trafico=row.get("impacto_trafico"),
            servicios_emergencia=row.get("servicios_emergencia", False),
            fecha_deteccion=row.get("fecha_deteccion"),
            alerta_enviada=row.get("alerta_enviada", False),
        ))

    return IncidentListResponse(total=len(items), items=items)
