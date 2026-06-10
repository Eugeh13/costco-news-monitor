"""
Heartbeat del worker — estado compartido entre el scheduler y /health.

El worker corre en un hilo daemon dentro del mismo proceso que FastAPI
(ver server.py). Si ese hilo muere, el proceso sigue vivo y Railway no
reinicia nada. Este módulo cierra ese hueco:

- El scheduler registra un latido (`beat`) al terminar cada ciclo, junto
  con cuánto planea dormir hasta el siguiente.
- /health consulta `check()`: si el último ciclo terminó hace más del
  sueño planeado + 3x el intervalo máximo configurado, el worker está
  muerto o atorado → 503 para que Railway reinicie el contenedor.
- Durante los primeros minutos tras el boot se responde "starting" (200)
  para no matar el contenedor antes de que el worker complete su primer
  ciclo (el primer ciclo puede tardar: triage IA, geocoding, etc.).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

from app.config.settings import settings

# Margen de arranque: minutos tras el boot durante los cuales /health
# devuelve 200 "starting" aunque el worker no haya latido todavía.
STARTUP_GRACE_SECS = 10 * 60

_lock = threading.Lock()
_boot_time = time.time()
_worker_registered = False
_last_beat: Optional[float] = None
_planned_sleep_secs: float = 0.0
_last_error: Optional[str] = None


def register_worker() -> None:
    """El worker anuncia que su hilo arrancó (antes del primer ciclo)."""
    global _worker_registered
    with _lock:
        _worker_registered = True


def beat(planned_sleep_secs: float) -> None:
    """Registra el fin de un ciclo y cuánto va a dormir el worker.

    El sueño planeado se guarda porque el intervalo es dinámico (5-15 min)
    y la pausa nocturna duerme horas: la tolerancia de /health debe
    calcularse contra lo que el worker REALMENTE planeó dormir.
    """
    global _last_beat, _planned_sleep_secs
    with _lock:
        _last_beat = time.time()
        _planned_sleep_secs = max(planned_sleep_secs, 0.0)


def record_error(message: str) -> None:
    """Guarda el último error de ciclo para mostrarlo en /health."""
    global _last_error
    with _lock:
        _last_error = message[:300]


def check() -> tuple[bool, str, Optional[str]]:
    """Evalúa la salud del worker.

    Returns:
        (healthy, status, detail) donde status es uno de:
        "ok" | "starting" | "sin_latido" | "atrasado"
    """
    with _lock:
        registered = _worker_registered
        last_beat = _last_beat
        planned_sleep = _planned_sleep_secs
        last_error = _last_error

    now = time.time()
    margin_secs = 3 * settings.max_poll_interval_minutes * 60

    # Aún no hay ningún ciclo completado
    if last_beat is None:
        if now - _boot_time < STARTUP_GRACE_SECS:
            return True, "starting", "worker arrancando, sin ciclos completados aún"
        if not registered:
            detail = "el hilo del worker nunca arrancó (sin registro tras el periodo de gracia)"
        else:
            detail = "el worker arrancó pero no ha completado ningún ciclo tras el periodo de gracia"
        if last_error:
            detail += f" | último error: {last_error}"
        return False, "sin_latido", detail

    # Hay latido: tolerancia = sueño planeado + 3x el intervalo máximo
    # (el 3x absorbe la duración del ciclo en sí: IA, geocoding, reintentos)
    elapsed = now - last_beat
    allowed = planned_sleep + margin_secs
    last_beat_str = datetime.fromtimestamp(last_beat).strftime("%Y-%m-%d %H:%M:%S")

    if elapsed > allowed:
        detail = (
            f"último ciclo terminó hace {elapsed / 60:.0f} min "
            f"(tolerancia: {allowed / 60:.0f} min, último latido: {last_beat_str})"
        )
        if last_error:
            detail += f" | último error: {last_error}"
        return False, "atrasado", detail

    return True, "ok", f"último ciclo: {last_beat_str}"
