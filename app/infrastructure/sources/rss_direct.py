"""
Direct RSS feed source — fetches from local news outlet RSS feeds.

Single responsibility: fetch direct RSS feeds and return NewsItem models.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
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
#
# NOTA (2026-06-10): se eliminó el feed de Milenio NL. Milenio ya no publica RSS:
# se probaron en vivo /rss/seccion/estados/nuevo-leon (404), /rss, /rss/portada,
# /rss/seccion/policia, /rss/seccion/monterrey, /rss.xml, /feed, /api/v1/rss y
# las rutas /rss7/ y /rss10/ de su robots.txt — todas devuelven 404 o HTML.
# La cobertura de Milenio llega igualmente vía Google News RSS (google_rss.py),
# que indexa milenio.com. Si Milenio reactiva un RSS, agregarlo aquí probado en vivo.
DEFAULT_FEEDS = [
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
        # feedparser entrega *_parsed como struct_time en UTC
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed:
            return None
        try:
            dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            return dt.astimezone(CENTRAL_TZ)
        except Exception:
            return None
