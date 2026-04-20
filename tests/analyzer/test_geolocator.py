"""Tests for src/analyzer/geolocator.py — mocks httpx (Nominatim) and Anthropic."""
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.analyzer.geolocator import (
    COSTCO_LOCATIONS,
    distance_to_costcos,
    extract_locations,
    geocode,
    is_within_radius,
)
from src.analyzer.types import GeolocationResult


# ── distance_to_costcos / is_within_radius ────────────────────────────────────

def test_distance_to_costcos_keys():
    dists = distance_to_costcos(25.6455, -100.3255)
    assert set(dists.keys()) == set(COSTCO_LOCATIONS.keys())


def test_distance_zero_at_valle_oriente():
    lat, lon = COSTCO_LOCATIONS["Costco Valle Oriente"]
    dists = distance_to_costcos(lat, lon)
    assert dists["Costco Valle Oriente"] < 1  # < 1 metre


def test_distance_known_pair():
    # Carretera Nacional (25.6026,-100.2640) → Valle Oriente (25.6457,-100.3072) ≈ 6.5 km
    lat1, lon1 = COSTCO_LOCATIONS["Costco Carretera Nacional"]
    lat2, lon2 = COSTCO_LOCATIONS["Costco Valle Oriente"]
    from src.analyzer.geolocator import _haversine_m
    d = _haversine_m(lat1, lon1, lat2, lon2)
    assert 5_000 < d < 9_000  # sanity range in metres


def test_is_within_radius_true():
    # Valle Oriente coords → distance 0 → within any radius
    lat, lon = COSTCO_LOCATIONS["Costco Valle Oriente"]
    assert is_within_radius(lat, lon, radius_m=1.0) is True


def test_is_within_radius_false():
    # Coordinates of Mexico City — far from Monterrey
    assert is_within_radius(19.4326, -99.1332, radius_m=3_000) is False


def test_distance_all_positive():
    dists = distance_to_costcos(25.0, -100.0)
    assert all(v > 0 for v in dists.values())


# ── geocode (mocked Nominatim) ────────────────────────────────────────────────

def _make_nominatim_response(lat="25.6455", lon="-100.3255", name="Av Lázaro Cárdenas, San Pedro") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=[{"lat": lat, "lon": lon, "display_name": name, "importance": "0.7"}])
    return resp


async def test_geocode_success():
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(return_value=_make_nominatim_response())

    result = await geocode("Av Lázaro Cárdenas", http_client=mock_http)
    assert result is not None
    assert abs(result.lat - 25.6455) < 0.001
    assert result.confidence == pytest.approx(0.7, abs=0.01)


async def test_geocode_empty_results():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=[])

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(return_value=resp)

    result = await geocode("Calle que no existe", http_client=mock_http)
    assert result is None


async def test_geocode_http_error():
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

    result = await geocode("anything", http_client=mock_http)
    assert result is None


# ── extract_locations (mocked Anthropic — tool_use format) ────────────────────

def _make_tool_use_client(
    exact_address: str | None = None,
    neighborhood: str | None = None,
    city: str = "Monterrey",
    confidence: float = 0.8,
    latitude: float | None = None,
    longitude: float | None = None,
) -> MagicMock:
    """Build a mock Anthropic client that returns a tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "extract_incident_location"
    tool_block.input = {
        "exact_address": exact_address,
        "neighborhood": neighborhood,
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "confidence": confidence,
        "reasoning": "Mock reasoning for test.",
    }

    resp = MagicMock()
    resp.content = [tool_block]
    resp.usage = MagicMock(
        input_tokens=400,
        output_tokens=60,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


async def test_extract_locations_returns_list():
    mock_client = _make_tool_use_client(
        exact_address="Av. Constitución",
        neighborhood="Centro",
        city="Monterrey",
    )
    result = await extract_locations("Accidente en Av. Constitución, centro", client=mock_client)
    assert "Av. Constitución" in result
    assert len(result) >= 1


async def test_extract_locations_neighborhood_only():
    mock_client = _make_tool_use_client(neighborhood="San Pedro Garza García", city="San Pedro")
    result = await extract_locations("Incendio en San Pedro", client=mock_client)
    assert any("San Pedro" in r for r in result)


async def test_extract_locations_low_confidence_returns_empty():
    """Confidence < 0.3 → geolocate_incident returns None → extract_locations returns []."""
    mock_client = _make_tool_use_client(city="Monterrey", confidence=0.1)
    result = await extract_locations("Reportan accidente en algún lugar", client=mock_client)
    assert result == []
