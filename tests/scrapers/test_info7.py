"""Tests for src/scrapers/info7.py."""

from __future__ import annotations

import pytest

from src.scrapers.info7 import Info7Scraper
from src.scrapers.base import RawArticle
from tests.scrapers.fixtures import INFO7_RSS, INFO7_HTML

_RSS_URL = "https://www.info7.mx/rss/secciones/monterrey"
_HTML_URL = "https://www.info7.mx/monterrey/"


class TestInfo7RSSPath:
    @pytest.mark.asyncio
    async def test_fetch_from_rss(self, httpx_mock):
        httpx_mock.add_response(url=_RSS_URL, text=INFO7_RSS, headers={"content-type": "application/rss+xml"})

        scraper = Info7Scraper()
        results = await scraper.fetch()
        assert len(results) == 2
        assert all(isinstance(a, RawArticle) for a in results)
        assert all(a.source_name == "Info7" for a in results)
        assert all(a.published_at.tzinfo is not None for a in results)

    @pytest.mark.asyncio
    async def test_rss_titles_correct(self, httpx_mock):
        httpx_mock.add_response(url=_RSS_URL, text=INFO7_RSS)

        scraper = Info7Scraper()
        results = await scraper.fetch()
        titles = [a.title for a in results]
        assert any("Accidente vial" in t for t in titles)
        assert any("Balacera" in t for t in titles)


class TestInfo7HTMLFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_html_when_rss_empty(self, httpx_mock):
        httpx_mock.add_response(url=_RSS_URL, text="<rss><channel></channel></rss>")
        httpx_mock.add_response(url=_HTML_URL, text=INFO7_HTML)

        scraper = Info7Scraper()
        results = await scraper.fetch()
        assert len(results) >= 1
        assert any("Inundación" in a.title for a in results)

    @pytest.mark.asyncio
    async def test_falls_back_to_html_when_rss_fails(self, httpx_mock):
        import httpx as _httpx
        httpx_mock.add_exception(_httpx.ConnectError("rss down"), url=_RSS_URL)
        httpx_mock.add_exception(_httpx.ConnectError("rss down"), url=_RSS_URL)
        httpx_mock.add_exception(_httpx.ConnectError("rss down"), url=_RSS_URL)
        httpx_mock.add_response(url=_HTML_URL, text=INFO7_HTML)

        scraper = Info7Scraper()
        results = await scraper.fetch()
        assert isinstance(results, list)


class TestInfo7Resilience:
    @pytest.mark.asyncio
    async def test_both_sources_fail_returns_empty(self, httpx_mock):
        import httpx as _httpx
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_RSS_URL)
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_RSS_URL)
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_RSS_URL)
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_HTML_URL)
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_HTML_URL)
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_HTML_URL)

        scraper = Info7Scraper()
        results = await scraper.fetch()
        assert results == []
