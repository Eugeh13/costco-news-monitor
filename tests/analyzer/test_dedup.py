"""Tests for src/analyzer/dedup.py — edge cases for semantic dedup."""
import pytest

from src.analyzer.dedup import _normalize, is_duplicate, reset_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure each test starts with a clean cache."""
    reset_cache()
    yield
    reset_cache()


# ── _normalize ────────────────────────────────────────────────────────────────

def test_normalize_lowercases():
    assert _normalize("INCENDIO EN CARRETERA NACIONAL") == _normalize("incendio en carretera nacional")


def test_normalize_removes_stopwords():
    result = _normalize("el incendio en la bodega")
    assert "el" not in result.split()
    assert "la" not in result.split()
    assert "en" not in result.split()


def test_normalize_removes_punctuation():
    result = _normalize("¡Balacera! en Av. Constitución (Monterrey)")
    assert "!" not in result
    assert "(" not in result
    assert "." not in result


def test_normalize_order_independent():
    a = _normalize("incendio bodega nacional")
    b = _normalize("bodega nacional incendio")
    assert a == b


def test_normalize_strips_common_suffixes():
    # "incendiando" → strip "ando" → "incendi"
    result = _normalize("incendiando")
    assert "ando" not in result


# ── is_duplicate ──────────────────────────────────────────────────────────────

def test_first_occurrence_not_duplicate():
    assert is_duplicate("Incendio en Carretera Nacional", "https://example.com/1") is False


def test_second_occurrence_is_duplicate():
    is_duplicate("Incendio en Carretera Nacional", "https://example.com/1")
    assert is_duplicate("Incendio en Carretera Nacional", "https://example.com/1") is True


def test_different_url_same_title_not_duplicate():
    is_duplicate("Balacera en Cumbres", "https://example.com/a")
    # Different URL → different hash → not duplicate
    assert is_duplicate("Balacera en Cumbres", "https://example.com/b") is False


def test_same_url_different_title_not_duplicate():
    url = "https://example.com/shared"
    is_duplicate("Accidente en Constitución", url)
    assert is_duplicate("Incendio en Carretera Nacional", url) is False


def test_semantic_equivalence_word_order():
    is_duplicate("incendio bodega carretera", "")
    # Word-order variation should hash the same
    assert is_duplicate("carretera bodega incendio", "") is True


def test_semantic_equivalence_stopwords():
    is_duplicate("el incendio en la bodega nacional", "")
    assert is_duplicate("incendio bodega nacional", "") is True


def test_empty_title_not_duplicate_then_duplicate():
    assert is_duplicate("", "") is False
    assert is_duplicate("", "") is True


def test_reset_cache_clears_state():
    is_duplicate("Bloqueo en Gonzalitos", "")
    reset_cache()
    assert is_duplicate("Bloqueo en Gonzalitos", "") is False


def test_different_incidents_are_independent():
    assert is_duplicate("Accidente vial", "") is False
    assert is_duplicate("Incendio en bodega", "") is False
    # First ones register but don't conflict with each other
    assert is_duplicate("Accidente vial", "") is True
    assert is_duplicate("Incendio en bodega", "") is True


def test_unicode_normalisation():
    # Accented vs un-accented should still be different (we don't strip accents)
    is_duplicate("inundación en san pedro", "")
    assert is_duplicate("inundacion en san pedro", "") is False
