"""Tests for src/notifier/telegram.py — mocks Telegram Bot API via pytest-httpx."""
import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock

from src.analyzer.types import GeoLocation, IncidentClassification, IncidentType
from src.notifier.telegram import TelegramClient, _esc

_TOKEN = "123456:ABC-TEST"
_CHAT = "-100987654321"
_SEND_URL = f"https://api.telegram.org/bot{_TOKEN}/sendMessage"


@pytest.fixture
def classification() -> IncidentClassification:
    return IncidentClassification(
        incident_type=IncidentType.FIRE,
        severity=8,
        affects_operations=True,
        reasoning="Incendio a 600m del acceso principal de Costco Carretera Nacional.",
        recommended_action="Notificar gerencia y activar protocolo de evacuación.",
    )


@pytest.fixture
def geo() -> GeoLocation:
    return GeoLocation(lat=25.581, lon=-100.249, address="Carretera Nacional, Monterrey, NL", confidence=0.9)


@pytest.fixture
def distances() -> dict:
    return {
        "Costco Carretera Nacional": 610.0,
        "Costco Cumbres": 18_200.0,
        "Costco Valle Oriente": 9_800.0,
    }


# ── _esc helper ───────────────────────────────────────────────────────────────

def test_esc_plain_text():
    assert _esc("Hello World") == "Hello World"


def test_esc_special_chars():
    escaped = _esc("1.5 km (aprox.) - 100% real!")  # plain hyphen-minus
    assert "\\." in escaped
    assert "\\(" in escaped
    assert "\\)" in escaped
    assert "\\-" in escaped
    assert "\\!" in escaped


# ── send_alert ────────────────────────────────────────────────────────────────

async def test_send_alert_success(httpx_mock: HTTPXMock, classification, geo, distances):
    httpx_mock.add_response(url=_SEND_URL, json={"ok": True, "result": {"message_id": 42}})

    import httpx as _httpx
    async with _httpx.AsyncClient() as http:
        client = TelegramClient(_TOKEN, _CHAT, http_client=http)
        result = await client.send_alert(
            classification, geo, distances, source_url="https://example.com/nota"
        )

    assert result["ok"] is True
    req = httpx_mock.get_request()
    body = req.read()
    import json
    payload = json.loads(body)
    assert payload["chat_id"] == _CHAT
    assert payload["parse_mode"] == "MarkdownV2"
    # Inline keyboard should exist
    kb = payload["reply_markup"]["inline_keyboard"]
    assert any(btn["callback_data"] == "ack" for row in kb for btn in row)
    assert any(btn["callback_data"] == "dismiss" for row in kb for btn in row)
    assert any(btn.get("url") == "https://example.com/nota" for row in kb for btn in row)


async def test_send_alert_no_source_url(httpx_mock: HTTPXMock, classification, geo, distances):
    httpx_mock.add_response(url=_SEND_URL, json={"ok": True, "result": {"message_id": 7}})

    import httpx as _httpx
    import json
    async with _httpx.AsyncClient() as http:
        client = TelegramClient(_TOKEN, _CHAT, http_client=http)
        await client.send_alert(classification, geo, distances)

    payload = json.loads(httpx_mock.get_request().read())
    kb = payload["reply_markup"]["inline_keyboard"]
    # No "url" key when source_url is None
    assert not any("url" in btn for row in kb for btn in row)


async def test_send_alert_no_geo(httpx_mock: HTTPXMock, classification, distances):
    httpx_mock.add_response(url=_SEND_URL, json={"ok": True, "result": {"message_id": 3}})

    import httpx as _httpx
    async with _httpx.AsyncClient() as http:
        client = TelegramClient(_TOKEN, _CHAT, http_client=http)
        result = await client.send_alert(classification, None, distances)

    assert result["ok"] is True


# ── Retry behaviour ───────────────────────────────────────────────────────────

async def test_send_alert_retries_on_5xx(httpx_mock: HTTPXMock, classification, geo, distances):
    # First response: 500; second: success
    httpx_mock.add_response(url=_SEND_URL, status_code=500)
    httpx_mock.add_response(url=_SEND_URL, json={"ok": True, "result": {"message_id": 9}})

    import httpx as _httpx
    async with _httpx.AsyncClient() as http:
        client = TelegramClient(_TOKEN, _CHAT, http_client=http)
        result = await client.send_alert(classification, geo, distances)

    assert result["ok"] is True
    assert len(httpx_mock.get_requests()) == 2


async def test_send_alert_respects_retry_after_on_429(httpx_mock: HTTPXMock, classification, geo, distances):
    httpx_mock.add_response(
        url=_SEND_URL,
        status_code=429,
        json={"ok": False, "parameters": {"retry_after": 1}},
    )
    httpx_mock.add_response(url=_SEND_URL, json={"ok": True, "result": {"message_id": 55}})

    import httpx as _httpx
    async with _httpx.AsyncClient() as http:
        client = TelegramClient(_TOKEN, _CHAT, http_client=http)
        result = await client.send_alert(classification, geo, distances)

    assert result["ok"] is True
    assert len(httpx_mock.get_requests()) == 2


# ── handle_callback_query ─────────────────────────────────────────────────────

async def test_handle_callback_query_logs(caplog):
    import logging
    client = TelegramClient(_TOKEN, _CHAT)
    query = {
        "id": "cq_001",
        "data": "ack",
        "from": {"username": "ops_user"},
        "message": {"message_id": 42},
    }
    with caplog.at_level(logging.INFO, logger="src.notifier.telegram"):
        await client.handle_callback_query(query)

    assert "ack" in caplog.text
    assert "ops_user" in caplog.text
    assert "cq_001" in caplog.text
