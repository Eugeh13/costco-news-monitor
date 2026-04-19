"""Tests for src/scrapers/milenio.py."""

from __future__ import annotations

import pytest
import httpx

from src.scrapers.milenio import MilenioScraper
from src.scrapers.base import RawArticle
from tests.scrapers.fixtures import (
    MILENIO_HTML,
    MILENIO_HTML_CHANGED_STRUCTURE,
    MILENIO_HTML_EMPTY,
)

_SECTION_URLS = [
    "https://www.milenio.com/ultima-hora",
    "https://www.milenio.com/estados/nuevo-leon",
]


class TestMilenioScraperParsing:
    def test_parse_standard_html(self):
        scraper = MilenioScraper()
        results = scraper._parse(MILENIO_HTML, _SECTION_URLS[0])
        assert len(results) == 2
        titles = [r.title for r in results]
        assert any("Choque múltiple" in t for t in titles)
        assert any("Incendio" in t for t in titles)

    def test_articles_are_raw_article_instances(self):
        scraper = MilenioScraper()
        results = scraper._parse(MILENIO_HTML, _SECTION_URLS[0])
        for art in results:
            assert isinstance(art, RawArticle)
            assert art.source_name == "Milenio"
            assert art.published_at.tzinfo is not None  # timezone-aware

    def test_parse_changed_structure_does_not_raise(self):
        scraper = MilenioScraper()
        results = scraper._parse(MILENIO_HTML_CHANGED_STRUCTURE, _SECTION_URLS[0])
        # Either finds the article via fallback selectors or returns empty — no crash
        assert isinstance(results, list)

    def test_parse_empty_html_returns_empty_list(self):
        scraper = MilenioScraper()
        results = scraper._parse(MILENIO_HTML_EMPTY, _SECTION_URLS[0])
        assert results == []

    def test_urls_are_absolute(self):
        scraper = MilenioScraper()
        results = scraper._parse(MILENIO_HTML, _SECTION_URLS[0])
        for art in results:
            assert art.url.startswith("https://")

    def test_deduplication_across_sections(self, httpx_mock):
        """Same URL appearing in two sections should only appear once."""
        httpx_mock.add_response(url=_SECTION_URLS[0], text=MILENIO_HTML)
        httpx_mock.add_response(url=_SECTION_URLS[1], text=MILENIO_HTML)

        import asyncio
        scraper = MilenioScraper()
        results = asyncio.run(scraper.fetch())
        urls = [a.url for a in results]
        assert len(urls) == len(set(urls))


class TestMilenioScraperHTTP:
    @pytest.mark.asyncio
    async def test_fetch_returns_articles(self, httpx_mock):
        httpx_mock.add_response(url=_SECTION_URLS[0], text=MILENIO_HTML)
        httpx_mock.add_response(url=_SECTION_URLS[1], text=MILENIO_HTML_CHANGED_STRUCTURE)

        scraper = MilenioScraper()
        results = await scraper.fetch()
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_one_section_fails_other_still_fetched(self, httpx_mock):
        """If one section returns 500, the other should still work."""
        httpx_mock.add_response(url=_SECTION_URLS[0], status_code=500)
        httpx_mock.add_response(url=_SECTION_URLS[0], status_code=500)
        httpx_mock.add_response(url=_SECTION_URLS[0], status_code=500)
        httpx_mock.add_response(url=_SECTION_URLS[1], text=MILENIO_HTML)

        scraper = MilenioScraper()
        results = await scraper.fetch()
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_all_sections_fail_returns_empty_not_exception(self, httpx_mock):
        """Complete network failure should return [] not raise."""
        for url in _SECTION_URLS:
            for _ in range(3):
                httpx_mock.add_exception(httpx.ConnectError("down"), url=url)

        scraper = MilenioScraper()
        results = await scraper.fetch()
        assert results == []
