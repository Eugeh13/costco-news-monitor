"""
Tests de la property Alert.fecha_evento (app/domain/models.py — Fase 2).

Las vistas SQL del dashboard filtran por noticias.fecha_evento. Reglas:
- Con fecha_pub: la property devuelve esa fecha tal cual.
- Sin fecha_pub: devuelve "ahora" CON tz de America/Chicago (no naive) —
  en Railway el reloj del contenedor es UTC y un naive quedaría ~6h corrido.
"""

from __future__ import annotations

from datetime import datetime

import pytz

from app.domain.models import Alert, AnalysisResult, NewsItem, ProximityResult

_CHICAGO = pytz.timezone("America/Chicago")


def _alerta(fecha_pub: datetime | None) -> Alert:
    """Alert mínima con los modelos reales (defaults para analysis/proximity)."""
    return Alert(
        news=NewsItem(titulo="Choque en avenida Garza Sada", fecha_pub=fecha_pub),
        analysis=AnalysisResult(),
        proximity=ProximityResult(),
    )


def test_con_fecha_pub_devuelve_fecha_pub():
    fecha_pub = _CHICAGO.localize(datetime(2026, 6, 9, 8, 15, 0))
    assert _alerta(fecha_pub).fecha_evento == fecha_pub


def test_con_fecha_pub_naive_tambien_la_devuelve_tal_cual():
    # La property no inventa tz cuando la fuente sí trajo fecha
    fecha_pub = datetime(2026, 6, 9, 8, 15, 0)
    assert _alerta(fecha_pub).fecha_evento == fecha_pub


def test_sin_fecha_pub_devuelve_datetime_aware():
    fecha = _alerta(None).fecha_evento
    assert fecha.tzinfo is not None
    assert fecha.utcoffset() is not None  # aware de verdad, no naive


def test_sin_fecha_pub_la_tz_es_america_chicago():
    fecha = _alerta(None).fecha_evento
    # pytz expone la zona en .zone; el offset debe coincidir con Chicago "ahora"
    assert getattr(fecha.tzinfo, "zone", None) == "America/Chicago"
    assert fecha.utcoffset() == datetime.now(_CHICAGO).utcoffset()


def test_sin_fecha_pub_es_ahora_no_el_timestamp_naive():
    alerta = _alerta(None)
    ahora = datetime.now(_CHICAGO)
    diferencia = abs((alerta.fecha_evento - ahora).total_seconds())
    assert diferencia < 5  # "ahora" en hora del centro, no algo viejo/corrido
