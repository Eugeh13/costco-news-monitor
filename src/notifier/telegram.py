"""
Async Telegram Bot notifier for Costco Monterrey incidents.

send_alert()           — formats MarkdownV2 message + inline keyboard, sends to chat
handle_callback_query() — logs callback data (DB integration in Phase 2)

Retry policy:
  • 429 → respect Telegram's retry_after parameter
  • 5xx → exponential backoff, up to 4 attempts
"""

from __future__ import annotations

import asyncio
import structlog
from typing import Optional

import httpx

from src.analyzer.types import GeoLocation, IncidentClassification, IncidentType

logger = structlog.get_logger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

_TYPE_LABEL: dict[IncidentType, str] = {
    IncidentType.ACCIDENT:  "🚗 Accidente Vial",
    IncidentType.FIRE:      "🔥 Incendio",
    IncidentType.SHOOTING:  "🚨 Situación de Seguridad",
    IncidentType.ROADBLOCK: "🚧 Bloqueo",
    IncidentType.FLOOD:     "🌊 Inundación / Tromba",
    IncidentType.OTHER:     "📌 Incidente",
}

_SEVERITY_EMOJI: list[tuple[int, str]] = [
    (9, "🚨🚨"),
    (7, "🚨"),
    (4, "⚠️"),
    (1, "ℹ️"),
]


def _severity_emoji(severity: int) -> str:
    for threshold, emoji in _SEVERITY_EMOJI:
        if severity >= threshold:
            return emoji
    return "ℹ️"


# Characters that must be escaped in Telegram MarkdownV2
_MD_SPECIAL = frozenset(r"_*[]()~`>#+-=|{}.!")


def _esc(text: str) -> str:
    """Escape text for Telegram MarkdownV2."""
    return "".join(f"\\{c}" if c in _MD_SPECIAL else c for c in str(text))


class TelegramClient:
    """
    Async client for the Telegram Bot API.

    Usage::

        async with TelegramClient(token, chat_id) as bot:
            await bot.send_alert(classification, geo, distances)
    """

    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._token = token
        self._chat_id = chat_id
        self._http = http_client or httpx.AsyncClient(timeout=15.0)
        self._owns_http = http_client is None

    async def __aenter__(self) -> "TelegramClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http:
            await self._http.aclose()

    # ── Public ────────────────────────────────────────────────────────────────

    async def send_alert(
        self,
        classification: IncidentClassification,
        geo: Optional[GeoLocation],
        costco_distances: dict[str, float],
        *,
        source_url: Optional[str] = None,
        dry_run: bool = False,
    ) -> dict:
        """Build and send an incident alert with inline action buttons.

        When dry_run=True, logs the payload but skips the actual HTTP call.
        """
        sev_emoji = _severity_emoji(classification.severity)
        type_label = _TYPE_LABEL.get(classification.incident_type, "📌 Incidente")

        # Closest Costco
        closest_str = ""
        if costco_distances:
            name, dist = min(costco_distances.items(), key=lambda kv: kv[1])
            closest_str = f"📏 A *{_esc(f'{dist/1000:.1f}')} km* de {_esc(name)}\n"

        geo_line = f"📍 {_esc(geo.address)}\n" if geo else ""

        affects = "Sí" if classification.affects_operations else "No"

        text = (
            f"{sev_emoji} *ALERTA COSTCO MTY* {sev_emoji}\n\n"
            f"{_esc(type_label)}\n"
            f"Severidad: *{_esc(str(classification.severity))}/10*  ·  "
            f"Afecta operaciones: *{_esc(affects)}*\n\n"
            f"{geo_line}"
            f"{closest_str}\n"
            f"🧠 _{_esc(classification.reasoning[:350])}_\n\n"
            f"✅ *Acción:* {_esc(classification.recommended_action)}"
        )

        # Inline keyboard
        row: list[dict] = [
            {"text": "✅ Acusar recibo", "callback_data": "ack"},
            {"text": "❌ Dismiss", "callback_data": "dismiss"},
        ]
        extra_row: list[dict] = []
        if source_url:
            extra_row.append({"text": "🔗 Ver fuente", "url": source_url})

        inline_keyboard = [row] + ([extra_row] if extra_row else [])

        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "reply_markup": {"inline_keyboard": inline_keyboard},
        }

        if dry_run:
            logger.info("send_alert dry_run=True — skipping HTTP call", text_preview=text[:120])
            return {"dry_run": True, "payload": payload}

        return await self._post("sendMessage", payload)

    async def handle_callback_query(self, callback_query: dict) -> None:
        """
        Handle a Telegram inline-keyboard callback.
        Phase 2 will persist the acknowledgement to the database.
        """
        query_id = callback_query.get("id", "?")
        data = callback_query.get("data", "")
        user = callback_query.get("from", {}).get("username", "anonymous")
        msg_id = callback_query.get("message", {}).get("message_id", "?")
        logger.info(
            "callback_query id=%s data=%r user=%s msg_id=%s",
            query_id, data, user, msg_id,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    async def _post(self, method: str, payload: dict) -> dict:
        """POST to the Telegram Bot API with 429 + 5xx retry handling."""
        url = _TELEGRAM_API.format(token=self._token, method=method)
        max_attempts = 5

        for attempt in range(1, max_attempts + 1):
            resp = await self._http.post(url, json=payload)

            if resp.status_code == 429:
                params = resp.json().get("parameters", {})
                wait = int(params.get("retry_after", 5))
                logger.warning(
                    "Telegram 429 on %s — waiting %ds (attempt %d/%d)",
                    method, wait, attempt, max_attempts,
                )
                await asyncio.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = 2 ** (attempt - 1)  # 1, 2, 4, 8, 16 s
                logger.warning(
                    "Telegram %d on %s — retrying in %ds (attempt %d/%d)",
                    resp.status_code, method, wait, attempt, max_attempts,
                )
                await asyncio.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(
            f"Telegram {method} failed after {max_attempts} attempts"
        )
