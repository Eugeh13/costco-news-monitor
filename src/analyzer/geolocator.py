"""
Geolocation helpers for the Costco Monterrey monitoring system.

geolocate_incident() — primary function: tool_use LLM extraction with prompt caching
extract_locations()  — backward-compat wrapper, returns list[str] for pipeline
geocode()            — Google Geocoding API via httpx, Monterrey-biased
distance_to_costcos() — haversine distances in metres to all 3 stores
is_within_radius()   — True if any store is within the given radius

Bug fix (T1.2): replaces brittle JSON mode (failed on ```json...``` fences) with
tool_use forcing a structured response block — eliminates json.loads entirely.
Prompt caching (T1.4): system prompt carries cache_control=ephemeral.
Geocoder (T2.x): replaced Nominatim with Google Geocoding API for higher precision
in Mexican addresses. Results with location_type=APPROXIMATE + partial_match are
rejected to avoid centroid-level misses.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import time
from typing import TYPE_CHECKING, Optional

import anthropic
import httpx
import structlog

from src.analyzer.types import GeoLocation, GeolocationResult

if TYPE_CHECKING:
    from src.core.token_counter import TokenAccumulator

logger = structlog.get_logger(__name__)

# ── Costco store coordinates (authoritative — from CLAUDE.md) ─────────────────
COSTCO_LOCATIONS: dict[str, tuple[float, float]] = {
    "Costco Carretera Nacional": (25.6026, -100.2640),
    "Costco Cumbres":            (25.7353, -100.4022),
    "Costco Valle Oriente":      (25.6457, -100.3072),
}

_GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
# Bounding box for Área Metropolitana de Monterrey — biases results toward ZMM
_MTY_BOUNDS = "25.5,-100.5|25.9,-100.1"

# ── Tool definition (T1.2) ────────────────────────────────────────────────────

_GEO_TOOL: dict = {
    "name": "extract_incident_location",
    "description": (
        "Extrae información de ubicación de un incidente en Monterrey o zona metropolitana"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "exact_address": {
                "type": ["string", "null"],
                "description": (
                    "Dirección exacta (calle, intersección, km de carretera) si el texto "
                    "la menciona literal. null si no hay."
                ),
            },
            "neighborhood": {
                "type": ["string", "null"],
                "description": (
                    "Colonia, zona o sector (ej: 'Cumbres', 'Valle Oriente', 'San Jerónimo', "
                    "'Centro'). null si no hay."
                ),
            },
            "city": {
                "type": "string",
                "description": (
                    "Ciudad o municipio (ej: 'Monterrey', 'San Pedro', 'Guadalupe', "
                    "'San Nicolás', 'Apodaca')"
                ),
            },
            "latitude": {
                "type": ["number", "null"],
                "description": (
                    "Latitud solo si se puede inferir con alta confianza. null en duda."
                ),
            },
            "longitude": {
                "type": ["number", "null"],
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "reasoning": {
                "type": "string",
                "description": "1-2 frases explicando cómo dedujiste la ubicación",
            },
        },
        "required": ["city", "confidence", "reasoning"],
    },
}

# ── System prompt (T1.4: ≥1024 tokens for prompt caching eligibility) ─────────

_SYSTEM_PROMPT_GEO = """\
Eres un sistema especializado en geolocalización de incidentes de seguridad y emergencias \
para la Zona Metropolitana de Monterrey (ZMM), Nuevo León, México. Tu única función es \
extraer con precisión la información de ubicación de textos de noticias o reportes de \
incidentes.

## Contexto geográfico

La ZMM incluye los siguientes municipios principales:
- **Monterrey** (municipio central): Centro histórico, Barrio Antiguo, Obispado, San Jerónimo, \
  Lomas de San Francisco, Contry, Del Valle, Cumbres (distintas etapas), San Bernabé, Mirador, \
  Linda Vista, Anáhuac, Mitras, Chepevera, Roma, Independencia, Nuevo Repueblo.
- **San Pedro Garza García**: Valle Oriente, Valle del Campestre, Del Valle, Calzada del Valle, \
  Las Cumbres, Los Nogales, Residencial San Agustín, Carrizalejo, Tec de Monterrey, \
  Santa Engracia, Jardines del Canadá.
- **Guadalupe**: Colinas de San Jerónimo, Azteca, Los Pinos, Del Maestro, Contry Sol, \
  Malvinas, Lomas de Chapultepec.
- **San Nicolás de los Garza**: Las Puentes, Bosques de Anáhuac, Mirasierra, Jardines, \
  Valle de Invierno.
- **Apodaca**: Hacienda los Morales, Villas de Apodaca, Cumbres Platinum, Cumbres Elite, \
  Aeropuerto Internacional Monterrey (General Mariano Escobedo).
