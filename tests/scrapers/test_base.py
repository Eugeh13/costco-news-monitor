"""Tests for src/scrapers/base.py."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.scrapers.base import RawArticle, BaseScraper, build_client


# ── RawArticle ────────────────────────────────────────────────

class TestRawArticle:
    def test_valid_creation(self):
        art = RawArticle(
            title="Test",
            url="https://example.com/news/1",
            source_name="TestSource",
            published_at=datetime.now(timezone.utc),
        )
        assert art.title == "Test"
        assert art.raw_html is None

    def test_requires_timezone_aware_datetime(self):
        with pytest.raises(Exception):
            # naive datetime should fail Pydantic validation
            RawArticle(
                title="Test",
                url="https://example.com/news/2",
                source_name="TestSource",
                published_at=datetime(2025, 10, 28, 18, 0, 0),  # naive
            )

    def test_optional_raw_html(self):
        art = RawArticle(
            title="Test",
            url="https://example.com/news/3",
            source_name="TestSource",
            published_at=datetime.now(timezone.utc),
            raw_html="<html></html>",
        )
        assert art.raw_html == "<html></html>"


# ── build_client ──────────────────────────────────────────────

class TestBuildClient:
    @pytest.mark.asyncio
    async def test_returns_async_client(self):
        client = build_client()
        assert isinstance(client, httpx.AsyncClient)
        await client.aclose()

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        client = build_client(timeout=10.0)
        assert client.timeout.read == 10.0
        await client.aclose()


# ── BaseScraper retry ─────────────────────────────────────────

class ConcreteTestScraper(BaseScraper):
    source_name = "TestScraper"

    async def fetch(self):
        return []


class TestBaseScraperRetry:
    @pytest.mark.asyncio
    async def test_retry_on_request_error(self, httpx_mock):
        """Should retry 3 times on network error then reraise."""
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))

        scraper = ConcreteTestScraper()
        async with build_client() as client:
            with pytest.raises(httpx.ConnectError):
                await scraper._get(client, "https://example.com/test")

    @pytest.mark.asyncio
    async def test_succeeds_after_one_retry(self, httpx_mock):
        """Should succeed on second attempt after one failure."""
        httpx_mock.add_exception(httpx.ConnectError("temporary failure"))
        httpx_mock.add_response(status_code=200, text="OK")

        scraper = ConcreteTestScraper()
        async with build_client() as client:
            resp = await scraper._get(client, "https://example.com/test")
        assert resp.status_code == 200
