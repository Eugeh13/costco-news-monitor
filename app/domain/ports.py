"""
Domain ports — Abstract interfaces (contracts) that infrastructure must implement.

These are the "ports" in hexagonal architecture. The services layer depends
on these abstractions, NOT on concrete implementations. This allows swapping
out infrastructure (e.g., OpenAI → Anthropic) without touching business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models import (
    AnalysisResult,
    Alert,
    NewsItem,
    TriageResult,
)


class NewsSource(ABC):
    """Contract for a news collection source."""

    @abstractmethod
    def collect(self) -> list[NewsItem]:
        """Collect news items from this source."""
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for logging."""
        ...


class DeepReader(ABC):
    """Contract for extracting full article content from a URL."""

    @abstractmethod
    def extract(self, url: str) -> Optional[str]:
        """Extract full text from an article URL. Returns None on failure."""
        ...


class AIProvider(ABC):
    """Contract for AI inference (triage + deep analysis)."""

    @abstractmethod
    def batch_triage(self, articles: list[dict]) -> list[TriageResult]:
        """Triage a batch of articles. Returns classification for each."""
        ...

    @abstractmethod
    def deep_analyze(self, title: str, content: str) -> Optional[AnalysisResult]:
        """Deep analysis of a single article. Returns structured result."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """E.g., 'openai / gpt-5-mini'"""
        ...


class Notifier(ABC):
    """Contract for sending alerts to external channels."""

    @abstractmethod
    def send_alert(self, alert: Alert) -> bool:
        """Send a high-impact alert. Returns True on success."""
        ...

    @abstractmethod
    def send_summary(self, stats: dict) -> bool:
        """Send a monitoring summary. Returns True on success."""
        ...


class NewsRepository(ABC):
    """Contract for persisting and querying incidents."""

    @abstractmethod
    def save_incident(self, alert: Alert) -> Optional[int]:
        """Persist an alert as an incident. Returns the ID or None."""
        ...

    @abstractmethod
    def is_duplicate(self, titulo: str, url: str, fuente: str, max_hours: int = 24) -> bool:
        """Check if this article was already processed."""
        ...

    @abstractmethod
    def get_incidents(
        self,
        hours: int = 24,
        category: Optional[str] = None,
        costco: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query recent incidents with optional filters."""
        ...

    @abstractmethod
    def get_stats(self, hours: int = 24) -> dict:
        """Get aggregate statistics for the dashboard."""
        ...


class DuplicateChecker(ABC):
    """Contract for local (file-based) duplicate detection."""

    @abstractmethod
    def is_processed(self, url: str) -> bool:
        ...

    @abstractmethod
    def mark_processed(self, url: str) -> None:
        ...


class GeocodingService(ABC):
    """Contract for geocoding text locations to coordinates."""

    @abstractmethod
    def geocode(self, location_text: str) -> Optional[tuple[float, float]]:
        """Convert text location to (lat, lon). Returns None on failure."""
        ...
