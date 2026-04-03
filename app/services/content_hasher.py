"""
Content hasher — detects when news sources haven't changed between runs.

If the hash is identical, the pipeline can skip entirely (0 tokens consumed).
"""

from __future__ import annotations

import hashlib

from app.domain.models import NewsItem


class ContentHasher:
    """Tracks content changes across monitoring cycles."""

    def __init__(self) -> None:
        self._last_hash: str | None = None
        self.consecutive_no_change: int = 0

    def has_changed(self, news: list[NewsItem]) -> bool:
        """
        Check if the news batch differs from the last run.

        Returns:
            True if content changed (or first run), False if identical.
        """
        current_hash = self._compute(news)

        if self._last_hash is None:
            self._last_hash = current_hash
            self.consecutive_no_change = 0
            return True

        if current_hash == self._last_hash:
            self.consecutive_no_change += 1
            return False

        self._last_hash = current_hash
        self.consecutive_no_change = 0
        return True

    @staticmethod
    def _compute(news: list[NewsItem]) -> str:
        titles = sorted(item.titulo for item in news)
        content = "|".join(titles)
        return hashlib.md5(content.encode()).hexdigest()
