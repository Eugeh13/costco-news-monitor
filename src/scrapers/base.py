"""
Base scraper infrastructure: RawArticle model, BaseScraper ABC, shared HTTP client.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog
from pydantic import BaseModel, field_validator
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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

# Read NEWS_MAX_AGE_HOURS directly from env at import time so tests don't need
# the full Settings initialisation (which requires database_url, api keys, etc.)
_ENV_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "3"))


class RawArticle(BaseModel):
    title: str
    url: str
    source_name: str
    published_at: Optional[datetime] = None  # None = date unknown; must be tz-aware if set
    content_snippet: str = ""
    raw_html: Optional[str] = None

    @field_validator("published_at")
    @classmethod
    def must_be_timezone_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return None
        if v.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return v


def build_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=_DEFAULT_HEADERS,
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
    )


class BaseScraper(ABC):
    """Abstract base for all scrapers. Each subclass targets one news source."""

    def __init__(self, max_age_hours: int | None = None) -> None:
        self.log = structlog.get_logger().bind(scraper=self.source_name)
        self.max_age_hours: int = max_age_hours if max_age_hours is not None else _ENV_MAX_AGE_HOURS

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self) -> list[RawArticle]: ...

    # ── Freshness filter ──────────────────────────────────────

    def _is_fresh(self, article: RawArticle) -> bool:
        """Return True if article is within max_age_hours. Logs stale/missing dates."""
        if article.published_at is None:
            self.log.warning("article.no_date", url=str(article.url))
            return False
        age_hours = (
            datetime.now(timezone.utc) - article.published_at
        ).total_seconds() / 3600
        if age_hours > self.max_age_hours:
            self.log.warning(
                "article.stale",
                age_hours=round(age_hours, 1),
                url=str(article.url),
            )
            return False
        return True

    def _filter_fresh(self, articles: list[RawArticle]) -> list[RawArticle]:
        fresh = [a for a in articles if self._is_fresh(a)]
        stale_count = len(articles) - len(fresh)
        if stale_count:
            self.log.info(
                "freshness_filter",
                total=len(articles),
                fresh=len(fresh),
                stale=stale_count,
                max_age_hours=self.max_age_hours,
            )
        return fresh

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
        """Runs fetch(), applies freshness filter, logs metrics."""
        t0 = time.monotonic()
        articles = await self.fetch()
        articles = self._filter_fresh(articles)
        elapsed = time.monotonic() - t0
        self.log.info(
            "fetch_complete",
            count=len(articles),
            elapsed_s=round(elapsed, 2),
        )
        return articles, elapsed
