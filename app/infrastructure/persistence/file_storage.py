"""
File-based duplicate checker — simple URL-based dedup using a local file.

Lightweight alternative to DB dedup for environments without PostgreSQL.
"""

from __future__ import annotations

import os

from app.domain.ports import DuplicateChecker


class FileStorage(DuplicateChecker):
    """File-based duplicate URL tracker."""

    def __init__(self, filepath: str) -> None:
        self._filepath = filepath
        self._processed: set[str] = self._load()

    def is_processed(self, url: str) -> bool:
        return url in self._processed

    def mark_processed(self, url: str) -> None:
        if url and url not in self._processed:
            self._processed.add(url)
            try:
                with open(self._filepath, "a", encoding="utf-8") as f:
                    f.write(f"{url}\n")
            except Exception as e:
                print(f"  ⚠️ File storage write error: {e}")

    def cleanup(self, max_entries: int = 1000) -> None:
        """Keep only the most recent entries."""
        if len(self._processed) <= max_entries:
            return
        recent = list(self._processed)[-max_entries:]
        self._processed = set(recent)
        try:
            with open(self._filepath, "w", encoding="utf-8") as f:
                for url in recent:
                    f.write(f"{url}\n")
        except Exception as e:
            print(f"  ⚠️ File cleanup error: {e}")

    # ── Private ──────────────────────────────────────────────

    def _load(self) -> set[str]:
        if not os.path.exists(self._filepath):
            return set()
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if line.strip()}
        except Exception:
            return set()
