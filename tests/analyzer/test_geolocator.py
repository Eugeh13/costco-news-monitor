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


# ── extract_locations (mocked Anthropic) ──────────────────────────────────────

def _make_anthropic_client(locations: list[str]) -> MagicMock:
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(locations)

    resp = MagicMock()
    resp.content = [text_block]
    resp.usage = MagicMock(input_tokens=200, output_tokens=30)

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


async def test_extract_locations_returns_list():
    mock_client = _make_anthropic_client(["Av. Constitución", "San Pedro Garza García"])
    result = await extract_locations("Accidente en Av. Constitución, San Pedro", client=mock_client)
    assert result == ["Av. Constitución", "San Pedro Garza García"]


async def test_extract_locations_empty():
    mock_client = _make_anthropic_client([])
    result = await extract_locations("El partido fue emocionante", client=mock_client)
    assert result == []


async def test_extract_locations_invalid_json_returns_empty():
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I cannot identify locations."

    resp = MagicMock()
    resp.content = [text_block]
    resp.usage = MagicMock(input_tokens=50, output_tokens=10)

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=resp)

    result = await extract_locations("some text", client=mock_client)
    assert result == []
