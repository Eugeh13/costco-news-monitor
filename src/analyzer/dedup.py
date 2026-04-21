"""
Deduplication for incident articles — two layers:

  1. Fast hash dedup (in-memory, TTL 24 h): catches duplicates within a single
     pipeline run using semantic title normalisation + URL.
  2. DB dedup (async, cross-run): checks decision_log for the same canonical URL
     or normalised title in the last 24 hours, catching duplicates across runs.

Both layers run BEFORE any LLM call so we never pay to classify a duplicate.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from cachetools import TTLCache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_TRACKING_PARAMS: frozenset[str] = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "fbclid", "gclid", "msclkid", "ref", "_ga",
})

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


def _canonicalize_url(url: str) -> str:
    """Strip common tracking query params from a URL."""
    if not url:
        return url
    parsed = urlparse(url)
    qs = {
        k: v
        for k, v in parse_qs(parsed.query, keep_blank_values=True).items()
        if k not in _TRACKING_PARAMS
    }
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))


async def is_duplicate_db(
    title: str,
    url: str,
    session: AsyncSession,
    exclude_run_id: str | None = None,
) -> bool:
    """Return True if the same canonical URL or normalised title exists in decision_log
    within the last 24 hours.  Falls back gracefully when the table does not exist.

    Pass exclude_run_id to ignore entries from the current run (which are written
    before this check is called and would otherwise cause false positives).
    """
    since = datetime.now(UTC) - timedelta(hours=24)
    canonical = _canonicalize_url(url)
    norm_title = _normalize(title)

    try:
        # Fast path: exact canonical-URL match
        if canonical:
            base_sql = "SELECT COUNT(*) FROM decision_log WHERE article_url = :url AND created_at >= :since"
            params: dict = {"url": canonical, "since": since.isoformat()}
            if exclude_run_id:
                base_sql += " AND run_id != :run_id"
                params["run_id"] = exclude_run_id
            result = await session.execute(text(base_sql), params)
            if result.scalar_one() > 0:
                return True

        # Slower path: normalised-title match (Python-side comparison)
        title_sql = "SELECT article_title FROM decision_log WHERE created_at >= :since"
        title_params: dict = {"since": since.isoformat()}
        if exclude_run_id:
            title_sql += " AND run_id != :run_id"
            title_params["run_id"] = exclude_run_id
        rows = await session.execute(text(title_sql), title_params)
        for row in rows:
            if _normalize(row.article_title) == norm_title:
                return True

    except Exception:
        pass

    return False
