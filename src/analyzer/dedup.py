"""
Semantic deduplication for incident titles.

Strategy:
  1. Normalise: lowercase, strip non-alpha, remove stop-words, basic stem.
  2. Sort stems so word-order differences collapse to the same hash.
  3. SHA-256 of "<normalised_title>|<url>".
  4. TTL-cached in memory for 24 h using cachetools.TTLCache.
"""

from __future__ import annotations

import hashlib
import re
from cachetools import TTLCache

_STOPWORDS: frozenset[str] = frozenset({
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "y", "e", "o", "u", "de", "del", "al", "en", "a", "con",
    "por", "para", "que", "se", "no", "su", "sus", "lo", "le",
    "les", "esta", "este", "esto", "esa", "ese", "eso", "pero",
    "más", "ya", "ha", "han", "fue", "ser", "es", "era", "son",
    "hay", "como", "si", "porque", "cuando", "también", "sobre",
    "entre", "hasta", "desde", "sin", "según", "ante", "bajo",
    "hacia", "contra", "durante", "mediante", "nuevo", "nueva",
    # English (articles/prepositions often appear in bilingual sources)
    "the", "a", "an", "and", "or", "of", "in", "to", "for",
    "is", "was", "are", "were", "it", "at", "by", "on", "that",
    "this", "with", "from", "be", "as", "has", "had",
})

# Ordered: longest suffix first to avoid partial matches
_SUFFIXES: tuple[str, ...] = (
    "ación", "ción", "ando", "iendo", "mente", "ados", "idas",
    "ado", "ida", "ido", "es", "s",
)

# 24-hour in-memory cache, max 10 000 entries
_cache: TTLCache = TTLCache(maxsize=10_000, ttl=86_400)


def _normalize(title: str) -> str:
    """Normalise a title to a canonical stem bag (sorted, deduped)."""
    title = title.lower()
    # Keep Spanish letters plus ASCII letters/spaces; collapse everything else to space
    title = re.sub(r"[^a-záéíóúüñ\s]", " ", title)
    words = [w for w in title.split() if w not in _STOPWORDS and len(w) > 2]

    stems: list[str] = []
    for w in words:
        for suffix in _SUFFIXES:
            if w.endswith(suffix) and len(w) - len(suffix) > 2:
                w = w[: -len(suffix)]
                break
        stems.append(w)

    # Sort + deduplicate so synonym word-order variation hashes the same
    return " ".join(sorted(set(stems)))


def _semantic_hash(title: str, url: str) -> str:
    payload = f"{_normalize(title)}|{url or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_duplicate(title: str, url: str = "") -> bool:
    """
    Return True if this title+url combination was already seen within 24 h.
    Side effect: registers the entry on first call so subsequent calls return True.
    """
    key = _semantic_hash(title, url)
    if key in _cache:
        return True
    _cache[key] = True
    return False


def reset_cache() -> None:
    """Clear the dedup cache (test helper)."""
    _cache.clear()
