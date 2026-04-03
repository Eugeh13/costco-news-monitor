"""
GNews API source — uses the gnews library to fetch news.

Single responsibility: fetch news via GNews API and return NewsItem models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytz

from app.domain.models import NewsItem
from app.domain.ports import NewsSource

CENTRAL_TZ = pytz.timezone("America/Chicago")

# GNews search queries
GNEWS_QUERIES = [
    "Monterrey accidente",
    "Monterrey incendio",
    "Monterrey balacera",
    "San Pedro Garza García incidente",
    "carretera nacional Monterrey",
    "Escobedo Nuevo León",
]

try:
    from gnews import GNews
    GNEWS_AVAILABLE = True
except ImportError:
    GNEWS_AVAILABLE = False


class GNewsSource(NewsSource):
    """Collects news via the GNews API wrapper."""

    def __init__(self) -> None:
        self._client = None
        if GNEWS_AVAILABLE:
            try:
                self._client = GNews(
                    language="es",
                    country="MX",
                    max_results=15,
                )
            except Exception:
                pass

    def source_name(self) -> str:
        return "GNews"

    def collect(self) -> list[NewsItem]:
        if not self._client:
            return []

        items: list[NewsItem] = []
        seen: set[str] = set()

        for query in GNEWS_QUERIES:
            try:
                results = self._client.get_news(query)
                if not results:
                    continue
                for article in results:
                    titulo = article.get("title", "").strip()
                    if not titulo:
                        continue
                    key = titulo.lower()[:80]
                    if key in seen:
                        continue
                    seen.add(key)

                    items.append(
                        NewsItem(
                            titulo=titulo,
                            contenido=article.get("description", ""),
                            url=article.get("url"),
                            fuente=article.get("publisher", {}).get("title", "GNews"),
                            fecha_pub=self._parse_date(article.get("published date")),
                            source_type="gnews",
                        )
                    )
            except Exception as e:
                print(f"  ⚠️ Error en GNews: {e}")

        return items

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        formats = [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = CENTRAL_TZ.localize(dt)
                return dt
            except (ValueError, TypeError):
                continue
        return None
