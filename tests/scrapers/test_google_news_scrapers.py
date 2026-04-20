"""Tests for proteccion_civil.py and bomberos_nl.py — Google News RSS scrapers."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from src.scrapers.proteccion_civil import ProteccionCivilScraper
from src.scrapers.bomberos_nl import BomberosNLScraper
from src.scrapers.base import RawArticle
from tests.scrapers.fixtures import GNEWS_RSS

_GNEWS_BASE = "https://news.google.com/rss/search"


def _gnews_url(query: str, max_age_hours: int = 3) -> str:
    from urllib.parse import quote_plus
    full_query = f"{query} when:{max_age_hours}h"
    return f"{_GNEWS_BASE}?q={quote_plus(full_query)}&hl=es-419&gl=MX&ceid=MX:es-419"


_PC_URL = _gnews_url("Protección Civil Nuevo León")
_BOM_URL = _gnews_url("Bomberos Nuevo León Monterrey")


class TestProteccionCivilScraper:
    @pytest.mark.asyncio
    async def test_fetch_returns_articles(self, httpx_mock):
        httpx_mock.add_response(url=_PC_URL, text=GNEWS_RSS)

        scraper = ProteccionCivilScraper()
        results = await scraper.fetch()
        assert isinstance(results, list)
        assert all(isinstance(a, RawArticle) for a in results)

    @pytest.mark.asyncio
    async def test_filters_old_articles(self, httpx_mock):
        """Stale articles in feed are filtered by _filter_fresh() via _timed_fetch()."""
        httpx_mock.add_response(url=_PC_URL, text=GNEWS_RSS)

        scraper = ProteccionCivilScraper(max_age_hours=3)
        results, _ = await scraper._timed_fetch()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
        for art in results:
            assert art.published_at >= cutoff

    @pytest.mark.asyncio
    async def test_failure_returns_empty_not_exception(self, httpx_mock):
        import httpx as _httpx
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_PC_URL)

        scraper = ProteccionCivilScraper()
        results = await scraper.fetch()
        assert results == []

    @pytest.mark.asyncio
    async def test_articles_have_timezone_aware_dates(self, httpx_mock):
        httpx_mock.add_response(url=_PC_URL, text=GNEWS_RSS)

        scraper = ProteccionCivilScraper()
        results = await scraper.fetch()
        for art in results:
            assert art.published_at.tzinfo is not None


class TestBomberosNLScraper:
    @pytest.mark.asyncio
    async def test_fetch_returns_articles(self, httpx_mock):
        httpx_mock.add_response(url=_BOM_URL, text=GNEWS_RSS)

        scraper = BomberosNLScraper()
        results = await scraper.fetch()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_failure_returns_empty(self, httpx_mock):
        import httpx as _httpx
        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_BOM_URL)

        scraper = BomberosNLScraper()
        results = await scraper.fetch()
        assert results == []

    @pytest.mark.asyncio
    async def test_source_name_contains_outlet(self, httpx_mock):
        httpx_mock.add_response(url=_BOM_URL, text=GNEWS_RSS)

        scraper = BomberosNLScraper()
        results = await scraper.fetch()
        for art in results:
            assert "·" in art.source_name


class TestScrapersIndependence:
    """Verify scrapers don't share state and failures are isolated."""

    @pytest.mark.asyncio
    async def test_each_scraper_independent(self, httpx_mock):
        import httpx as _httpx

        httpx_mock.add_exception(_httpx.ConnectError("down"), url=_PC_URL)
        httpx_mock.add_response(url=_BOM_URL, text=GNEWS_RSS)

        pc = ProteccionCivilScraper()
        bom = BomberosNLScraper()

        pc_results = await pc.fetch()
        bom_results = await bom.fetch()

        assert pc_results == []
        assert isinstance(bom_results, list)
