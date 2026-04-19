"""
Info7 Monterrey scraper — noticias de la sección Monterrey/NL.

Info7 publica un RSS feed y una sección web. Intentamos RSS primero;
si falla, caemos a scraping HTML con selectolax.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import pytz
from selectolax.parser import HTMLParser

from src.scrapers.base import BaseScraper, RawArticle, build_client

_BASE = "https://www.info7.mx"
_RSS_URL = f"{_BASE}/rss/secciones/monterrey"
_HTML_URL = f"{_BASE}/monterrey/"
_CENTRAL_TZ = pytz.timezone("America/Chicago")

_ARTICLE_SELECTORS = ["article", ".noticia", ".nota", "li.item", ".card"]
_TITLE_SELECTORS = ["h2 a", "h3 a", "h1 a", ".titulo a", "a.title", "a[href]"]
_DATE_SELECTORS = ["time[datetime]", "time", ".fecha", ".date", "[datetime]"]
_SNIPPET_SELECTORS = [".resumen", ".summary", ".descripcion", "p"]


class Info7Scraper(BaseScraper):
    source_name = "Info7"

    async def fetch(self) -> list[RawArticle]:
        async with build_client() as client:
            articles = await self._fetch_rss(client)
            if not articles:
                self.log.info("rss_empty_falling_back_to_html")
                articles = await self._fetch_html(client)
        return articles

    # ── RSS path ─────────────────────────────────────────────

    async def _fetch_rss(self, client) -> list[RawArticle]:
        try:
            resp = await self._get(client, _RSS_URL)
            feed = feedparser.parse(resp.text)
            articles = []
            for entry in feed.entries:
                art = self._entry_to_article(entry)
                if art:
                    articles.append(art)
            return articles
        except Exception as exc:
            self.log.warning("rss_fetch_failed", error=str(exc))
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


# ── Shared HTML utilities (reused across scrapers) ────────────

def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _find_nodes(tree: HTMLParser, selectors: list[str]):
    for sel in selectors:
        nodes = tree.css(sel)
        if nodes:
            return nodes
    return []


def _title_and_url(node, base_url: str, selectors: list[str]) -> tuple[str, str]:
    for sel in selectors:
        el = node.css_first(sel)
        if el:
            title = el.text(strip=True)
            href = el.attributes.get("href", "")
            if title and href:
                return title, urljoin(base_url, href)
    return "", ""


def _parse_date_node(node, selectors: list[str]) -> Optional[datetime]:
    for sel in selectors:
        el = node.css_first(sel)
        if el:
            raw = el.attributes.get("datetime", "") or el.text(strip=True)
            dt = _try_parse_datetime(raw)
            if dt:
                return dt
    return None


def _snippet_text(node, selectors: list[str]) -> str:
    for sel in selectors:
        el = node.css_first(sel)
        if el:
            text = el.text(strip=True)
            if len(text) > 20:
                return text[:400]
    return ""


def _parse_feedparser_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        t = feedparser._parse_date(date_str)
        if t:
            dt = datetime(*t[:6], tzinfo=pytz.utc)
            return dt.astimezone(pytz.timezone("America/Chicago"))
    except Exception:
        pass
    return _try_parse_datetime(date_str)


def _try_parse_datetime(raw: str) -> Optional[datetime]:
    central = pytz.timezone("America/Chicago")
    raw = raw.strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = central.localize(dt)
        return dt
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S", "%d %b %Y %H:%M"):
        try:
            dt = datetime.strptime(raw[:25], fmt)
            if dt.tzinfo is None:
                dt = central.localize(dt)
            return dt
        except ValueError:
            continue
    return None
