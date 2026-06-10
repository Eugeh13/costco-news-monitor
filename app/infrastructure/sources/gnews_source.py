"""
GNews API source — uses the gnews library to fetch news.

DESACTIVADA POR DEFAULT (settings.gnews_enabled = False). Diagnóstico 2026-06-10:

1. La lib gnews descarga con feedparser.parse(url) (urllib), que en local falla
   la verificación SSL y revienta con NetworkError ("object has no attribute
   'status'"). A diferencia de google_rss (arreglado en a76e0bb con requests+UA),
   gnews NO permite inyectar una sesión/User-Agent propio.
2. Es redundante: gnews consulta el mismo backend (news.google.com/rss/search)
   que GoogleRSSSource, y GOOGLE_NEWS_QUERIES ya cubre las GNEWS_QUERIES con
   variantes más completas (OR de keywords). Solo producía duplicados a dedupear.

Se conserva el archivo por si Google RSS muere y hay que reactivar esta vía:
exporta GNEWS_ENABLED=true (y resuelve el problema SSL de urllib primero).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytz

from app.config.settings import settings
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

    def __init__(self, enabled: bool | None = None) -> None:
        # Default: settings.gnews_enabled (False) — ver diagnóstico en el docstring.
        self._enabled = settings.gnews_enabled if enabled is None else enabled
        self._client = None
        if self._enabled and GNEWS_AVAILABLE:
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
        if not self._enabled:
            print("  ⚠️ GNews desactivada (redundante con Google RSS; ver gnews_source.py)")
            return []
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
                    # GNews publica en GMT; %Z parsea "GMT" pero deja tzinfo=None
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(CENTRAL_TZ)
            except (ValueError, TypeError):
                continue
        return None
