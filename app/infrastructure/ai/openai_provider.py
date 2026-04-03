"""
OpenAI provider — implements AIProvider interface using the OpenAI SDK.

Single responsibility: translate between domain models and OpenAI API calls.
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
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(AIProvider):
    """OpenAI-based AI provider for triage and deep analysis."""

    def __init__(self, model: str = "gpt-5-mini", api_key: Optional[str] = None) -> None:
        if not OPENAI_AVAILABLE:
            raise ImportError("pip install openai")
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self._model = model

    def provider_name(self) -> str:
        return f"openai / {self._model}"

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
        return self._parse_triage_response(raw, len(articles))

    def deep_analyze(self, title: str, content: str) -> Optional[AnalysisResult]:
        user_prompt = DEEP_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            title=title,
            content=content[:3000],
        )

        raw = self._call(DEEP_ANALYSIS_SYSTEM_PROMPT, user_prompt)
        return self._parse_analysis_response(raw)

    # ── Private ──────────────────────────────────────────────

    def _call(self, system: str, user: str) -> Optional[str]:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  ⚠️ OpenAI error: {e}")
            return None

    def _parse_triage_response(self, raw: Optional[str], count: int) -> list[TriageResult]:
        if not raw:
            # Fallback: treat all as candidates
            return [
                TriageResult(index=i, decision=TriageDecision.UNKNOWN)
                for i in range(count)
            ]

        try:
            data = json.loads(self._extract_json(raw))
            # Handle both {"results": [...]} and direct array [...] if the model hallucinates
            items = data.get("results", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            
            results = []
            for item in items:
                decision_str = item.get("decision", "desconocido")
                try:
                    decision = TriageDecision(decision_str)
                except ValueError:
                    decision = TriageDecision.UNKNOWN

                results.append(
                    TriageResult(
                        index=item.get("index", 0),
                        decision=decision,
                        estimated_category=item.get("category", "desconocido"),
                        estimated_severity=min(max(item.get("severity", 5), 1), 10),
                        location_hint=item.get("location_hint", "no_especifica"),
                        reason=item.get("reason", ""),
                    )
                )
            return results

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ⚠️ JSON parse error: {e}")
            print(f"  ⚠️ Triage falló — fallback: todas como candidatas")
            return [
                TriageResult(index=i, decision=TriageDecision.UNKNOWN)
                for i in range(count)
            ]

    def _parse_analysis_response(self, raw: Optional[str]) -> Optional[AnalysisResult]:
        if not raw:
            return None

        try:
            data = json.loads(self._extract_json(raw))

            location_data = data.get("location", {})
            details = data.get("details", {})

            # Parse category safely
            cat_str = data.get("category", "otro")
            try:
                category = IncidentCategory(cat_str)
            except ValueError:
                category = IncidentCategory.OTRO

            # Parse traffic impact safely
            impact_str = details.get("traffic_impact", "unknown")
            try:
                traffic = TrafficImpact(impact_str)
            except ValueError:
                traffic = TrafficImpact.UNKNOWN

            return AnalysisResult(
                is_relevant=data.get("is_relevant", False),
                category=category,
                severity=min(max(data.get("severity", 5), 1), 10),
                summary=data.get("summary", ""),
                exclusion_reason=data.get("exclusion_reason", ""),
                location=LocationInfo(
                    extracted=location_data.get("extracted", ""),
                    normalized=location_data.get("normalized", ""),
                    is_specific=location_data.get("is_specific", False),
                ),
                victims=details.get("victims", 0),
                traffic_impact=traffic,
                emergency_services=details.get("emergency_services", False),
            )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ⚠️ Analysis parse error: {e}")
            return None

    @staticmethod
    def _extract_json(text: str) -> str:
        """Strip markdown code fences if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return text
