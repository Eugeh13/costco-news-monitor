"""
Tests for the Google Geocoding API implementation in geocode().

All tests mock httpx — no real API calls are made.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.analyzer.geolocator import geocode


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_google_response(
    *,
    status: str = "OK",
    lat: float = 25.639695,
    lng: float = -100.317631,
    formatted_address: str = "Av Lázaro Cárdenas 800, Zona Valle Oriente, 66269 San Pedro Garza García, N.L.",
    location_type: str = "ROOFTOP",
    partial_match: bool = False,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.raise_for_status = MagicMock()
    payload: dict = {"status": status, "results": []}
    if status == "OK":
        payload["results"] = [
            {
                "formatted_address": formatted_address,
                "geometry": {
                    "location": {"lat": lat, "lng": lng},
                    "location_type": location_type,
                },
                "partial_match": partial_match,
            }
        ]
    resp.json = MagicMock(return_value=payload)
    return resp


def _mock_http(response: MagicMock) -> AsyncMock:
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=response)
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_geocode_returns_precise_result_for_known_address():
    """ROOFTOP result with no partial_match should return a GeoLocation."""
    mock_http = _mock_http(_make_google_response(location_type="ROOFTOP"))
    result = await geocode("Av. Lázaro Cárdenas 800, Valle Oriente", http_client=mock_http, api_key="test-key")

    assert result is not None
    assert abs(result.lat - 25.639695) < 0.001
    assert abs(result.lon - (-100.317631)) < 0.001
    assert result.confidence == 1.0  # ROOFTOP → 1.0
    assert "Valle Oriente" in result.address


async def test_geocode_returns_none_for_zero_results():
    """ZERO_RESULTS status should return None without raising."""
    mock_http = _mock_http(_make_google_response(status="ZERO_RESULTS"))
    result = await geocode("Calle Inventada 999", http_client=mock_http, api_key="test-key")

    assert result is None


async def test_geocode_returns_none_for_partial_match_approximate():
    """APPROXIMATE location_type + partial_match=True must be rejected."""
    mock_http = _mock_http(
        _make_google_response(location_type="APPROXIMATE", partial_match=True)
    )
    result = await geocode("colonia vaga sin datos", http_client=mock_http, api_key="test-key")

    assert result is None


async def test_geocode_handles_timeout():
    """TransportError (e.g. timeout) triggers one retry; if both fail, returns None."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.TransportError("timeout"))

    result = await geocode("Calle Real", http_client=client, api_key="test-key")

    assert result is None
    assert client.get.call_count == 2  # initial attempt + one retry


async def test_geocode_includes_region_and_bounds_for_mty_bias():
    """The request to Google must include region=mx and Monterrey bounds."""
    mock_http = _mock_http(_make_google_response())
    await geocode("Av. Garza Sada 300", http_client=mock_http, api_key="test-key")

    call_kwargs = mock_http.get.call_args
    params = call_kwargs.kwargs.get("params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
    assert params.get("region") == "mx"
    assert "25.5,-100.5" in params.get("bounds", "")
    assert params.get("language") == "es"
    assert "Monterrey" in params.get("address", "")
