"""
Triage service — batch classification of news articles.

Orchestrates the AI provider for batch triage, handling chunking and
re-indexing of large batches.
"""

from __future__ import annotations

from app.domain.models import NewsItem, TriageResult
from app.domain.ports import AIProvider


class TriageService:
    """Runs batch triage on news items using an AI provider."""

    def __init__(self, ai: AIProvider, chunk_size: int = 25) -> None:
        self._ai = ai
        self._chunk_size = chunk_size

    def triage(self, news: list[NewsItem]) -> list[tuple[NewsItem, TriageResult]]:
        """
        Triage a list of news items in batches.

        Returns:
            List of (news_item, triage_result) tuples for CANDIDATES only.
        """
        batch = [item.to_dict() for item in news]
        all_results: list[TriageResult] = []

        # Process in chunks to avoid prompt truncation
        for chunk_start in range(0, len(batch), self._chunk_size):
            chunk = batch[chunk_start : chunk_start + self._chunk_size]

            chunk_results = self._ai.batch_triage(chunk)

            # Restore global index
            for result in chunk_results:
                result.index = chunk_start + result.index
                all_results.append(result)

        # Filter to candidates only
        candidates = []
        for triage in all_results:
            if triage.is_candidate and triage.index < len(news):
                candidates.append((news[triage.index], triage))

        return candidates