- **Escobedo**: Sendero, Ciudad Apodaca, Villa Escobedo.
- **Santa Catarina**: Balcones de Santa Catarina, Portales, Las Torres.
- **Garza García** (coloquialmente): Frecuentemente se usa para referirse a San Pedro Garza García.

## Arterias y vías principales de referencia

- **Lázaro Cárdenas / Frida Kahlo**: Corredor principal de negocios E-O en San Pedro y MTY sur.
- **Gonzalitos / Churubusco**: Eje vial importante N-S en Monterrey.
- **Constitución**: Vía histórica E-O en el centro de Monterrey.
- **Garza Sada**: Corredor universitario hacia el Tecnológico.
- **Morones Prieto**: Vía rápida O-E paralela a Lázaro Cárdenas.
- **Carretera Nacional (México 40D / libre)**: Sale hacia el sur (Saltillo), pasa por \
  Bosques de Valle Alto, Valle Alto, antes de cruzar la sierra.
- **Carretera Monterrey-Laredo (México 85)**: Sale hacia el norte.
- **Periferico**: Anillo periférico de la ciudad.
- **Autopista MTY-SLP / MTY-Saltillo**: Accesos principales.

## Sucursales Costco monitoreadas (relevancia especial)

Las siguientes ubicaciones son de máxima prioridad para este sistema:

1. **Costco Carretera Nacional**
   - Dirección: Km 268+500, Carretera Nacional, Bosques de Valle Alto, Monterrey
   - Coordenadas: 25.6026° N, 100.2640° O
   - Referencias: cerca del cruce con Vía Tampico, zona Bosques de Valle Alto / Valle Alto

2. **Costco Valle Oriente**
   - Dirección: Av. Lázaro Cárdenas 800, Valle Oriente, San Pedro Garza García
   - Coordenadas: 25.6457° N, 100.3072° O
   - Referencias: frente a Galerías Valle Oriente, zona Centrito Valle

3. **Costco Cumbres**
   - Dirección: Alejandro de Rodas 6767, Cumbres, Monterrey
   - Coordenadas: 25.7353° N, 100.4022° O
   - Referencias: zona Cumbres 7° Sector / Cumbres Elite, cerca de Liverpool Cumbres

## Criterios de extracción

1. **Prioridad de especificidad**: Si el texto menciona una dirección exacta (calle + número \
   o intersección), captúrala en `exact_address`. Si solo menciona colonia o zona, usa \
   `neighborhood`. Siempre deduce la ciudad/municipio.

2. **Coordenadas (lat/lng)**: Proporciona latitud y longitud SOLO si puedes inferirlas con \
   alta confianza (conoces la ubicación exacta de la calle, km de carretera, o edificio). \
   Prefiere `null` + `neighborhood` sobre coordenadas inventadas. Es mejor un campo null \
   que una coordenada incorrecta.

3. **Confianza**: Asigna `confidence` según la especificidad:
   - 0.9-1.0: Dirección exacta con número o km claramente identificables
   - 0.7-0.89: Intersección o referencia de calle sin número, colonia bien definida
   - 0.5-0.69: Colonia o zona mencionada explícitamente pero sin calle
   - 0.3-0.49: Solo se menciona municipio o referencia vaga ("al norte de MTY")
   - 0.0-0.29: Información demasiado vaga para ubicar ("en la ciudad", "en MTY")

4. **Ciudad por defecto**: Si el texto no especifica municipio pero el contexto sugiere \
   zona metropolitana de Monterrey, usa "Monterrey" como ciudad por defecto.

5. **Razonamiento**: Explica brevemente cómo llegaste a la ubicación deducida. Sé específico \
   (menciona qué palabras del texto te llevaron a la conclusión).

