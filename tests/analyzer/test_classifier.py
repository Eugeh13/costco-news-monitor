"""Tests for src/analyzer/classifier.py — mocks Anthropic SDK."""
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from src.analyzer.classifier import Classifier
from src.analyzer.types import IncidentInput, IncidentType


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_tool_response(tool_name: str, tool_input: dict, in_tok: int = 100, out_tok: int = 40) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input

    resp = MagicMock()
    resp.content = [block]
    resp.usage = MagicMock(input_tokens=in_tok, output_tokens=out_tok)
    return resp


def _make_client(resp: MagicMock) -> MagicMock:
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


_INCIDENT = IncidentInput(
    title="Incendio en bodega cerca de Carretera Nacional",
    content="Un incendio de grandes dimensiones consume una bodega a 800m de Costco.",
    source="Milenio",
)


# ── Triage tests ──────────────────────────────────────────────────────────────

async def test_triage_relevant():
    resp = _make_tool_response("triage_result", {"is_relevant": True, "reason": "Fuego cerca de Costco"})
    clf = Classifier(_client=_make_client(resp))
    assert await clf.triage(_INCIDENT) is True


async def test_triage_irrelevant():
    resp = _make_tool_response("triage_result", {"is_relevant": False, "reason": "Noticia de entretenimiento"})
    clf = Classifier(_client=_make_client(resp))
    assert await clf.triage(_INCIDENT) is False


async def test_triage_missing_tool_block():
    """If the model returns no tool_use block, triage defaults to False."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "No relevant"

    resp = MagicMock()
    resp.content = [text_block]
    resp.usage = MagicMock(input_tokens=50, output_tokens=10)
    clf = Classifier(_client=_make_client(resp))
    assert await clf.triage(_INCIDENT) is False


# ── Deep-analyze tests ────────────────────────────────────────────────────────

async def test_deep_analyze_success():
    resp = _make_tool_response(
        "classify_incident",
        {
            "incident_type": "fire",
            "severity": 8,
            "affects_operations": True,
            "reasoning": "Incendio a 800m bloquea acceso principal",
            "recommended_action": "Activar protocolo de evacuación preventiva",
        },
    )
    clf = Classifier(_client=_make_client(resp))
    result = await clf.deep_analyze(_INCIDENT)
    assert result is not None
    assert result.incident_type == IncidentType.FIRE
    assert result.severity == 8
    assert result.affects_operations is True


async def test_deep_analyze_unknown_type_falls_back_to_none():
    """An unrecognised incident_type enum value returns None."""
    resp = _make_tool_response(
        "classify_incident",
        {
            "incident_type": "TOTALLY_UNKNOWN",
            "severity": 5,
            "affects_operations": False,
            "reasoning": "x",
            "recommended_action": "y",
        },
    )
    clf = Classifier(_client=_make_client(resp))
    result = await clf.deep_analyze(_INCIDENT)
    assert result is None


async def test_deep_analyze_no_tool_block_returns_none():
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Here is the analysis..."

    resp = MagicMock()
    resp.content = [text_block]
    resp.usage = MagicMock(input_tokens=300, output_tokens=100)
    clf = Classifier(_client=_make_client(resp))
    result = await clf.deep_analyze(_INCIDENT)
    assert result is None


async def test_deep_analyze_tokens_logged(caplog):
    import logging
    resp = _make_tool_response(
        "classify_incident",
        {
            "incident_type": "accident",
            "severity": 5,
            "affects_operations": False,
            "reasoning": "Accidente menor",
            "recommended_action": "Monitorear",
        },
        in_tok=750,
        out_tok=120,
    )
    clf = Classifier(_client=_make_client(resp))
    with caplog.at_level(logging.INFO, logger="src.analyzer.classifier"):
        await clf.deep_analyze(_INCIDENT)
    assert "750" in caplog.text
    assert "120" in caplog.text


async def test_triage_uses_haiku_model():
    """Ensure triage sends requests to the haiku model."""
    resp = _make_tool_response("triage_result", {"is_relevant": True, "reason": "ok"})
    mock_client = _make_client(resp)
    clf = Classifier(_client=mock_client)
    await clf.triage(_INCIDENT)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


async def test_deep_analyze_uses_sonnet_model():
    resp = _make_tool_response(
        "classify_incident",
        {"incident_type": "flood", "severity": 6, "affects_operations": True, "reasoning": "r", "recommended_action": "a"},
    )
    mock_client = _make_client(resp)
    clf = Classifier(_client=mock_client)
    await clf.deep_analyze(_INCIDENT)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
