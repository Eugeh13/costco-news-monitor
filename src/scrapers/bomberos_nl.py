"""
Bomberos Nuevo León / Monterrey scraper — Google News RSS.
"""

from __future__ import annotations

from src.scrapers.base import BaseScraper, RawArticle, build_client
from src.scrapers._google_news_rss import fetch_google_news

_QUERY = "Bomberos Nuevo León Monterrey"


class BomberosNLScraper(BaseScraper):
    source_name = "Bomberos NL (Google News)"

    async def fetch(self) -> list[RawArticle]:
        async with build_client() as client:
            return await fetch_google_news(
                client, _QUERY, self.source_name, self.log,
                max_age_hours=self.max_age_hours,
            )
