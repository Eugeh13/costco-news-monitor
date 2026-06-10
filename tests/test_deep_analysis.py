"""
Tests del servicio de análisis profundo (DeepAnalysisService).

Cubre el fix C4c de Fase 1: cuando la IA devuelve una ubicación NO específica
(is_specific=false, p.ej. solo "Monterrey"), el servicio NO debe geocodificarla:
geocodificar "Monterrey" da el centro de la ciudad (dentro del radio de Costco
Valle Oriente) y generaba alertas falsas. En ese caso solo se consultan las
vialidades clave mencionadas en el texto (GeoService.check_roads_only).

Todo es sintético: AIProvider, DeepReader y GeoService son MagicMock con spec —
ningún test toca red, BD ni APIs de pago.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.models import (
    Alert,
    AnalysisResult,
    IncidentCategory,
    LocationInfo,
    NewsItem,
    ProximityResult,
    TriageResult,
)
from app.domain.ports import AIProvider, DeepReader
from app.services.deep_analysis import DeepAnalysisService
from app.services.geo_service import GeoService


# ============================================================
# Helpers — datos sintéticos y servicio con dependencias mock
# ============================================================

def _noticia(url: str | None = "https://ejemplo.test/nota-1") -> NewsItem:
    return NewsItem(
        titulo="Balacera en avenida del sur de Monterrey",
        contenido="Se reporta una balacera con personas lesionadas.",
        url=url,
        fuente="fuente-sintetica",
    )


def _triage() -> TriageResult:
    return TriageResult(estimated_category="seguridad", estimated_severity=8)


def _analisis(
    is_relevant: bool = True,
    extracted: str = "Av. Lázaro Cárdenas 800, San Pedro",
    normalized: str = "Av. Lázaro Cárdenas 800, San Pedro Garza García, NL",
    is_specific: bool = True,
) -> AnalysisResult:
    return AnalysisResult(
        is_relevant=is_relevant,
        category=IncidentCategory.SEGURIDAD,
        severity=8,
        summary="Balacera reportada cerca de zona comercial.",
        exclusion_reason="" if is_relevant else "evento sin impacto operacional",
        location=LocationInfo(extracted=extracted, normalized=normalized, is_specific=is_specific),
    )


def _dentro_de_radio(via: str = "geocoding") -> ProximityResult:
    return ProximityResult(
        is_within_radius=True,
        costco_nombre="Costco Valle Oriente",
        costco_direccion="Av Lázaro Cárdenas 800, San Pedro Garza García",
        distancia_km=1.2,
        matched_via=via,
    )


def _fuera_de_radio() -> ProximityResult:
    return ProximityResult(is_within_radius=False, distancia_km=42.0)


def _servicio(
    analisis: AnalysisResult | None,
    resultado_roads: ProximityResult | None = None,
    resultado_proximity: ProximityResult | None = None,
    contenido_completo: str | None = None,
):
    """DeepAnalysisService con las tres dependencias simuladas."""
    ai = MagicMock(spec=AIProvider)
    ai.deep_analyze.return_value = analisis

    reader = MagicMock(spec=DeepReader)
    reader.extract.return_value = contenido_completo

    geo = MagicMock(spec=GeoService)
    geo.check_roads_only.return_value = (
        resultado_roads if resultado_roads is not None else _fuera_de_radio()
    )
    geo.check_proximity.return_value = resultado_proximity

    return DeepAnalysisService(ai, reader, geo), ai, reader, geo


# ============================================================
# Fix C4c — ubicación vaga NO se geocodifica
# ============================================================

def test_ubicacion_vaga_no_geocodifica_ni_produce_alerta():
    """
    Núcleo del fix C4c: is_specific=false (solo "Monterrey") y sin vialidades
    clave en el texto → NO se llama check_proximity (geocodificación) y NO hay
    alerta. Antes del fix, geocodificar "Monterrey" caía en el centro de la
    ciudad y disparaba alertas falsas de Valle Oriente.
    """
    analisis = _analisis(extracted="Monterrey", normalized="Monterrey, NL", is_specific=False)
    servicio, ai, _, geo = _servicio(analisis, resultado_roads=_fuera_de_radio())

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is None, "ubicación vaga sin vialidades clave NO debe producir alerta"
    geo.check_proximity.assert_not_called()  # jamás geocodificar una ubicación vaga
    geo.check_roads_only.assert_called_once()
    # El chequeo de vialidades recibe el texto completo (título + contenido)
    texto = geo.check_roads_only.call_args.args[0]
    assert "Balacera en avenida" in texto and "personas lesionadas" in texto, (
        "check_roads_only debe recibir título + contenido para buscar vialidades clave"
    )


def test_ubicacion_vaga_con_vialidad_clave_si_alerta_via_vialidades():
    """
    Ubicación vaga PERO el texto menciona una vialidad clave dentro del radio:
    sí hay alerta, resuelta vía vialidades — y sigue sin geocodificarse.
    """
    analisis = _analisis(extracted="Monterrey", normalized="", is_specific=False)
    servicio, _, _, geo = _servicio(analisis, resultado_roads=_dentro_de_radio(via="vialidad"))

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is not None, "vialidad clave dentro del radio debe producir alerta"
    assert isinstance(alerta, Alert)
    assert alerta.proximity.matched_via == "vialidad"
    assert alerta.proximity.costco_nombre == "Costco Valle Oriente"
    # Con ubicación vaga nunca se geocodifica, ni aunque haya match de vialidad
    geo.check_proximity.assert_not_called()


def test_sin_ubicacion_extraida_solo_consulta_vialidades():
    """Si la IA no extrajo ubicación (extracted=""), tampoco se geocodifica."""
    analisis = _analisis(extracted="", normalized="", is_specific=False)
    servicio, _, _, geo = _servicio(analisis, resultado_roads=_fuera_de_radio())

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is None, "sin ubicación ni vialidades clave no hay alerta"
    geo.check_proximity.assert_not_called()
    geo.check_roads_only.assert_called_once()


# ============================================================
# Caso positivo — ubicación específica sí pasa a geocodificación
# ============================================================

def test_ubicacion_especifica_si_geocodifica_y_produce_alerta():
    """is_specific=true → check_proximity con la ubicación normalizada → Alert."""
    analisis = _analisis(is_specific=True)
    servicio, _, _, geo = _servicio(analisis, resultado_proximity=_dentro_de_radio())

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is not None, "ubicación específica dentro del radio debe producir alerta"
    geo.check_proximity.assert_called_once()
    ubicacion_usada = geo.check_proximity.call_args.args[0]
    assert ubicacion_usada == "Av. Lázaro Cárdenas 800, San Pedro Garza García, NL", (
        "debe geocodificarse la ubicación NORMALIZADA que devolvió la IA"
    )
    geo.check_roads_only.assert_not_called()
    # La alerta queda completamente armada
    assert alerta.news.titulo == _noticia().titulo
    assert alerta.analysis is analisis
    assert alerta.proximity.is_within_radius is True


def test_ubicacion_especifica_usa_extracted_si_normalized_viene_vacio():
    """Si la IA no normalizó, se geocodifica la ubicación tal como fue extraída."""
    analisis = _analisis(extracted="Garza Sada y Alfonso Reyes", normalized="", is_specific=True)
    servicio, _, _, geo = _servicio(analisis, resultado_proximity=_dentro_de_radio())

    servicio.analyze(_noticia(), _triage())

    ubicacion_usada = geo.check_proximity.call_args.args[0]
    assert ubicacion_usada == "Garza Sada y Alfonso Reyes", (
        "con normalized vacío debe usarse location.extracted como fallback"
    )


def test_ubicacion_especifica_fuera_de_radio_no_produce_alerta():
    """Geocodificación exitosa pero lejos de todo Costco → se descarta."""
    servicio, _, _, geo = _servicio(_analisis(), resultado_proximity=_fuera_de_radio())

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is None, "evento fuera del radio no debe producir alerta"
    geo.check_proximity.assert_called_once()


def test_check_proximity_devuelve_none_no_truena_y_no_alerta():
    """Si geo no pudo resolver nada (None), el servicio descarta sin excepción."""
    servicio, _, _, _ = _servicio(_analisis(), resultado_proximity=None)

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is None, "proximity None debe descartar la noticia sin tronar"


# ============================================================
# Respuestas de IA inválidas o no relevantes
# ============================================================

def test_respuesta_ia_invalida_none_no_truena_y_no_llama_geo():
    """
    Si el parser de deep analysis devolvió None (JSON malformado, API caída),
    analyze devuelve None sin excepción y sin tocar geo.
    """
    servicio, ai, _, geo = _servicio(analisis=None)

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is None, "análisis IA inválido (None) debe descartar la noticia"
    ai.deep_analyze.assert_called_once()
    geo.check_proximity.assert_not_called()
    geo.check_roads_only.assert_not_called()


def test_articulo_no_relevante_se_descarta_antes_de_geo():
    """is_relevant=false corta el pipeline: ni geocodificación ni vialidades."""
    servicio, _, _, geo = _servicio(_analisis(is_relevant=False))

    alerta = servicio.analyze(_noticia(), _triage())

    assert alerta is None, "artículo no relevante no debe producir alerta"
    geo.check_proximity.assert_not_called()
    geo.check_roads_only.assert_not_called()


# ============================================================
# Lectura de contenido (DeepReader)
# ============================================================

def test_usa_articulo_completo_del_reader_cuando_es_mas_largo():
    """Si el reader extrae un texto más largo que el snippet, la IA analiza ese."""
    texto_largo = "Texto completo del artículo con muchos más detalles. " * 20
    servicio, ai, reader, _ = _servicio(_analisis(is_relevant=False), contenido_completo=texto_largo)
    noticia = _noticia()

    servicio.analyze(noticia, _triage())

    reader.extract.assert_called_once_with(noticia.url)
    titulo_usado, contenido_usado = ai.deep_analyze.call_args.args
    assert titulo_usado == noticia.titulo
    assert contenido_usado == texto_largo, (
        "deep_analyze debe recibir el artículo completo cuando es más largo que el snippet"
    )


def test_usa_snippet_si_el_reader_falla():
    """Si el reader devuelve None, la IA analiza el snippet original."""
    servicio, ai, _, _ = _servicio(_analisis(is_relevant=False), contenido_completo=None)
    noticia = _noticia()

    servicio.analyze(noticia, _triage())

    _, contenido_usado = ai.deep_analyze.call_args.args
    assert contenido_usado == noticia.contenido, (
        "con reader fallido se debe usar el snippet original"
    )


def test_sin_url_no_llama_al_reader():
    """Noticia sin URL: no se intenta extracción profunda."""
    servicio, ai, reader, _ = _servicio(_analisis(is_relevant=False))
    noticia = _noticia(url=None)

    servicio.analyze(noticia, _triage())

    reader.extract.assert_not_called()
    _, contenido_usado = ai.deep_analyze.call_args.args
    assert contenido_usado == noticia.contenido
