"""
Tests del digest mensual programado (scheduler) y del sondeo de cortes
SESNSP (SESNSPMunicipalData.probe_beyond).

Sin red: requests.head va mockeado, generar_digest se reemplaza con
monkeypatch y el marcador persistente se escribe en tmp_path.
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import scheduler
from app.config.settings import settings
from app.infrastructure.sources.sesnsp_municipal import SESNSPMunicipalData
from app.services.crime_digest import MESES
from crime_report import generar_digest


# ── Helpers ──────────────────────────────────────────────────


def _ahora(dia: int, hora: int) -> datetime:
    """Un 'now' sintético de junio 2026 (mes con datos en los tests)."""
    return datetime(2026, 6, dia, hora, 30)


@pytest.fixture
def marcador_en_tmp(tmp_path, monkeypatch):
    """Redirige el directorio de datos (FileStorage) a tmp_path y devuelve
    la ruta donde debe quedar el marcador del digest."""
    monkeypatch.setattr(
        settings, "processed_news_file", str(tmp_path / "processed_news.txt")
    )
    return tmp_path / "crime_digest_sent.txt"


# ── Marcador persistente ─────────────────────────────────────


def test_marcador_roundtrip(marcador_en_tmp):
    assert not scheduler._digest_already_sent("2026-06")
    scheduler._mark_digest_sent("2026-06")
    assert scheduler._digest_already_sent("2026-06")
    # Formato simple YYYY-MM en archivo (sobrevive reinicios del contenedor)
    assert marcador_en_tmp.read_text(encoding="utf-8").strip() == "2026-06"
    # Mes nuevo → el marcador del mes pasado no bloquea
    assert not scheduler._digest_already_sent("2026-07")


# ── _maybe_send_crime_digest: condiciones de disparo ─────────


def test_digest_no_corre_antes_del_dia_configurado(marcador_en_tmp, monkeypatch):
    gen = MagicMock()
    monkeypatch.setattr(scheduler, "generar_digest", gen)
    scheduler._maybe_send_crime_digest(MagicMock(), _ahora(dia=24, hora=10))
    gen.assert_not_called()


def test_digest_no_corre_antes_de_las_9(marcador_en_tmp, monkeypatch):
    gen = MagicMock()
    monkeypatch.setattr(scheduler, "generar_digest", gen)
    scheduler._maybe_send_crime_digest(MagicMock(), _ahora(dia=25, hora=8))
    gen.assert_not_called()


def test_digest_deshabilitado_por_flag(marcador_en_tmp, monkeypatch):
    gen = MagicMock()
    monkeypatch.setattr(scheduler, "generar_digest", gen)
    monkeypatch.setattr(settings, "crime_digest_enabled", False)
    scheduler._maybe_send_crime_digest(MagicMock(), _ahora(dia=25, hora=10))
    gen.assert_not_called()


def test_digest_corre_dias_posteriores_si_no_se_ha_enviado(marcador_en_tmp, monkeypatch):
    """`>=` en el día: si el portal falló el 25, el 27 todavía lo intenta."""
    monkeypatch.setattr(scheduler, "generar_digest", lambda: "digest")
    pipeline = MagicMock()
    scheduler._maybe_send_crime_digest(pipeline, _ahora(dia=27, hora=11))
    pipeline._notifier.send_text.assert_called_once_with("digest")


# ── _maybe_send_crime_digest: envío y marcador ───────────────


def test_digest_envia_por_el_notifier_del_pipeline_y_marca(marcador_en_tmp, monkeypatch):
    monkeypatch.setattr(scheduler, "generar_digest", lambda: "📊 digest de prueba")
    pipeline = MagicMock()
    scheduler._maybe_send_crime_digest(pipeline, _ahora(dia=25, hora=9))
    pipeline._notifier.send_text.assert_called_once_with("📊 digest de prueba")
    assert scheduler._digest_already_sent("2026-06")


def test_digest_no_se_reenvia_el_mismo_mes(marcador_en_tmp, monkeypatch):
    scheduler._mark_digest_sent("2026-06")
    gen = MagicMock()
    monkeypatch.setattr(scheduler, "generar_digest", gen)
    pipeline = MagicMock()
    scheduler._maybe_send_crime_digest(pipeline, _ahora(dia=26, hora=12))
    gen.assert_not_called()
    pipeline._notifier.send_text.assert_not_called()


def test_digest_sin_filas_no_marca_y_reintenta(marcador_en_tmp, monkeypatch):
    """Portal caído (generar_digest → None): nada se envía ni se marca."""
    monkeypatch.setattr(scheduler, "generar_digest", lambda: None)
    pipeline = MagicMock()
    scheduler._maybe_send_crime_digest(pipeline, _ahora(dia=25, hora=9))
    pipeline._notifier.send_text.assert_not_called()
    assert not scheduler._digest_already_sent("2026-06")


def test_digest_envio_fallido_no_marca(marcador_en_tmp, monkeypatch):
    """Telegram devuelve False → reintento en el siguiente ciclo."""
    monkeypatch.setattr(scheduler, "generar_digest", lambda: "digest")
    pipeline = MagicMock()
    pipeline._notifier.send_text.return_value = False
    scheduler._maybe_send_crime_digest(pipeline, _ahora(dia=25, hora=9))
    assert not scheduler._digest_already_sent("2026-06")


def test_digest_excepcion_no_propaga_ni_marca(marcador_en_tmp, monkeypatch):
    """Una excepción del portal no debe tumbar el loop del scheduler."""

    def _explota():
        raise RuntimeError("portal caído")

    monkeypatch.setattr(scheduler, "generar_digest", _explota)
    scheduler._maybe_send_crime_digest(MagicMock(), _ahora(dia=25, hora=9))  # no levanta
    assert not scheduler._digest_already_sent("2026-06")


# ── probe_beyond: sondeo de cortes posteriores ───────────────

_URL_DIC25 = "https://repodatos.atdt.gob.mx/api_update/sesnsp/IDM_NM_dic25.csv"


def _mock_head(monkeypatch, existentes: set[str]):
    """requests.head falso: 200 si el archivo está 'publicado', 503 si no
    (el comportamiento real observado en repodatos.atdt.gob.mx)."""
    llamadas = []

    def fake_head(url, **kwargs):
        llamadas.append(url)
        nombre = url.rsplit("/", 1)[-1]
        return SimpleNamespace(status_code=200 if nombre in existentes else 503)

    monkeypatch.setattr(
        "app.infrastructure.sources.sesnsp_municipal.requests.head", fake_head
    )
    return llamadas


def test_probe_beyond_encuentra_el_corte_mas_nuevo(monkeypatch):
    llamadas = _mock_head(monkeypatch, {"IDM_NM_ene26.csv", "IDM_NM_feb26.csv"})
    url = SESNSPMunicipalData().probe_beyond(_URL_DIC25, hoy=date(2026, 6, 10))
    assert url.endswith("IDM_NM_feb26.csv")
    # Sondea de ene26 a jun26 (hasta el mes actual, inclusive)
    assert len(llamadas) == 6


def test_probe_beyond_sin_cortes_nuevos_conserva_y_avisa_rezago(monkeypatch, capsys):
    _mock_head(monkeypatch, set())  # nada publicado después de dic25
    url = SESNSPMunicipalData().probe_beyond(_URL_DIC25, hoy=date(2026, 6, 10))
    assert url == _URL_DIC25
    salida = capsys.readouterr().out
    # dic25 vs jun26 = 6 meses de rezago (> 2) → advertencia
    assert "6 meses sin publicar" in salida
    assert "dic25" in salida


def test_probe_beyond_rezago_normal_no_avisa(monkeypatch, capsys):
    """Corte de hace 1 mes (lo normal): sin advertencia de rezago."""
    url_may26 = _URL_DIC25.replace("dic25", "may26")
    _mock_head(monkeypatch, set())
    url = SESNSPMunicipalData().probe_beyond(url_may26, hoy=date(2026, 6, 10))
    assert url == url_may26
    assert "sin publicar" not in capsys.readouterr().out


def test_probe_beyond_url_sin_patron_no_sondea(monkeypatch):
    head = MagicMock()
    monkeypatch.setattr(
        "app.infrastructure.sources.sesnsp_municipal.requests.head", head
    )
    url_rara = "https://repodatos.atdt.gob.mx/otro_dataset.csv"
    assert SESNSPMunicipalData().probe_beyond(url_rara, hoy=date(2026, 6, 10)) == url_rara
    head.assert_not_called()


def test_probe_beyond_tolera_errores_de_red(monkeypatch):
    """Un timeout en un mes no aborta el sondeo de los siguientes."""
    import requests as _requests

    def fake_head(url, **kwargs):
        nombre = url.rsplit("/", 1)[-1]
        if nombre == "IDM_NM_ene26.csv":
            raise _requests.exceptions.ConnectTimeout("timeout simulado")
        return SimpleNamespace(status_code=200 if nombre == "IDM_NM_feb26.csv" else 503)

    monkeypatch.setattr(
        "app.infrastructure.sources.sesnsp_municipal.requests.head", fake_head
    )
    url = SESNSPMunicipalData().probe_beyond(_URL_DIC25, hoy=date(2026, 6, 10))
    assert url.endswith("IDM_NM_feb26.csv")


# ── generar_digest (función reutilizable del CLI) ────────────


def _fila(anio: int, subtipo: str, **meses: str) -> dict:
    fila = {
        "Año": str(anio),
        "Cve. Municipio": "19039",
        "Tipo de delito": "Robo",
        "Subtipo de delito": subtipo,
    }
    fila.update({mes: "" for mes in MESES})
    fila.update(meses)
    return fila


def test_generar_digest_sin_filas_devuelve_none(monkeypatch):
    monkeypatch.setattr(
        "crime_report.SESNSPMunicipalData.fetch_rows", lambda self, **kw: []
    )
    assert generar_digest() is None


def test_generar_digest_con_filas_devuelve_texto(monkeypatch):
    filas = [
        _fila(2026, "Robo de vehículo automotor", Enero="5", Febrero="3"),
        _fila(2025, "Robo de vehículo automotor", Enero="4", Febrero="6"),
    ]
    monkeypatch.setattr(
        "crime_report.SESNSPMunicipalData.fetch_rows", lambda self, **kw: filas
    )
    texto = generar_digest()
    assert texto is not None
    assert "Contexto delictivo — Febrero 2026" in texto
    assert "Monterrey" in texto
