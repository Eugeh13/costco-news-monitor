"""
Tests for geolocate_incident() — tool_use based geolocation (T1.2 + T1.4).

All tests mock the Anthropic client to avoid real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.analyzer.geolocator import _GEO_TOOL, _SYSTEM_PROMPT_GEO, geolocate_incident
from src.analyzer.types import GeolocationResult


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _make_client(
    *,
    exact_address: str | None = None,
    neighborhood: str | None = None,
    city: str = "Monterrey",
    latitude: float | None = None,
    longitude: float | None = None,
    confidence: float = 0.8,
    reasoning: str = "Dirección mencionada explícitamente en el texto.",
) -> MagicMock:
    """Return a mock AsyncAnthropic client that produces a valid tool_use response."""
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
        "reasoning": reasoning,
    }

    resp = MagicMock()
    resp.content = [tool_block]
    resp.usage = MagicMock(
        input_tokens=450,
        output_tokens=70,
        cache_creation_input_tokens=450,
        cache_read_input_tokens=0,
    )

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extracts_exact_address() -> None:
    """Tool returns an exact_address when street intersection is in text."""
    mock_client = _make_client(
        exact_address="Av. Constitución y Zaragoza",
        neighborhood="Centro",
        city="Monterrey",
        confidence=0.9,
        reasoning="El texto menciona 'Av. Constitución y Zaragoza, centro de Monterrey'.",
    )

    result = await geolocate_incident(
        "Accidente en Av. Constitución y Zaragoza, centro de Monterrey",
        client=mock_client,
    )

    assert result is not None
    assert result.exact_address == "Av. Constitución y Zaragoza"
    assert result.city == "Monterrey"
    assert result.confidence >= 0.7


@pytest.mark.asyncio
async def test_extracts_neighborhood_only() -> None:
    """Tool returns neighborhood when only zone is mentioned, exact_address=None."""
    mock_client = _make_client(
        exact_address=None,
        neighborhood="Valle Oriente",
        city="San Pedro",
        confidence=0.65,
        reasoning="El texto menciona 'Valle Oriente' como zona del incidente.",
    )

    result = await geolocate_incident(
        "Incendio en bodega en Valle Oriente",
        client=mock_client,
    )

    assert result is not None
    assert result.neighborhood == "Valle Oriente"
    assert result.exact_address is None
    assert result.confidence >= 0.5


@pytest.mark.asyncio
async def test_low_confidence_vague_text() -> None:
    """Confidence < 0.3 → geolocate_incident returns None."""
    mock_client = _make_client(
        city="Monterrey",
        confidence=0.15,
        reasoning="El texto dice 'en la ciudad' sin especificar zona.",
    )

    result = await geolocate_incident(
        "Reportan accidente en la ciudad",
        client=mock_client,
    )

    assert result is None


@pytest.mark.asyncio
async def test_respects_cache_control() -> None:
    """System prompt must include cache_control=ephemeral for prompt caching."""
    mock_client = _make_client(city="Monterrey", confidence=0.7)

    await geolocate_incident("Balacera en zona norte", client=mock_client)

    # Inspect the call made to messages.create
    create_call: call = mock_client.messages.create.call_args
    kwargs = create_call.kwargs if create_call.kwargs else create_call[1]

    system_arg = kwargs.get("system")
    assert system_arg is not None, "system argument must be present"
    assert isinstance(system_arg, list), "system must be a list for cache_control"
    assert len(system_arg) >= 1

    first_block = system_arg[0]
    assert first_block["type"] == "text"
    assert "cache_control" in first_block
    assert first_block["cache_control"]["type"] == "ephemeral"


@pytest.mark.asyncio
async def test_maps_to_geolocation_result() -> None:
    """Full response maps correctly to all GeolocationResult fields."""
    mock_client = _make_client(
        exact_address="Carretera Nacional Km 268",
        neighborhood="Bosques de Valle Alto",
        city="Monterrey",
        latitude=25.577970,
        longitude=-100.251028,
        confidence=0.92,
        reasoning="El texto menciona el kilómetro exacto de Carretera Nacional.",
    )

    result = await geolocate_incident(
        "Volcadura en Carretera Nacional Km 268, Bosques de Valle Alto",
        client=mock_client,
    )

    assert result is not None
    assert isinstance(result, GeolocationResult)
    assert result.exact_address == "Carretera Nacional Km 268"
    assert result.neighborhood == "Bosques de Valle Alto"
    assert result.city == "Monterrey"
    assert result.latitude == pytest.approx(25.577970)
    assert result.longitude == pytest.approx(-100.251028)
    assert result.confidence == pytest.approx(0.92)
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_no_tool_use_block_returns_none() -> None:
    """If response has no tool_use block (unexpected), returns None gracefully."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "No puedo identificar la ubicación."

    resp = MagicMock()
    resp.content = [text_block]
    resp.usage = MagicMock(
        input_tokens=100,
        output_tokens=15,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=resp)

    result = await geolocate_incident("Texto ambiguo", client=client)
    assert result is None


@pytest.mark.asyncio
async def test_system_prompt_length_for_caching() -> None:
    """System prompt must be long enough to qualify for Anthropic prompt caching (>1024 tokens)."""
    # Rough token estimate: ~4 chars per token. Prompt must be > 4096 chars.
    assert len(_SYSTEM_PROMPT_GEO) > 4096, (
        f"System prompt is {len(_SYSTEM_PROMPT_GEO)} chars — likely < 1024 tokens. "
        "Extend it to qualify for prompt caching."
    )


def test_geo_tool_schema_has_required_fields() -> None:
    """Tool schema must require city, confidence, reasoning as per task spec."""
    required = _GEO_TOOL["input_schema"]["required"]
    assert "city" in required
    assert "confidence" in required
    assert "reasoning" in required


def test_geo_tool_confidence_bounds() -> None:
    """Confidence field must declare minimum=0, maximum=1."""
    props = _GEO_TOOL["input_schema"]["properties"]
    assert props["confidence"]["minimum"] == 0
    assert props["confidence"]["maximum"] == 1
