"""
Deep analysis service — full analysis of candidate articles.

Takes a triage candidate, reads the full content, runs deep AI analysis,
checks geo proximity, and produces a resolved Alert (or discards the article).
"""

from __future__ import annotations

from typing import Optional

from app.domain.models import Alert, AnalysisResult, NewsItem, TriageResult
from app.domain.ports import AIProvider, DeepReader
from app.services.geo_service import GeoService


class DeepAnalysisService:
    """Processes individual candidates through deep analysis + geo check."""

    def __init__(
        self,
        ai: AIProvider,
        reader: DeepReader,
        geo: GeoService,
    ) -> None:
        self._ai = ai
        self._reader = reader
        self._geo = geo

    def analyze(self, news: NewsItem, triage: TriageResult) -> Optional[Alert]:
        """
        Full analysis pipeline for a single candidate.

        Steps:
        1. Extract full article content (deep read)
        2. Run deep AI analysis
        3. Verify geographic proximity
        4. Return Alert if relevant, None if discarded

        Returns:
            Alert if the article is relevant and within radius, None otherwise.
        """
        print(f"\n  📰 Procesando: {news.titulo[:70]}...")
        print(f"     Triage: {triage.estimated_category} | Sev ~{triage.estimated_severity} | {triage.location_hint}")

        # Step 1: Deep content extraction
        content = self._read_content(news)

        # Step 2: AI Deep Analysis
        print("     🤖 Análisis profundo...")
        analysis = self._ai.deep_analyze(news.titulo, content)

        if not analysis:
            print("     ⚠️ Error en análisis IA")
            return None

        if not analysis.is_relevant:
            print(f"     ❌ Descartada: {analysis.exclusion_reason}")
            return None

        print(f"     ✓ Relevante | {analysis.category.value} | Severidad: {analysis.severity}/10")

        # Step 3: Geo proximity check
        proximity = self._check_location(news, analysis, content)

        if not proximity or not proximity.is_within_radius:
            if proximity:
                print(f"     ❌ Fuera del radio ({proximity.distancia_km} km)")
            else:
                print("     ❌ Sin ubicación detectable")
            return None

        print(f"     ✓ Dentro del radio: {proximity.distancia_km} km de {proximity.costco_nombre}")

        # Step 4: Build Alert
        return Alert(
            news=news,
            analysis=analysis,
            proximity=proximity,
        )

    # ── Private ──────────────────────────────────────────────

    def _read_content(self, news: NewsItem) -> str:
        """Try to get full article content, fall back to snippet."""
        content = news.contenido

        if news.url:
            print("     📖 Extrayendo artículo completo...")
            full = self._reader.extract(news.url)
            if full and len(full) > len(content):
                content = full
                print(f"     ✓ Artículo completo: {len(content)} chars")
            else:
                print(f"     ⚠️ Usando snippet ({len(content)} chars)")

        return content

    def _check_location(self, news: NewsItem, analysis: AnalysisResult, content: str):
        """Check if the event is near a Costco."""
        location_text = analysis.location.extracted
        full_text = f"{news.titulo} {content}"

        if not location_text:
            # No location from AI — try road keywords only
            print("     ⚠️ Sin ubicación — verificando vialidades clave...")
            result = self._geo.check_roads_only(full_text)
            return result if result.is_within_radius else None

        if not analysis.location.is_specific:
            print(f"     ⚠️ Ubicación no específica: '{location_text}'")
        else:
            print(f"     📍 Ubicación: {location_text}")

        # Try normalized first, then raw
        normalized = analysis.location.normalized or location_text
        return self._geo.check_proximity(normalized, full_text)
