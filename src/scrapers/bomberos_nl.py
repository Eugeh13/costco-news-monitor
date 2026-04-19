"""
Bomberos Nuevo León / Monterrey scraper — Google News RSS.

Mismo patrón que proteccion_civil: filtra últimas 24 horas.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.scrapers.base import BaseScraper, RawArticle, build_client
from src.scrapers._google_news_rss import fetch_google_news

_QUERY = "Bomberos Nuevo León Monterrey"
_MAX_AGE_HOURS = 24


class BomberosNLScraper(BaseScraper):
    source_name = "Bomberos NL (Google News)"

    async def fetch(self) -> list[RawArticle]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=_MAX_AGE_HOURS)
        async with build_client() as client:
            all_articles = await fetch_google_news(client, _QUERY, self.source_name, self.log)

        fresh = [a for a in all_articles if a.published_at >= cutoff]
        self.log.info("age_filter_applied", total=len(all_articles), fresh=len(fresh))
        return fresh
