"""Tests for src/scrapers/horizonte.py."""

from __future__ import annotations

import pytest

from src.scrapers.horizonte import HorizonteScraper
from src.scrapers.base import RawArticle
from tests.scrapers.fixtures import HORIZONTE_RSS, HORIZONTE_HTML

_RSS_URL = "https://www.elhorizonte.mx/rss/portada"
_RSS_CANDIDATES = [
    "https://www.elhorizonte.mx/rss/portada",
    "https://www.elhorizonte.mx/feed",
    "https://www.elhorizonte.mx/rss",
]
_HTML_URL = "https://www.elhorizonte.mx/nuevo-leon/"


class TestHorizonteRSSPath:
    @pytest.mark.asyncio
    async def test_fetch_from_rss(self, httpx_mock):
        httpx_mock.add_response(url=_RSS_URL, text=HORIZONTE_RSS)

        scraper = HorizonteScraper()
        results = await scraper.fetch()
        assert len(results) == 1
        assert isinstance(results[0], RawArticle)
        assert results[0].source_name == "El Horizonte"
        assert results[0].published_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_rss_title_correct(self, httpx_mock):
        httpx_mock.add_response(url=_RSS_URL, text=HORIZONTE_RSS)

        scraper = HorizonteScraper()
        results = await scraper.fetch()
        assert "Valle Oriente" in results[0].title


class TestHorizonteHTMLFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_html_when_all_rss_empty(self, httpx_mock):
        for url in _RSS_CANDIDATES:
            httpx_mock.add_response(url=url, text="<rss><channel></channel></rss>")
        httpx_mock.add_response(url=_HTML_URL, text=HORIZONTE_HTML)

        scraper = HorizonteScraper()
        results = await scraper.fetch()
        assert len(results) >= 1
        assert any("Bloqueo" in a.title for a in results)


class TestHorizonteResilience:
    @pytest.mark.asyncio
    async def test_complete_failure_returns_empty(self, httpx_mock):
        import httpx as _httpx
        for url in _RSS_CANDIDATES:
            for _ in range(3):
                httpx_mock.add_exception(_httpx.ConnectError("down"), url=url)
        for _ in range(3):
            httpx_mock.add_exception(_httpx.ConnectError("down"), url=_HTML_URL)

        scraper = HorizonteScraper()
        results = await scraper.fetch()
        assert results == []
