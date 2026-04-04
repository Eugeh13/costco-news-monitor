"""
Anthropic provider — implements AIProvider interface using the Anthropic SDK.

Mirror of OpenAI provider. Same prompts, different API surface.
"""

from __future__ import annotations

import json
from typing import Optional

from app.domain.models import (
    AnalysisResult,
    IncidentCategory,
    LocationInfo,
    TrafficImpact,
    TriageDecision,
    TriageResult,
)
from app.domain.ports import AIProvider
from app.infrastructure.ai.prompts import (
    DEEP_ANALYSIS_SYSTEM_PROMPT,
    DEEP_ANALYSIS_USER_PROMPT_TEMPLATE,
    TRIAGE_SYSTEM_PROMPT,
    TRIAGE_USER_PROMPT_TEMPLATE,
)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(AIProvider):
    """Anthropic-based AI provider for triage and deep analysis."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001", api_key: Optional[str] = None) -> None:
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("pip install anthropic")
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._model = model

    def provider_name(self) -> str:
        return f"anthropic / {self._model}"

    def batch_triage(self, articles: list[dict]) -> list[TriageResult]:
        articles_text = json.dumps(
            [{"index": i, **a} for i, a in enumerate(articles)],
            ensure_ascii=False,
            indent=2,
        )
        user_prompt = TRIAGE_USER_PROMPT_TEMPLATE.format(
            count=len(articles),
            articles_json=articles_text,
        )

        raw = self._call(TRIAGE_SYSTEM_PROMPT, user_prompt)
        return self._parse_triage(raw, len(articles))

    def deep_analyze(self, title: str, content: str) -> Optional[AnalysisResult]:
        user_prompt = DEEP_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            title=title,
            content=content[:3000],
        )

        raw = self._call(DEEP_ANALYSIS_SYSTEM_PROMPT, user_prompt)
        return self._parse_analysis(raw)

    # ── Private ──────────────────────────────────────────────

    def _call(self, system: str, user: str) -> Optional[str]:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except Exception as e:
            print(f"  ⚠️ Anthropic error: {e}")
            return None

    def _parse_triage(self, raw: Optional[str], count: int) -> list[TriageResult]:
        if not raw:
            return [TriageResult(index=i, decision=TriageDecision.UNKNOWN) for i in range(count)]

        try:
            text = self._extract_json(raw)
            data = json.loads(text)
            results = []
            for item in data:
                try:
                    decision = TriageDecision(item.get("decision", "desconocido"))
                except ValueError:
                    decision = TriageDecision.UNKNOWN
                results.append(TriageResult(
                    index=item.get("index", 0),
                    decision=decision,
                    estimated_category=item.get("category", "desconocido"),
                    estimated_severity=min(max(item.get("severity", 5), 1), 10),
                    location_hint=item.get("location_hint", "no_especifica"),
                    reason=item.get("reason", ""),
                ))
            return results
        except (json.JSONDecodeError, KeyError):
            return [TriageResult(index=i, decision=TriageDecision.UNKNOWN) for i in range(count)]

    def _parse_analysis(self, raw: Optional[str]) -> Optional[AnalysisResult]:
        if not raw:
            return None
        try:
            data = json.loads(self._extract_json(raw))
            loc = data.get("location", {})
            det = data.get("details", {})
            try:
                cat = IncidentCategory(data.get("category", "otro"))
            except ValueError:
                cat = IncidentCategory.OTRO
            try:
                traffic = TrafficImpact(det.get("traffic_impact", "unknown"))
            except ValueError:
                traffic = TrafficImpact.UNKNOWN

            return AnalysisResult(
                is_relevant=data.get("is_relevant", False),
                category=cat,
                severity=min(max(data.get("severity", 5), 1), 10),
                summary=data.get("summary", ""),
                exclusion_reason=data.get("exclusion_reason", ""),
                location=LocationInfo(
                    extracted=loc.get("extracted", ""),
                    normalized=loc.get("normalized", ""),
                    is_specific=loc.get("is_specific", False),
                ),
                victims=det.get("victims", 0),
                traffic_impact=traffic,
                emergency_services=det.get("emergency_services", False),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return text
