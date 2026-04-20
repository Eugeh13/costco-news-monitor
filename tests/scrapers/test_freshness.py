"""Tests for T1.5 freshness filter and T1.6 Google News when: parameter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import unquote_plus

import pytest

from src.scrapers.base import BaseScraper, RawArticle


# ── Concrete scraper for testing ──────────────────────────────

class _FakeScraper(BaseScraper):
    source_name = "FakeScraper"

    async def fetch(self) -> list[RawArticle]:
        return []


# ── _is_fresh ─────────────────────────────────────────────────

class TestIsFresh:
    def test_rejects_stale_article(self):
        scraper = _FakeScraper(max_age_hours=3)
        art = RawArticle(
            title="Old news",
            url="https://example.com/old",
            source_name="Test",
            published_at=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        assert scraper._is_fresh(art) is False

    def test_rejects_article_with_no_date(self):
        scraper = _FakeScraper(max_age_hours=3)
        art = RawArticle(
            title="No date",
            url="https://example.com/nodate",
            source_name="Test",
            published_at=None,
        )
        assert scraper._is_fresh(art) is False

    def test_accepts_fresh_article(self):
        scraper = _FakeScraper(max_age_hours=3)
        art = RawArticle(
            title="Recent news",
            url="https://example.com/recent",
            source_name="Test",
            published_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert scraper._is_fresh(art) is True

    def test_boundary_exactly_at_max_age_is_fresh(self):
        scraper = _FakeScraper(max_age_hours=3)
        art = RawArticle(
            title="Boundary",
            url="https://example.com/boundary",
            source_name="Test",
            published_at=datetime.now(timezone.utc) - timedelta(hours=3, seconds=-1),
        )
        assert scraper._is_fresh(art) is True


# ── T1.6 — Google News when: parameter ───────────────────────

class TestGoogleNewsWhenParam:
    @pytest.mark.asyncio
    async def test_query_includes_when_hours(self, httpx_mock):
        from src.scrapers._google_news_rss import fetch_google_news
        from src.scrapers.base import build_client
        import structlog

        httpx_mock.add_response(status_code=200, text="<?xml version='1.0'?><rss><channel></channel></rss>")

        log = structlog.get_logger()
        async with build_client() as client:
            await fetch_google_news(client, "Protección Civil Nuevo León", "Test", log, max_age_hours=3)

        request = httpx_mock.get_request()
        decoded_url = unquote_plus(str(request.url))
        assert "when:3h" in decoded_url

    @pytest.mark.asyncio
    async def test_custom_max_age_reflected_in_url(self, httpx_mock):
        from src.scrapers._google_news_rss import fetch_google_news
        from src.scrapers.base import build_client
        import structlog

        httpx_mock.add_response(status_code=200, text="<?xml version='1.0'?><rss><channel></channel></rss>")

        log = structlog.get_logger()
        async with build_client() as client:
            await fetch_google_news(client, "Bomberos NL", "Test", log, max_age_hours=6)

        request = httpx_mock.get_request()
        decoded_url = unquote_plus(str(request.url))
        assert "when:6h" in decoded_url
        assert "when:3h" not in decoded_url
