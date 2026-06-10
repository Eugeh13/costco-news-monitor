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
        # Lista en orden de inserción (para que cleanup conserve realmente
        # las más recientes) + set para lookups O(1).
        self._order: list[str] = self._load()
        self._processed: set[str] = set(self._order)

    def is_processed(self, url: str) -> bool:
        return url in self._processed

    def mark_processed(self, url: str) -> None:
        if url and url not in self._processed:
            self._processed.add(url)
            self._order.append(url)
            try:
                with open(self._filepath, "a", encoding="utf-8") as f:
                    f.write(f"{url}\n")
            except Exception as e:
                print(f"  ⚠️ File storage write error: {e}")

    def cleanup(self, max_entries: int = 1000) -> int:
        """Keep only the most recent entries. Returns how many were removed.

        M8: lo invoca el scheduler una vez al día; antes nunca se llamaba
        y el archivo crecía sin tope.
        """
        removed = len(self._order) - max_entries
        if removed <= 0:
            return 0

        self._order = self._order[-max_entries:]
        self._processed = set(self._order)
        try:
            with open(self._filepath, "w", encoding="utf-8") as f:
                for url in self._order:
                    f.write(f"{url}\n")
        except Exception as e:
            print(f"  ⚠️ File cleanup error: {e}")
        return removed

    # ── Private ──────────────────────────────────────────────

    def _load(self) -> list[str]:
        """Load URLs preserving file order (insertion order), deduplicated."""
        if not os.path.exists(self._filepath):
            return []
        try:
            seen: set[str] = set()
            order: list[str] = []
            with open(self._filepath, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url and url not in seen:
                        seen.add(url)
                        order.append(url)
            return order
        except Exception:
            return []
