"""
Tests del heartbeat del worker (app/infrastructure/heartbeat.py — Fase 2).

Cubre la máquina de estados de check():
- "starting": dentro de la gracia de arranque, sin ciclos completados.
- "sin_latido": tras la gracia sin latido (con y sin register_worker).
- "ok": latido fresco dentro de la tolerancia.
- "atrasado": latido más viejo que sueño planeado + 3x max_poll_interval.
- record_error() aparece en el detail de los estados no saludables.

El módulo guarda estado en variables globales: cada test las resetea vía
monkeypatch.setattr sobre app.infrastructure.heartbeat (se restauran solas
al terminar). Nada toca red ni BD.
"""

from __future__ import annotations

import time

import pytest

from app.config.settings import settings
from app.infrastructure import heartbeat


def _margen_secs() -> float:
    """Misma fórmula que check(): 3x el intervalo máximo configurado."""
    return 3 * settings.max_poll_interval_minutes * 60


@pytest.fixture(autouse=True)
def _estado_limpio(monkeypatch):
    """Resetea las globales del módulo; monkeypatch las restaura al final."""
    monkeypatch.setattr(heartbeat, "_worker_registered", False)
    monkeypatch.setattr(heartbeat, "_last_beat", None)
    monkeypatch.setattr(heartbeat, "_planned_sleep_secs", 0.0)
    monkeypatch.setattr(heartbeat, "_last_error", None)
    monkeypatch.setattr(heartbeat, "_boot_time", time.time())


# ============================================================
# "starting" — gracia de arranque
# ============================================================

def test_starting_dentro_de_la_gracia_sin_register():
    healthy, status, detail = heartbeat.check()
    assert healthy is True
    assert status == "starting"
    assert "arrancando" in detail


def test_starting_dentro_de_la_gracia_con_register():
    # La gracia aplica igual aunque el hilo ya se haya registrado:
    # el primer ciclo puede tardar (triage IA, geocoding, etc.).
    heartbeat.register_worker()
    healthy, status, _ = heartbeat.check()
    assert healthy is True
    assert status == "starting"


# ============================================================
# "sin_latido" — tras la gracia, sin ciclos completados
# ============================================================

def test_sin_latido_tras_gracia_sin_register(monkeypatch):
    monkeypatch.setattr(
        heartbeat, "_boot_time", time.time() - heartbeat.STARTUP_GRACE_SECS - 1
    )
    healthy, status, detail = heartbeat.check()
    assert healthy is False
    assert status == "sin_latido"
    assert "nunca arrancó" in detail


def test_sin_latido_tras_gracia_con_register(monkeypatch):
    monkeypatch.setattr(
        heartbeat, "_boot_time", time.time() - heartbeat.STARTUP_GRACE_SECS - 1
    )
    heartbeat.register_worker()
    healthy, status, detail = heartbeat.check()
    assert healthy is False
    assert status == "sin_latido"
    assert "no ha completado ningún ciclo" in detail


# ============================================================
# "ok" — latido fresco
# ============================================================

def test_ok_con_latido_fresco():
    heartbeat.register_worker()
    heartbeat.beat(planned_sleep_secs=300)
    healthy, status, detail = heartbeat.check()
    assert healthy is True
    assert status == "ok"
    assert "último ciclo" in detail


def test_ok_aunque_pase_la_gracia_si_el_latido_es_fresco(monkeypatch):
    # Un latido fresco manda sobre la gracia ya vencida.
    monkeypatch.setattr(
        heartbeat, "_boot_time", time.time() - heartbeat.STARTUP_GRACE_SECS - 1
    )
    heartbeat.beat(planned_sleep_secs=60)
    healthy, status, _ = heartbeat.check()
    assert healthy is True
    assert status == "ok"


# ============================================================
# "atrasado" — latido más viejo que la tolerancia
# ============================================================

def test_atrasado_con_latido_viejo(monkeypatch):
    planned = 60.0
    # 5 s pasados de la tolerancia (sueño planeado + 3x intervalo máximo)
    elapsed = planned + _margen_secs() + 5
    monkeypatch.setattr(heartbeat, "_last_beat", time.time() - elapsed)
    monkeypatch.setattr(heartbeat, "_planned_sleep_secs", planned)
    healthy, status, detail = heartbeat.check()
    assert healthy is False
    assert status == "atrasado"
    assert "tolerancia" in detail


def test_tolerancia_es_sueno_planeado_mas_3x_intervalo_maximo(monkeypatch):
    """Justo dentro de la tolerancia → ok; justo fuera → atrasado."""
    planned = 120.0
    allowed = planned + _margen_secs()

    # 10 s ANTES del límite (colchón para el tiempo del propio test)
    monkeypatch.setattr(heartbeat, "_last_beat", time.time() - (allowed - 10))
    monkeypatch.setattr(heartbeat, "_planned_sleep_secs", planned)
    healthy, status, _ = heartbeat.check()
    assert (healthy, status) == (True, "ok")

    # 10 s DESPUÉS del límite
    monkeypatch.setattr(heartbeat, "_last_beat", time.time() - (allowed + 10))
    healthy, status, _ = heartbeat.check()
    assert (healthy, status) == (False, "atrasado")


def test_tolerancia_escala_con_max_poll_interval(monkeypatch):
    """El margen sale de settings: con 1 min de intervalo, 200 s ya es atrasado."""
    monkeypatch.setattr(settings, "max_poll_interval_minutes", 1)  # margen = 180 s
    monkeypatch.setattr(heartbeat, "_last_beat", time.time() - 200)
    monkeypatch.setattr(heartbeat, "_planned_sleep_secs", 0.0)
    healthy, status, _ = heartbeat.check()
    assert healthy is False
    assert status == "atrasado"


def test_sueno_nocturno_largo_no_marca_atrasado(monkeypatch):
    """La pausa nocturna duerme horas: la tolerancia respeta el sueño planeado."""
    planned = 6 * 3600.0  # 6 horas
    monkeypatch.setattr(heartbeat, "_last_beat", time.time() - 5 * 3600.0)
    monkeypatch.setattr(heartbeat, "_planned_sleep_secs", planned)
    healthy, status, _ = heartbeat.check()
    assert healthy is True
    assert status == "ok"


# ============================================================
# record_error — visible en el detail
# ============================================================

def test_record_error_aparece_en_detail_atrasado(monkeypatch):
    heartbeat.record_error("ValueError: explotó el geocoder")
    monkeypatch.setattr(
        heartbeat, "_last_beat", time.time() - (_margen_secs() + 100)
    )
    healthy, _, detail = heartbeat.check()
    assert healthy is False
    assert "último error: ValueError: explotó el geocoder" in detail


def test_record_error_aparece_en_detail_sin_latido(monkeypatch):
    heartbeat.record_error("timeout del triage")
    monkeypatch.setattr(
        heartbeat, "_boot_time", time.time() - heartbeat.STARTUP_GRACE_SECS - 1
    )
    healthy, status, detail = heartbeat.check()
    assert (healthy, status) == (False, "sin_latido")
    assert "último error: timeout del triage" in detail


def test_record_error_trunca_a_300_caracteres():
    heartbeat.record_error("x" * 500)
    assert heartbeat._last_error == "x" * 300


def test_beat_clampa_sueno_negativo_a_cero():
    heartbeat.beat(planned_sleep_secs=-50)
    assert heartbeat._planned_sleep_secs == 0.0
