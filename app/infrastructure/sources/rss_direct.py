"""
Direct RSS feed source — fetches from local news outlet RSS feeds.

Single responsibility: fetch direct RSS feeds and return NewsItem models.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import feedparser
import pytz
import requests

from app.domain.models import NewsItem
from app.domain.ports import NewsSource

CENTRAL_TZ = pytz.timezone("America/Chicago")


class RSSFeed:
    """Configuration for a single RSS feed."""

    def __init__(self, url: str, nombre: str, filtro_geo: bool = True) -> None:
        self.url = url
        self.nombre = nombre
        self.filtro_geo = filtro_geo


# Default feeds for Monterrey / Coahuila region
DEFAULT_FEEDS = [
    RSSFeed(
        url="https://www.milenio.com/rss/seccion/estados/nuevo-leon",
        nombre="Milenio NL",
        filtro_geo=False,
    ),
    RSSFeed(
        url="https://vanguardia.com.mx/rss.xml",
        nombre="Vanguardia",
        filtro_geo=True,
    ),
]


class RSSDirectSource(NewsSource):
    """Collects news from direct RSS feed URLs."""

    def __init__(self, feeds: list[RSSFeed] | None = None) -> None:
        self._feeds = feeds or DEFAULT_FEEDS

    def source_name(self) -> str:
        return "RSS directo"

    def collect(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        seen: set[str] = set()

        for feed_config in self._feeds:
            try:
                fetched = self._fetch_feed(feed_config)
                for item in fetched:
                    key = item.titulo.lower().strip()[:80]
                    if key not in seen:
                        seen.add(key)
                        items.append(item)
            except Exception as e:
                print(f"  ⚠️ Error en RSS {feed_config.nombre}: {e}")

        return items

    # ── Private ──────────────────────────────────────────────

    def _fetch_feed(self, feed_config: RSSFeed) -> list[NewsItem]:
        response = requests.get(feed_config.url, timeout=15)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        items: list[NewsItem] = []

        for entry in feed.entries:
            titulo = self._clean_html(entry.get("title", "")).strip()
            if not titulo:
                continue

            items.append(
                NewsItem(
                    titulo=titulo,
                    contenido=self._clean_html(entry.get("summary", entry.get("description", ""))),
                    url=entry.get("link"),
                    fuente=feed_config.nombre,
                    fecha_pub=self._parse_date(entry),
                    source_type="rss_directo",
                )
            )

        return items

    @staticmethod
    def _clean_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()

    @staticmethod
    def _parse_date(entry: dict) -> Optional[datetime]:
        date_str = entry.get("published") or entry.get("updated")
        if not date_str:
            return None
        try:
            dt = datetime(*feedparser._parse_date(date_str)[:6])
            return CENTRAL_TZ.localize(dt)
        except Exception:
            return None
