"""
Tests de run_watchdog (server.py — Fase 2), sin refactorizar el server.

run_watchdog es un loop infinito que duerme 120 s, consulta heartbeat.check()
y llama os._exit(1) tras DOS chequeos no saludables consecutivos. Para
probarlo sin matar pytest ni esperar minutos:

- time.sleep se parchea para contar iteraciones y cortar el loop con una
  excepción centinela cuando la secuencia de chequeos se agotó;
- heartbeat.check se parchea para devolver una secuencia predefinida;
- os._exit se parchea para registrar la llamada y cortar el loop (el real
  nunca regresa, así que el falso también debe interrumpir).
"""

from __future__ import annotations

import os
import time

import pytest

import server
from app.infrastructure import heartbeat

SANO = (True, "ok", "último ciclo: hace nada")
ENFERMO = (False, "sin_latido", "el worker no late")


class _SalidaForzada(Exception):
    """Sustituye a os._exit: registra la llamada y corta el loop."""


class _FinDelTest(Exception):
    """Corta el loop infinito cuando la secuencia de chequeos se agotó."""


def _preparar(monkeypatch, chequeos: list[tuple]) -> list[int]:
    """Parchea sleep/check/os._exit; devuelve la lista donde caen los exit codes."""
    exit_codes: list[int] = []
    dormidas = {"n": 0}
    secuencia = iter(chequeos)

    def sleep_falso(secs):
        assert secs == 120  # el intervalo del watchdog no debe cambiar
        dormidas["n"] += 1
        if dormidas["n"] > len(chequeos):
            raise _FinDelTest()

    def exit_falso(code):
        exit_codes.append(code)
        raise _SalidaForzada()

    monkeypatch.setattr(time, "sleep", sleep_falso)
    monkeypatch.setattr(heartbeat, "check", lambda: next(secuencia))
    monkeypatch.setattr(os, "_exit", exit_falso)
    return exit_codes


# ============================================================
# Dos fallos consecutivos → exit(1)
# ============================================================

def test_dos_fallos_consecutivos_terminan_el_proceso(monkeypatch):
    exit_codes = _preparar(monkeypatch, [ENFERMO, ENFERMO])
    with pytest.raises(_SalidaForzada):
        server.run_watchdog()
    assert exit_codes == [1]


def test_fallos_consecutivos_tras_recuperacion_tambien_salen(monkeypatch):
    # fallo → ok (resetea) → fallo → fallo: los DOS últimos sí disparan exit
    exit_codes = _preparar(monkeypatch, [ENFERMO, SANO, ENFERMO, ENFERMO])
    with pytest.raises(_SalidaForzada):
        server.run_watchdog()
    assert exit_codes == [1]


# ============================================================
# Fallo aislado → NO exit (el contador se resetea con un chequeo sano)
# ============================================================

def test_fallo_aislado_no_termina_el_proceso(monkeypatch):
    exit_codes = _preparar(monkeypatch, [ENFERMO, SANO, SANO])
    with pytest.raises(_FinDelTest):
        server.run_watchdog()
    assert exit_codes == []


def test_fallos_alternados_nunca_salen(monkeypatch):
    # Nunca hay dos fallos SEGUIDOS: el reset del contador debe evitar el exit
    exit_codes = _preparar(monkeypatch, [ENFERMO, SANO, ENFERMO, SANO])
    with pytest.raises(_FinDelTest):
        server.run_watchdog()
    assert exit_codes == []


def test_todo_sano_nunca_sale(monkeypatch):
    exit_codes = _preparar(monkeypatch, [SANO, SANO, SANO])
    with pytest.raises(_FinDelTest):
        server.run_watchdog()
    assert exit_codes == []
