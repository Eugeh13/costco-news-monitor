"""
El Horizonte scraper — portal de noticias de Monterrey/NL.

Intenta RSS primero; si el feed no existe o está vacío, hace scraping HTML.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import pytz
from selectolax.parser import HTMLParser

from src.scrapers.base import BaseScraper, RawArticle, build_client
from src.scrapers.info7 import (
    _clean_html,
    _find_nodes,
    _parse_date_node,
    _parse_feedparser_date,
    _snippet_text,
    _title_and_url,
    _try_parse_datetime,
)

_BASE = "https://www.elhorizonte.mx"
_RSS_CANDIDATES = [
    f"{_BASE}/rss/portada",
    f"{_BASE}/feed",
    f"{_BASE}/rss",
]
_HTML_URL = f"{_BASE}/nuevo-leon/"
_CENTRAL_TZ = pytz.timezone("America/Chicago")

_ARTICLE_SELECTORS = ["article", ".nota", ".card", ".item-nota", "li.item"]
_TITLE_SELECTORS = ["h2 a", "h3 a", "h1 a", ".titulo a", "a.link-nota", "a[href]"]
_DATE_SELECTORS = ["time[datetime]", "time", ".fecha", ".date", "[datetime]"]
_SNIPPET_SELECTORS = [".bajada", ".resumen", ".summary", "p"]


class HorizonteScraper(BaseScraper):
    source_name = "El Horizonte"

    async def fetch(self) -> list[RawArticle]:
        async with build_client() as client:
            articles = await self._fetch_rss(client)
            if not articles:
                self.log.info("rss_empty_falling_back_to_html")
                articles = await self._fetch_html(client)
        return articles

    # ── RSS path ─────────────────────────────────────────────

    async def _fetch_rss(self, client) -> list[RawArticle]:
        for rss_url in _RSS_CANDIDATES:
            try:
                resp = await self._get(client, rss_url)
                feed = feedparser.parse(resp.text)
                if not feed.entries:
                    continue
                articles = []
                for entry in feed.entries:
                    art = self._entry_to_article(entry)
                    if art:
                        articles.append(art)
                if articles:
                    self.log.info("rss_ok", url=rss_url, count=len(articles))
                    return articles
            except Exception as exc:
                self.log.debug("rss_candidate_failed", url=rss_url, error=str(exc))
        return []

    def _entry_to_article(self, entry) -> Optional[RawArticle]:
        title = _clean_html(entry.get("title", "")).strip()
        url = entry.get("link", "").strip()
        if not title or not url:
            return None
        published_at = _parse_feedparser_date(entry.get("published")) or datetime.now(_CENTRAL_TZ)
        snippet = _clean_html(entry.get("summary", entry.get("description", "")))[:400]
        return RawArticle(
            title=title,
            url=url,
            source_name=self.source_name,
            published_at=published_at,
            content_snippet=snippet,
        )

    # ── HTML fallback ─────────────────────────────────────────

    async def _fetch_html(self, client) -> list[RawArticle]:
        try:
            resp = await self._get(client, _HTML_URL)
            return self._parse_html(resp.text)
        except Exception as exc:
            self.log.warning("html_fetch_failed", error=str(exc))
            return []

    def _parse_html(self, html: str) -> list[RawArticle]:
        tree = HTMLParser(html)
        articles = []

        nodes = _find_nodes(tree, _ARTICLE_SELECTORS)
        if not nodes:
            self.log.warning("no_article_nodes_found")
            return articles

        for node in nodes:
            try:
                title, url = _title_and_url(node, _BASE, _TITLE_SELECTORS)
                if not title or not url:
                    continue
                published_at = _parse_date_node(node, _DATE_SELECTORS) or datetime.now(_CENTRAL_TZ)
                snippet = _snippet_text(node, _SNIPPET_SELECTORS)
                articles.append(RawArticle(
                    title=title,
                    url=url,
                    source_name=self.source_name,
                    published_at=published_at,
                    content_snippet=snippet,
                ))
            except Exception as exc:
                self.log.debug("article_parse_error", error=str(exc))

        return articles
