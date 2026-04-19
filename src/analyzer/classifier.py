"""
AI classifier for incident analysis.

triage()      — claude-haiku-4-5-20251001  — fast noise filter
deep_analyze() — claude-sonnet-4-6          — full IncidentClassification

Tool-use forces structured output; tenacity retries on 5xx only.
"""

from __future__ import annotations

import structlog
from typing import Optional

import anthropic
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.analyzer.types import IncidentClassification, IncidentInput, IncidentType

logger = structlog.get_logger(__name__)

_TRIAGE_MODEL = "claude-haiku-4-5-20251001"
_ANALYZE_MODEL = "claude-sonnet-4-6"

_TRIAGE_TOOL: dict = {
    "name": "triage_result",
    "description": (
        "Decide if a news item describes an incident (accident, fire, shooting, "
        "roadblock, flood) that could affect Costco stores in Monterrey, NL."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "is_relevant": {
                "type": "boolean",
                "description": "True if the incident warrants deep analysis",
            },
            "reason": {
                "type": "string",
                "description": "One-sentence explanation",
            },
        },
        "required": ["is_relevant", "reason"],
        "additionalProperties": False,
    },
}

_CLASSIFY_TOOL: dict = {
    "name": "classify_incident",
    "description": "Produce a complete incident classification for the Costco Monterrey alert system.",
    "input_schema": {
        "type": "object",
        "properties": {
            "incident_type": {
                "type": "string",
                "enum": ["accident", "fire", "shooting", "roadblock", "flood", "other"],
            },
            "severity": {
                "type": "integer",
                "description": "Severity 1 (trivial) to 10 (catastrophic)",
            },
            "affects_operations": {
                "type": "boolean",
                "description": "True if the incident likely affects store access or operations",
            },
            "reasoning": {
                "type": "string",
                "description": "Detailed reasoning for this classification",
            },
            "recommended_action": {
                "type": "string",
                "description": "Specific action recommended for Costco management",
            },
        },
        "required": [
            "incident_type",
            "severity",
            "affects_operations",
            "reasoning",
            "recommended_action",
        ],
        "additionalProperties": False,
    },
}

_ANALYZE_SYSTEM = (
    "You are an expert analyst for Costco Monterrey's security and operations team. "
    "Three Costco stores are monitored in Monterrey, NL, México:\n"
    "• Costco Carretera Nacional — Km 268, Bosques de Valle Alto\n"
    "• Costco Cumbres — Alejandro de Rodas 6767, Cumbres\n"
    "• Costco Valle Oriente — Av Lázaro Cárdenas 800, San Pedro Garza García\n\n"
    "Classify the incident type, severity (1-10), and whether it disrupts store "
    "operations or blocks customer access within a 3 km radius."
)


def _is_5xx(exc: BaseException) -> bool:
    return isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500


class Classifier:
    """Async two-stage incident classifier backed by the Anthropic SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        _client: Optional[anthropic.AsyncAnthropic] = None,
    ) -> None:
        self._client = _client or anthropic.AsyncAnthropic(api_key=api_key)

    # ── Public API ────────────────────────────────────────────────────────────

    async def triage(self, incident: IncidentInput) -> bool:
        """Quick triage with haiku. Returns True if the item passes to deep analysis."""
        user = (
            f"Title: {incident.title}\n"
            f"Content excerpt: {incident.content[:400]}\n"
            f"Source: {incident.source}"
        )
        response = await self._api_call(
            model=_TRIAGE_MODEL,
            system=(
                "You are a triage filter for Costco Monterrey. Quickly decide if a "
                "news item describes a relevant incident (accident, fire, shooting, "
                "roadblock, flood) near any of 3 Costco stores in Monterrey, NL, México. "
                "Discard press releases, sports news, entertainment, opinion pieces, and "
                "incidents far from the metro area."
            ),
            user=user,
            tool=_TRIAGE_TOOL,
            max_tokens=256,
        )
        tool_input = self._extract_tool_input(response, "triage_result")
        if tool_input is None:
            logger.warning("triage: no tool_use block in response — treating as irrelevant")
            return False

        is_relevant: bool = bool(tool_input.get("is_relevant", False))
        logger.info(
            "triage result=%s reason=%r in_tokens=%d out_tokens=%d",
            is_relevant,
            tool_input.get("reason", ""),
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return is_relevant

    async def deep_analyze(self, incident: IncidentInput) -> Optional[IncidentClassification]:
        """Full analysis with sonnet. Returns IncidentClassification or None on failure."""
        user = (
            f"Title: {incident.title}\n\n"
            f"Content: {incident.content[:2500]}\n\n"
            f"Source: {incident.source}\n"
            f"URL: {incident.url or 'N/A'}\n"
            f"Published: {incident.published_at.isoformat() if incident.published_at else 'unknown'}"
        )
        response = await self._api_call(
            model=_ANALYZE_MODEL,
            system=_ANALYZE_SYSTEM,
            user=user,
            tool=_CLASSIFY_TOOL,
            max_tokens=1024,
        )
        tool_input = self._extract_tool_input(response, "classify_incident")
        if tool_input is None:
            logger.error("deep_analyze: no tool_use block in response")
            return None

        logger.info(
            "deep_analyze type=%s severity=%d affects_ops=%s in_tokens=%d out_tokens=%d",
            tool_input.get("incident_type"),
            tool_input.get("severity", 0),
            tool_input.get("affects_operations"),
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        try:
            return IncidentClassification(
                incident_type=IncidentType(tool_input["incident_type"]),
                severity=int(tool_input["severity"]),
                affects_operations=bool(tool_input["affects_operations"]),
                reasoning=tool_input["reasoning"],
                recommended_action=tool_input["recommended_action"],
            )
        except (KeyError, ValueError) as exc:
            logger.error("deep_analyze: failed to build IncidentClassification: %s — raw=%s", exc, tool_input)
            return None

    # ── Private ───────────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception(_is_5xx),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def _api_call(
        self,
        model: str,
        system: str,
        user: str,
        tool: dict,
        max_tokens: int,
    ) -> anthropic.types.Message:
        return await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )

    @staticmethod
    def _extract_tool_input(response: anthropic.types.Message, name: str) -> Optional[dict]:
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == name:
                return block.input  # type: ignore[return-value]
        return None