Responde únicamente con la herramienta `extract_incident_location`. No agregues texto \
adicional fuera de la llamada a herramienta.
"""

# ── Pure math helpers ─────────────────────────────────────────────────────────

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


# ── Primary async functions ───────────────────────────────────────────────────

async def geolocate_incident(
    text: str,
    *,
    client: Optional[anthropic.AsyncAnthropic] = None,
    accumulator: Optional["TokenAccumulator"] = None,
) -> Optional[GeolocationResult]:
    """
    Extract structured location from incident text using Claude tool_use.

    Uses prompt caching on the system prompt (T1.4).
    Returns None if confidence < 0.3 (too vague to be actionable).
    """
    _client = client or anthropic.AsyncAnthropic()
    try:
        response = await _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT_GEO,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": f"Texto del incidente:\n{text[:2000]}"}],
            tools=[_GEO_TOOL],
            tool_choice={"type": "tool", "name": "extract_incident_location"},
        )

        if accumulator is not None:
            accumulator.add_response(response)

        tool_use_block = next(
            (b for b in response.content if getattr(b, "type", None) == "tool_use"),
            None,
        )
        if tool_use_block is None:
            logger.warning("geolocate_incident: no tool_use block in response")
            return None

        data: dict = tool_use_block.input  # already validated by Anthropic SDK
        confidence: float = float(data.get("confidence", 0.0))

        logger.debug(
            "geolocate_incident city=%r neighborhood=%r confidence=%.2f "
            "in_tokens=%d out_tokens=%d cache_creation=%d cache_read=%d",
            data.get("city"),
            data.get("neighborhood"),
            confidence,
            response.usage.input_tokens,
            response.usage.output_tokens,
            getattr(response.usage, "cache_creation_input_tokens", 0),
            getattr(response.usage, "cache_read_input_tokens", 0),
        )

        if confidence < 0.3:
            logger.info("geolocate_incident: low confidence %.2f — treating as no_result", confidence)
            return None

        return GeolocationResult(
            exact_address=data.get("exact_address"),
            neighborhood=data.get("neighborhood"),
            city=data.get("city", "Monterrey"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            confidence=confidence,
            reasoning=data.get("reasoning", ""),
        )

    except anthropic.APIError as exc:
        logger.error("geolocate_incident: Anthropic API error: %s", exc)
        return None


async def extract_locations(
    text: str,
    *,
    client: Optional[anthropic.AsyncAnthropic] = None,
) -> list[str]:
    """
    Backward-compatible wrapper: calls geolocate_incident and returns address strings.

    Used by run_pipeline.py to feed strings into geocode() for Google Geocoding lookup.
    """
    result = await geolocate_incident(text, client=client)
    if result is None:
        return []

    addresses: list[str] = []
    if result.exact_address:
        addresses.append(result.exact_address)
    if result.neighborhood:
        addr = f"{result.neighborhood}, {result.city}"
        if addr not in addresses:
            addresses.append(addr)
    if not addresses:
        addresses.append(result.city)
    return addresses


async def geocode(
    address: str,
    *,
    http_client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
) -> Optional[GeoLocation]:
    """
    Geocode an address string via Google Geocoding API.

    Biases results toward Área Metropolitana de Monterrey via the ``bounds``
    parameter. Rejects results flagged as APPROXIMATE + partial_match to avoid
    centroid-level misses that plagued the Nominatim implementation.

    Returns None on ZERO_RESULTS, non-OK status, or HTTP/parse error.
    One transparent retry on transient HTTP errors.
    """
    key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        logger.warning("geocode: GOOGLE_MAPS_API_KEY not set — skipping geocode")
        return None

    params = {
        "address": f"{address}, Monterrey, Nuevo León, México",
        "key": key,
        "region": "mx",
        "bounds": _MTY_BOUNDS,
        "language": "es",
    }

    owns_client = http_client is None
    _http = http_client or httpx.AsyncClient(timeout=10.0)

    async def _attempt() -> Optional[GeoLocation]:
        resp = await _http.get(_GOOGLE_GEOCODE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", "")
        if status == "ZERO_RESULTS":
            logger.info("geocoder.no_result", address=address, status=status)
            return None
        if status != "OK":
            logger.warning("geocoder.error", address=address, status=status)
            return None

        results = data.get("results", [])
        if not results:
            logger.info("geocoder.no_result", address=address, status="empty_results")
            return None

        hit = results[0]
        location_type = hit.get("geometry", {}).get("location_type", "")
        partial_match = hit.get("partial_match", False)

        # Reject low-precision results: centroid of a large area + partial text match
        if location_type == "APPROXIMATE" and partial_match:
            logger.info(
                "geocoder.no_result",
                address=address,
                reason="APPROXIMATE+partial_match",
                location_type=location_type,
            )
            return None

        loc = hit["geometry"]["location"]
        formatted = hit.get("formatted_address", address)
        logger.info("geocoder.success", address=address, formatted=formatted, location_type=location_type)
        return GeoLocation(
            lat=float(loc["lat"]),
            lon=float(loc["lng"]),
            address=formatted,
            confidence=_location_type_confidence(location_type),
        )

    try:
        return await _attempt()
    except httpx.TransportError as exc:
        logger.warning("geocoder.error", address=address, error=str(exc), retry=True)
        try:
            return await _attempt()
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc2:
            logger.warning("geocoder.error", address=address, error=str(exc2), retry=False)
            return None
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("geocoder.error", address=address, error=str(exc))
        return None
    finally:
        if owns_client:
            await _http.aclose()


def _location_type_confidence(location_type: str) -> float:
    """Map Google location_type to a confidence score in [0, 1]."""
    return {
        "ROOFTOP": 1.0,
        "RANGE_INTERPOLATED": 0.85,
        "GEOMETRIC_CENTER": 0.7,
        "APPROXIMATE": 0.5,
    }.get(location_type, 0.5)
