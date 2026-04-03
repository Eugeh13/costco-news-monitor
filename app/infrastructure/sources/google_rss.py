"""
Google News RSS source — scrapes Google News RSS feeds for Monterrey region.

Single responsibility: fetch and parse Google News RSS into NewsItem models.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
import pytz

from app.domain.models import NewsItem
from app.domain.ports import NewsSource

CENTRAL_TZ = pytz.timezone("America/Chicago")

# Search queries focused on Monterrey metro area
GOOGLE_NEWS_QUERIES = [
    "Monterrey Nuevo León accidente OR choque OR incendio OR balacera",
    "San Pedro Garza García incidente OR accidente OR emergencia",
    "carretera nacional Monterrey accidente OR cierre",
    "Lázaro Cárdenas Monterrey accidente OR choque OR incendio",
    "Escobedo Nuevo León accidente OR incendio OR balacera",
    "Valle Oriente Monterrey incidente OR emergencia",
]


class GoogleRSSSource(NewsSource):
    """Collects news from Google News RSS feeds."""

    def source_name(self) -> str:
        return "Google News RSS"

    def collect(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        seen_titles: set[str] = set()

        for query in GOOGLE_NEWS_QUERIES:
            try:
                fetched = self._fetch_query(query)
                for item in fetched:
                    key = item.titulo.lower().strip()[:80]
                    if key not in seen_titles:
                        seen_titles.add(key)
                        items.append(item)
            except Exception as e:
                print(f"  ⚠️ Error en Google RSS query: {e}")

        return items

    # ── Private ──────────────────────────────────────────────

    def _fetch_query(self, query: str) -> list[NewsItem]:
        encoded = query.replace(" ", "+")
        url = (
            f"https://news.google.com/rss/search?"
            f"q={encoded}&hl=es-419&gl=MX&ceid=MX:es-419"
        )

        feed = feedparser.parse(url)
        items: list[NewsItem] = []

        for entry in feed.entries:
            titulo = self._clean_html(entry.get("title", ""))
            if not titulo:
                continue

            fecha = self._parse_date(entry.get("published"))

            items.append(
                NewsItem(
                    titulo=titulo,
                    contenido=self._clean_html(entry.get("summary", "")),
                    url=entry.get("link"),
                    fuente=self._extract_source(entry.get("title", "")),
                    fecha_pub=fecha,
                    source_type="google_rss",
                )
            )

        return items

    @staticmethod
    def _clean_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()

    @staticmethod
    def _extract_source(title: str) -> str:
        """Google News titles end with ' - SourceName'."""
        if " - " in title:
            return title.rsplit(" - ", 1)[-1].strip()
        return "Google News"

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            dt = datetime(*feedparser._parse_date(date_str)[:6])
            return CENTRAL_TZ.localize(dt)
        except Exception:
            return None
