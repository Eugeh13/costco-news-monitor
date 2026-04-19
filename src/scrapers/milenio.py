"""
Milenio scraper — Última Hora + Monterrey sections.

Uses selectolax for fast HTML parsing. Gracefully handles structural changes:
if a selector returns nothing, logs a warning and continues without crashing.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import pytz
from selectolax.parser import HTMLParser

from src.scrapers.base import BaseScraper, RawArticle, build_client

_BASE = "https://www.milenio.com"
_SECTIONS = [
    f"{_BASE}/ultima-hora",
    f"{_BASE}/estados/nuevo-leon",
]
_CENTRAL_TZ = pytz.timezone("America/Chicago")

# Selector candidates — tried in order so minor HTML changes don't break parsing
_ARTICLE_SELECTORS = [
    "article.card",
    "article",
    ".card-item",
    "li.item",
]
_TITLE_SELECTORS = ["h2 a", "h3 a", "h1 a", ".title a", "a[href]"]
_DATE_SELECTORS = ["time[datetime]", "time", ".date", ".published", "[datetime]"]
_SNIPPET_SELECTORS = [".summary", ".description", "p"]


class MilenioScraper(BaseScraper):
    source_name = "Milenio"

    async def fetch(self) -> list[RawArticle]:
        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        async with build_client() as client:
            for section_url in _SECTIONS:
                try:
                    resp = await self._get(client, section_url)
                    parsed = self._parse(resp.text, section_url)
                    for art in parsed:
                        if art.url not in seen_urls:
                            seen_urls.add(art.url)
                            articles.append(art)
                except Exception as exc:
                    self.log.warning("section_failed", url=section_url, error=str(exc))

        return articles

    # ── Parsing ───────────────────────────────────────────────

    def _parse(self, html: str, page_url: str) -> list[RawArticle]:
        tree = HTMLParser(html)
        articles: list[RawArticle] = []

        nodes = self._find_nodes(tree)
        if not nodes:
            self.log.warning("no_article_nodes_found", page=page_url)
            return articles

        for node in nodes:
            try:
                art = self._extract(node, page_url)
                if art:
                    articles.append(art)
            except Exception as exc:
                self.log.debug("article_parse_error", error=str(exc))

        return articles

    def _find_nodes(self, tree: HTMLParser):
        for sel in _ARTICLE_SELECTORS:
            nodes = tree.css(sel)
            if nodes:
                return nodes
        return []

    def _extract(self, node, page_url: str) -> Optional[RawArticle]:
        title, url = self._title_and_url(node, page_url)
        if not title or not url:
            return None

        published_at = self._parse_date(node)
        snippet = self._snippet(node)

        return RawArticle(
            title=title,
            url=url,
            source_name=self.source_name,
            published_at=published_at,
            content_snippet=snippet,
        )

    def _title_and_url(self, node, page_url: str) -> tuple[str, str]:
        for sel in _TITLE_SELECTORS:
            el = node.css_first(sel)
            if el:
                title = el.text(strip=True)
                href = el.attributes.get("href", "")
                if title and href:
                    return title, urljoin(_BASE, href)
        return "", ""

    def _parse_date(self, node) -> datetime:
        for sel in _DATE_SELECTORS:
            el = node.css_first(sel)
            if el:
                dt_str = el.attributes.get("datetime", "") or el.text(strip=True)
                parsed = _try_parse_datetime(dt_str)
                if parsed:
                    return parsed
        return datetime.now(_CENTRAL_TZ)

    def _snippet(self, node) -> str:
        for sel in _SNIPPET_SELECTORS:
            el = node.css_first(sel)
            if el:
                text = el.text(strip=True)
                if len(text) > 20:
                    return text[:400]
        return ""


def _try_parse_datetime(raw: str) -> Optional[datetime]:
    raw = raw.strip()
    if not raw:
        return None
    # ISO 8601
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = _CENTRAL_TZ.localize(dt)
        return dt
    except ValueError:
        pass
    # Common Spanish-locale patterns: "28 oct 2025 18:00"
    patterns = [
        "%d %b %Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
    ]
    for fmt in patterns:
        try:
            dt = datetime.strptime(raw[:25], fmt)
            if dt.tzinfo is None:
                dt = _CENTRAL_TZ.localize(dt)
            return dt
        except ValueError:
            continue
    return None
