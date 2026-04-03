"""
Geolocation service — geocoding, proximity checks, and road matching.

Combines functionality from:
- geolocation.py (geocoding + distance)
- main_ai.py _check_key_roads() (vialidad matching)

Single responsibility: determine if a news event is near a Costco.
"""

from __future__ import annotations

from typing import Optional

from geopy.distance import geodesic
from geopy.geocoders import Nominatim

from app.domain.models import Coordinates, CostcoLocation, ProximityResult
from app.domain.ports import GeocodingService


# Generic coordinates for fallback
ZONE_COORDS: dict[str, tuple[float, float]] = {
    "monterrey": (25.6866, -100.3161),
    "centro": (25.6692, -100.3099),
    "san pedro": (25.6520, -100.4092),
    "san pedro garza garcía": (25.6520, -100.4092),
    "garza garcía": (25.6520, -100.4092),
    "guadalupe": (25.6767, -100.2561),
    "san nicolás": (25.7420, -100.2990),
    "escobedo": (25.7959, -100.3185),
    "apodaca": (25.7803, -100.1867),
    "santa catarina": (25.6747, -100.4597),
    "garcía": (25.8075, -100.5892),
    "cumbres": (25.7295, -100.3928),
    "valle oriente": (25.6397, -100.3176),
    "carretera nacional": (25.5781, -100.2512),
}


class NominatimGeocoder(GeocodingService):
    """Geocodes location text using OpenStreetMap's Nominatim."""

    def __init__(self) -> None:
        self._geocoder = Nominatim(user_agent="costco_news_monitor_v2")

    def geocode(self, location_text: str) -> Optional[tuple[float, float]]:
        """
        Geocode a location string. Priority:
        1. Precise Nominatim geocoding
        2. Fallback to generic zone coordinates
        """
        text_lower = location_text.lower().strip()

        # Try precise geocoding first
        for suffix in [", Monterrey, Nuevo León, México", ""]:
            try:
                result = self._geocoder.geocode(
                    location_text + suffix, timeout=10
                )
                if result:
                    print(f"  ✓ Geocodificación precisa: ({result.latitude:.6f}, {result.longitude:.6f})")
                    return (result.latitude, result.longitude)
            except Exception:
                continue

        # Fallback to generic zone
        for zone, coords in ZONE_COORDS.items():
            if zone in text_lower:
                print(f"  ⚠️ Usando coordenadas aproximadas para '{zone}'")
                return coords

        return None


class GeoService:
    """
    High-level geolocation service for the monitoring pipeline.

    Combines geocoding, proximity checking, and road name matching
    into a single cohesive service.
    """

    def __init__(
        self,
        geocoder: GeocodingService,
        locations: list[CostcoLocation],
        radius_km: float = 5.0,
    ) -> None:
        self._geocoder = geocoder
        self._locations = locations
        self._radius_km = radius_km

    def check_proximity(
        self, location_text: str, full_text: str
    ) -> ProximityResult:
        """
        Full proximity check combining geocoding and road matching.

        Args:
            location_text: The specific location extracted by AI analysis.
            full_text: Title + content for road keyword scanning.

        Returns:
            ProximityResult with all details.
        """
        # Strategy 1: Geocode and check radius
        coords = self._geocoder.geocode(location_text)

        if coords:
            result = self._check_radius(coords)
            if result.is_within_radius:
                result.event_coords = Coordinates(lat=coords[0], lon=coords[1])
                result.matched_via = "geocoding"
                return result

        # Strategy 2: Check road keywords
        road_result = self._check_roads(full_text, coords)
        if road_result.is_within_radius:
            return road_result

        # Not within radius
        if coords:
            result = self._find_nearest(coords)
            result.event_coords = Coordinates(lat=coords[0], lon=coords[1])
            return result

        return ProximityResult()

    def check_roads_only(self, full_text: str) -> ProximityResult:
        """Check only road keywords, no geocoding. Used when AI extracts no location."""
        return self._check_roads(full_text, coords=None)

    # ── Private ──────────────────────────────────────────────

    def _check_radius(self, coords: tuple[float, float]) -> ProximityResult:
        """Check if coords are within radius of any Costco."""
        for loc in self._locations:
            costco_coords = loc.coords.as_tuple()
            dist = geodesic(coords, costco_coords).kilometers

            if dist <= self._radius_km:
                return ProximityResult(
                    is_within_radius=True,
                    costco_nombre=loc.nombre,
                    costco_direccion=loc.direccion,
                    distancia_km=round(dist, 2),
                    event_coords=Coordinates(lat=coords[0], lon=coords[1]),
                )

        return self._find_nearest(coords)

    def _find_nearest(self, coords: tuple[float, float]) -> ProximityResult:
        """Find the nearest Costco (even if outside radius)."""
        nearest = None
        min_dist = float("inf")

        for loc in self._locations:
            dist = geodesic(coords, loc.coords.as_tuple()).kilometers
            if dist < min_dist:
                min_dist = dist
                nearest = loc

        if nearest:
            return ProximityResult(
                is_within_radius=False,
                costco_nombre=nearest.nombre,
                costco_direccion=nearest.direccion,
                distancia_km=round(min_dist, 2),
            )

        return ProximityResult()

    def _check_roads(
        self, text: str, coords: Optional[tuple[float, float]]
    ) -> ProximityResult:
        """Check if text mentions key roads near any Costco."""
        text_lower = text.lower()

        for loc in self._locations:
            for road in loc.vialidades_clave:
                if road in text_lower:
                    print(f"  ✓ Vialidad clave: '{road}' ({loc.nombre})")

                    if coords:
                        dist = geodesic(coords, loc.coords.as_tuple()).kilometers
                    else:
                        dist = 0.5  # Assume close if road is mentioned

                    return ProximityResult(
                        is_within_radius=True,
                        costco_nombre=loc.nombre,
                        costco_direccion=loc.direccion,
                        distancia_km=round(dist, 2),
                        event_coords=(
                            Coordinates(lat=coords[0], lon=coords[1])
                            if coords
                            else loc.coords
                        ),
                        matched_via="vialidad",
                    )

        return ProximityResult()
