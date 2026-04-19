"""
Base scraper infrastructure: RawArticle model, BaseScraper ABC, shared HTTP client.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


class RawArticle(BaseModel):
    title: str
    url: str
    source_name: str
    published_at: datetime  # must be timezone-aware
    content_snippet: str = ""
    raw_html: Optional[str] = None


def build_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=_DEFAULT_HEADERS,
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
    )


class BaseScraper(ABC):
    """Abstract base for all scrapers. Each subclass targets one news source."""

    def __init__(self) -> None:
        self.log = structlog.get_logger().bind(scraper=self.source_name)

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self) -> list[RawArticle]: ...

    # ── Shared retry-enabled GET ──────────────────────────────

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _get(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response

    async def _timed_fetch(self) -> tuple[list[RawArticle], float]:
        """Runs fetch() and returns (articles, elapsed_seconds)."""
        t0 = time.monotonic()
        articles = await self.fetch()
        elapsed = time.monotonic() - t0
        self.log.info(
            "fetch_complete",
            count=len(articles),
            elapsed_s=round(elapsed, 2),
        )
        return articles, elapsed
