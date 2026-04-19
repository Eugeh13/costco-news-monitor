"""
Shared Google News RSS helper used by proteccion_civil and bomberos scrapers.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import feedparser
import pytz

from src.scrapers.base import RawArticle, build_client

_CENTRAL_TZ = pytz.timezone("America/Chicago")
_GNEWS_RSS = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=es-419&gl=MX&ceid=MX:es-419"
)


async def fetch_google_news(
    client,
    query: str,
    source_name: str,
    log,
) -> list[RawArticle]:
    url = _GNEWS_RSS.format(query=quote_plus(query))
    try:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("google_news_rss_failed", query=query, error=str(exc))
        return []

    feed = feedparser.parse(resp.text)
    articles: list[RawArticle] = []

    for entry in feed.entries:
        title = _clean_html(entry.get("title", "")).strip()
        url_item = entry.get("link", "").strip()
        if not title or not url_item:
            continue

        outlet = _extract_outlet(entry.get("title", ""))
        published_at = _parse_date(entry.get("published")) or datetime.now(_CENTRAL_TZ)
        snippet = _clean_html(entry.get("summary", ""))[:400]

        articles.append(RawArticle(
            title=title,
            url=url_item,
            source_name=f"{source_name} · {outlet}",
            published_at=published_at,
            content_snippet=snippet,
        ))

    return articles


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_outlet(full_title: str) -> str:
    """Google News titles end with ' - OutletName'."""
    if " - " in full_title:
        return full_title.rsplit(" - ", 1)[-1].strip()
    return "Google News"


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        t = feedparser._parse_date(date_str)
        if t:
            dt = datetime(*t[:6], tzinfo=pytz.utc)
            return dt.astimezone(_CENTRAL_TZ)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = _CENTRAL_TZ.localize(dt)
        return dt
    except ValueError:
        return None
