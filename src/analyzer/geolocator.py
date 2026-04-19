"""
Geolocation helpers for the Costco Monterrey monitoring system.

extract_locations() — LLM extracts place names from incident text
geocode()           — Nominatim (OpenStreetMap) via httpx, 1 req/s rate-limited
distance_to_costcos() — haversine distances in metres to all 3 stores
is_within_radius()  — True if any store is within the given radius
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from typing import Optional

import anthropic
import httpx
import structlog

from src.analyzer.types import GeoLocation

logger = structlog.get_logger(__name__)

# ── Costco store coordinates (from project README / CLAUDE.md) ───────────────
COSTCO_LOCATIONS: dict[str, tuple[float, float]] = {
    "Costco Carretera Nacional": (25.6026, -100.2640),
    "Costco Cumbres":            (25.7353, -100.4022),
    "Costco Valle Oriente":      (25.6457, -100.3072),
}

_NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_UA = "CostcoMonterreyMonitor/2.0 (ops@costco-mty.example)"

# Module-level rate-limiter state (shared across all calls)
_last_geocode_t: float = 0.0
_geocode_lock: asyncio.Lock = asyncio.Lock()


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def distance_to_costcos(lat: float, lon: float) -> dict[str, float]:
    """Haversine distances in metres from (lat, lon) to each Costco store."""
    return {
        name: _haversine_m(lat, lon, clat, clon)
        for name, (clat, clon) in COSTCO_LOCATIONS.items()
    }


def is_within_radius(lat: float, lon: float, radius_m: float = 3_000.0) -> bool:
    """True if (lat, lon) is within radius_m of at least one Costco store."""
    return any(d <= radius_m for d in distance_to_costcos(lat, lon).values())


# ── Async functions ───────────────────────────────────────────────────────────

async def extract_locations(
    text: str,
    *,
    client: Optional[anthropic.AsyncAnthropic] = None,
) -> list[str]:
    """
    Ask Claude haiku to extract geographic place mentions from incident text.
    Returns a list of address strings (may be empty).
    """
    _client = client or anthropic.AsyncAnthropic()
    try:
        response = await _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=(
                "Extract all geographic location mentions from the text "
                "(streets, neighbourhoods, districts, cities, landmarks). "
                'Return ONLY a valid JSON array of strings, e.g. ["Av. Lázaro Cárdenas", "San Pedro Garza García"]. '
                "If no locations are found return []."
            ),
            messages=[{"role": "user", "content": f"Text:\n{text[:1800]}"}],
        )
        raw = next(
            (b.text for b in response.content if getattr(b, "type", None) == "text"),
            "[]",
        )
        logger.debug(
            "extract_locations in_tokens=%d out_tokens=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        result = json.loads(raw.strip())
        if isinstance(result, list):
            return [str(x) for x in result if x]
    except json.JSONDecodeError as exc:
        logger.warning("extract_locations: JSON parse error: %s — raw=%r", exc, raw[:200])
    except anthropic.APIError as exc:
        logger.error("extract_locations: Anthropic API error: %s", exc)
    return []


async def geocode(
    address: str,
    *,
    http_client: Optional[httpx.AsyncClient] = None,
) -> Optional[GeoLocation]:
    """
    Geocode an address string via Nominatim.

    Enforces a 1 req/s rate limit using a module-level asyncio.Lock.
    Returns None if Nominatim returns no results or on HTTP error.
    """
    global _last_geocode_t

    async with _geocode_lock:
        now = time.monotonic()
        gap = 1.0 - (now - _last_geocode_t)
        if gap > 0:
            await asyncio.sleep(gap)
        _last_geocode_t = time.monotonic()

    params = {
        "q": f"{address}, Monterrey, Nuevo León, México",
        "format": "json",
        "limit": "1",
        "countrycodes": "mx",
    }
    headers = {"User-Agent": _NOMINATIM_UA}

    owns_client = http_client is None
    _http = http_client or httpx.AsyncClient(timeout=10.0)
    try:
        resp = await _http.get(_NOMINATIM_BASE, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            logger.debug("geocode: no Nominatim results for %r", address)
            return None
        hit = data[0]
        return GeoLocation(
            lat=float(hit["lat"]),
            lon=float(hit["lon"]),
            address=hit.get("display_name", address),
            confidence=min(1.0, float(hit.get("importance", 0.5))),
        )
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("geocode error for %r: %s", address, exc)
        return None
    finally:
        if owns_client:
            await _http.aclose()
