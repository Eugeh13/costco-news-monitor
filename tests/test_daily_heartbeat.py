"""
Tests del heartbeat diario (M1): un solo reporte de estado al día en vez de
un resumen por ciclo.

Sin red: notifier mockeado, marcador persistente en tmp_path, y el pipeline
con stubs para verificar que run_once devuelve métricas y ya no envía
resúmenes por ciclo.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

import scheduler
from app.config.settings import settings
from app.domain.models import NewsItem
from app.services.content_hasher import ContentHasher
from app.services.pipeline import MonitoringPipeline


# ── Helpers ──────────────────────────────────────────────────


def _ahora(hora: int, dia: int = 15) -> datetime:
    return datetime(2026, 6, dia, hora, 30)


def _acc(cycles: int = 3, new: int = 7, alerts: int = 1) -> dict:
    return {"cycles": cycles, "new": new, "alerts": alerts}


@pytest.fixture
def marcador_en_tmp(tmp_path, monkeypatch):
    """Redirige el directorio de datos a tmp_path y devuelve la ruta del
    marcador del heartbeat."""
    monkeypatch.setattr(
        settings, "processed_news_file", str(tmp_path / "processed_news.txt")
    )
    return tmp_path / "daily_heartbeat_sent.txt"


def _pipeline_stub(notifier) -> MonitoringPipeline:
    """Pipeline con una fuente de 1 noticia y triage sin candidatas."""
    source = MagicMock()
    source.source_name.return_value = "stub"
    source.collect.return_value = [NewsItem(titulo="noticia de prueba", url="u1")]
    triage = MagicMock()
    triage.triage.return_value = []
    storage = MagicMock()
    storage.is_processed.return_value = False
    return MonitoringPipeline(
        sources=[source],
        triage=triage,
        deep=MagicMock(),
        notifier=notifier,
        repository=None,
        file_storage=storage,
        hasher=ContentHasher(),
        max_age_hours=999999,
    )


# ── Pipeline: métricas por ciclo, sin resumen a Telegram ─────


def test_run_once_devuelve_stats_y_no_envia_summary():
    notifier = MagicMock()
    pipeline = _pipeline_stub(notifier)

    stats = pipeline.run_once()

    assert stats == {"collected": 1, "recent": 1, "new": 1, "alerts": 0}
    notifier.send_summary.assert_not_called()


def test_run_once_sin_cambios_de_hash_tambien_devuelve_stats():
    notifier = MagicMock()
    pipeline = _pipeline_stub(notifier)
    pipeline.run_once()

    stats = pipeline.run_once()  # mismo contenido → hash sin cambios

    assert stats["collected"] == 1 and stats["new"] == 0
    notifier.send_summary.assert_not_called()


# ── Marcador persistente ─────────────────────────────────────


def test_heartbeat_marcador_roundtrip(marcador_en_tmp):
    assert not scheduler._heartbeat_already_sent("2026-06-15")
    scheduler._mark_heartbeat_sent("2026-06-15")
    assert scheduler._heartbeat_already_sent("2026-06-15")
    assert marcador_en_tmp.read_text(encoding="utf-8").strip() == "2026-06-15"
    # Día nuevo → el marcador de ayer no bloquea
    assert not scheduler._heartbeat_already_sent("2026-06-16")


# ── Condiciones de disparo ───────────────────────────────────


def test_heartbeat_no_corre_antes_de_la_hora(marcador_en_tmp):
    notifier = MagicMock()
    pipeline = MagicMock(_notifier=notifier)
    scheduler._maybe_send_daily_heartbeat(pipeline, _acc(), _ahora(hora=7))
    notifier.send_summary.assert_not_called()


def test_heartbeat_deshabilitado_por_flag(marcador_en_tmp, monkeypatch):
    monkeypatch.setattr(settings, "daily_heartbeat_enabled", False)
    notifier = MagicMock()
    pipeline = MagicMock(_notifier=notifier)
    scheduler._maybe_send_daily_heartbeat(pipeline, _acc(), _ahora(hora=10))
    notifier.send_summary.assert_not_called()


def test_heartbeat_envia_marca_y_resetea_acumulador(marcador_en_tmp):
    notifier = MagicMock()
    notifier.send_summary.return_value = True
    pipeline = MagicMock(_notifier=notifier)
    acc = _acc(cycles=12, new=34, alerts=2)

    scheduler._maybe_send_daily_heartbeat(pipeline, acc, _ahora(hora=8))

    stats = notifier.send_summary.call_args[0][0]
    assert stats["cycles"] == 12
    assert stats["news_analyzed"] == 34
    assert stats["alerts_sent"] == 2
    assert scheduler._heartbeat_already_sent("2026-06-15")
    assert acc == {"cycles": 0, "new": 0, "alerts": 0}


def test_heartbeat_no_reenvia_el_mismo_dia(marcador_en_tmp):
    notifier = MagicMock()
    notifier.send_summary.return_value = True
    pipeline = MagicMock(_notifier=notifier)

    scheduler._maybe_send_daily_heartbeat(pipeline, _acc(), _ahora(hora=8))
    scheduler._maybe_send_daily_heartbeat(pipeline, _acc(), _ahora(hora=14))

    assert notifier.send_summary.call_count == 1


def test_heartbeat_envio_fallido_no_marca_ni_resetea(marcador_en_tmp):
    notifier = MagicMock()
    notifier.send_summary.return_value = False  # Telegram caído
    pipeline = MagicMock(_notifier=notifier)
    acc = _acc(cycles=5, new=9, alerts=0)

    scheduler._maybe_send_daily_heartbeat(pipeline, acc, _ahora(hora=9))

    assert not scheduler._heartbeat_already_sent("2026-06-15")
    assert acc == {"cycles": 5, "new": 9, "alerts": 0}  # reintenta con todo

    # Siguiente ciclo: Telegram se recupera → ahora sí marca y resetea
    notifier.send_summary.return_value = True
    scheduler._maybe_send_daily_heartbeat(pipeline, acc, _ahora(hora=9))
    assert scheduler._heartbeat_already_sent("2026-06-15")
    assert acc == {"cycles": 0, "new": 0, "alerts": 0}


def test_heartbeat_nunca_propaga_excepciones(marcador_en_tmp):
    notifier = MagicMock()
    notifier.send_summary.side_effect = RuntimeError("boom")
    pipeline = MagicMock(_notifier=notifier)
    # No debe lanzar (el loop del worker no puede morir por el heartbeat)
    scheduler._maybe_send_daily_heartbeat(pipeline, _acc(), _ahora(hora=10))
    assert not scheduler._heartbeat_already_sent("2026-06-15")
