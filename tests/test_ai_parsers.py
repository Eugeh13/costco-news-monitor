"""
Tests de los parsers de respuestas IA (triage y análisis profundo).

Cubre el fix C1 de Fase 0: el parser de triage de Anthropic tronaba con
AttributeError cuando la respuesta del modelo no era exactamente
{"results": [...]}. El comportamiento correcto documentado por la auditoría:

  - El parser NUNCA lanza excepción, sin importar qué devuelva el modelo.
  - Acepta {"results": [...]} (lo que pide el prompt), una lista JSON directa,
    y JSON envuelto en fences markdown (```json ... ```).
  - Ante respuesta vacía / JSON malformado o truncado, el fallback es
    "todas como candidatas": una TriageResult con decision=UNKNOWN por cada
    noticia enviada (TriageResult.is_candidate trata UNKNOWN como candidata,
    para no perder alertas por un error de parseo).

Ningún test toca red: los providers se instancian con __new__ (sin construir
el cliente del SDK) o con el cliente reemplazado por un MagicMock.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.domain.models import IncidentCategory, TrafficImpact, TriageDecision, TriageResult
from app.infrastructure.ai.anthropic_provider import AnthropicProvider
from app.infrastructure.ai.openai_provider import OpenAIProvider

PROVIDERS = ["anthropic", "openai"]

# NOTA HISTÓRICA: estos tests encontraron un BUG REAL — el fix C1 (except amplio
# en el parser de triage/análisis) no estaba replicado en openai_provider.py.
# Corregido el 2026-06-10: ambos providers capturan ahora
# (JSONDecodeError, KeyError, AttributeError, TypeError). Las listas se
# conservan por claridad de intención; hoy equivalen a PROVIDERS.
PROVIDERS_XFAIL_OPENAI = PROVIDERS
PROVIDERS_XFAIL_OPENAI_ANALYSIS = PROVIDERS



# ============================================================
# Helpers — instancian los providers SIN cliente SDK real
# ============================================================

def _provider_sin_cliente(nombre: str):
    """Crea el provider sin pasar por __init__ (que instancia el SDK real)."""
    if nombre == "anthropic":
        return AnthropicProvider.__new__(AnthropicProvider)
    return OpenAIProvider.__new__(OpenAIProvider)


def _parse_triage(nombre: str, raw, count: int) -> list[TriageResult]:
    """Despacha al método de parseo de triage de cada provider."""
    provider = _provider_sin_cliente(nombre)
    if nombre == "anthropic":
        return provider._parse_triage(raw, count)
    return provider._parse_triage_response(raw, count)


def _parse_analysis(nombre: str, raw):
    """Despacha al método de parseo de análisis profundo de cada provider."""
    provider = _provider_sin_cliente(nombre)
    if nombre == "anthropic":
        return provider._parse_analysis(raw)
    return provider._parse_analysis_response(raw)


def _item_triage(index: int = 0, decision: str = "candidata", **extra) -> dict:
    """Item de triage sintético con la forma que pide el prompt."""
    base = {
        "index": index,
        "decision": decision,
        "category": "seguridad",
        "severity": 8,
        "location_hint": "Av. Lázaro Cárdenas, San Pedro",
        "reason": "balacera reportada",
    }
    base.update(extra)
    return base


def _assert_fallback_todas_candidatas(results: list[TriageResult], count: int, contexto: str):
    """Verifica el fallback documentado: N resultados UNKNOWN, todos candidatas."""
    assert len(results) == count, (
        f"{contexto}: el fallback debe devolver un resultado por noticia "
        f"({count}), devolvió {len(results)}"
    )
    for i, r in enumerate(results):
        assert r.decision == TriageDecision.UNKNOWN, (
            f"{contexto}: el resultado {i} del fallback debe ser UNKNOWN, fue {r.decision}"
        )
        assert r.is_candidate, (
            f"{contexto}: UNKNOWN debe tratarse como candidata (no perder alertas)"
        )
        assert r.index == i, (
            f"{contexto}: los índices del fallback deben ser secuenciales (esperado {i}, fue {r.index})"
        )


# ============================================================
# Triage — formatos de respuesta aceptados (fix C1)
# ============================================================

@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_acepta_formato_results_que_pide_el_prompt(nombre):
    """Formato canónico {"results": [...]} se parsea con todos sus campos."""
    raw = json.dumps({"results": [
        _item_triage(0, "candidata"),
        _item_triage(1, "descartada", category="otro", severity=2, reason="deportes"),
    ]})

    results = _parse_triage(nombre, raw, 2)

    assert len(results) == 2, f"{nombre}: debió parsear 2 resultados"
    assert results[0].decision == TriageDecision.CANDIDATE, f"{nombre}: item 0 debió ser candidata"
    assert results[0].estimated_category == "seguridad"
    assert results[0].estimated_severity == 8
    assert results[0].location_hint == "Av. Lázaro Cárdenas, San Pedro"
    assert results[0].reason == "balacera reportada"
    assert results[1].decision == TriageDecision.DISCARDED, f"{nombre}: item 1 debió ser descartada"
    assert not results[1].is_candidate, f"{nombre}: descartada no debe ser candidata"


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_acepta_lista_json_directa_sin_envoltorio(nombre):
    """El modelo a veces devuelve [...] en vez de {"results": [...]} — debe aceptarse."""
    raw = json.dumps([_item_triage(0, "candidata"), _item_triage(1, "descartada")])

    results = _parse_triage(nombre, raw, 2)

    assert len(results) == 2, f"{nombre}: la lista directa debió parsearse igual que 'results'"
    assert results[0].decision == TriageDecision.CANDIDATE
    assert results[1].decision == TriageDecision.DISCARDED


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_acepta_json_envuelto_en_fences_markdown(nombre):
    """JSON dentro de ```json ... ``` debe limpiarse y parsearse."""
    interno = json.dumps({"results": [_item_triage(0, "candidata")]}, indent=2)
    raw = f"```json\n{interno}\n```"

    results = _parse_triage(nombre, raw, 1)

    assert len(results) == 1, f"{nombre}: el JSON con fences debió parsearse"
    assert results[0].decision == TriageDecision.CANDIDATE


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_json_truncado_no_lanza_y_devuelve_fallback_todas_candidatas(nombre):
    """
    Fix C1: una respuesta cortada a media cadena (p.ej. por max_tokens) NO debe
    lanzar excepción — debe caer al fallback de todas candidatas.
    """
    raw = '{"results": [{"index": 0, "decision": "candi'  # truncado a media cadena

    results = _parse_triage(nombre, raw, 3)

    _assert_fallback_todas_candidatas(results, 3, f"{nombre} con JSON truncado")


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_respuesta_none_devuelve_fallback_todas_candidatas(nombre):
    """Si la llamada al API falló (_call devuelve None), fallback completo."""
    results = _parse_triage(nombre, None, 4)

    _assert_fallback_todas_candidatas(results, 4, f"{nombre} con respuesta None")


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_texto_plano_sin_json_devuelve_fallback(nombre):
    """Una disculpa en prosa del modelo (sin JSON) no debe tronar."""
    raw = "Lo siento, no puedo clasificar estas noticias en este momento."

    results = _parse_triage(nombre, raw, 2)

    _assert_fallback_todas_candidatas(results, 2, f"{nombre} con texto plano")


# ============================================================
# Triage — truncamiento lógico (menos items que noticias)
# ============================================================

@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_menos_items_que_noticias_devuelve_solo_los_parseados_sin_crash(nombre):
    """
    JSON válido pero con menos items que noticias enviadas (el modelo se quedó
    corto): comportamiento documentado — se devuelven solo los items parseados,
    sin excepción. TriageService tolera la lista corta (filtra por
    triage.index < len(news)); las noticias sin veredicto simplemente no
    avanzan, no hay crash.
    """
    raw = json.dumps({"results": [
        _item_triage(0, "candidata"),
        _item_triage(1, "descartada"),
    ]})

    results = _parse_triage(nombre, raw, 5)  # se enviaron 5 noticias

    assert len(results) == 2, (
        f"{nombre}: con respuesta corta se devuelven solo los items que sí llegaron"
    )
    assert [r.index for r in results] == [0, 1], f"{nombre}: los índices originales se preservan"


# ============================================================
# Triage — robustez ante campos inesperados
# ============================================================

@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_decision_invalida_cae_a_desconocido(nombre):
    """Una decision fuera del enum (p.ej. 'tal vez') cae a UNKNOWN, no truena."""
    raw = json.dumps({"results": [_item_triage(0, decision="tal vez")]})

    results = _parse_triage(nombre, raw, 1)

    assert len(results) == 1
    assert results[0].decision == TriageDecision.UNKNOWN, (
        f"{nombre}: decision inválida debe degradar a UNKNOWN"
    )
    assert results[0].is_candidate, f"{nombre}: UNKNOWN cuenta como candidata"


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_campos_inesperados_e_is_candidate_string_no_truenan(nombre):
    """
    Item con campos que el prompt no pide (p.ej. is_candidate: "true") y sin
    "decision": los campos extra se ignoran y la decision ausente cae a UNKNOWN.
    """
    raw = json.dumps({"results": [
        {"index": 0, "is_candidate": "true", "confianza": 0.9, "extra": [1, 2]},
    ]})

    results = _parse_triage(nombre, raw, 1)

    assert len(results) == 1, f"{nombre}: el item con campos raros debe producir un resultado"
    assert results[0].decision == TriageDecision.UNKNOWN, (
        f"{nombre}: sin campo 'decision' la decisión debe ser UNKNOWN"
    )
    assert results[0].is_candidate, (
        f"{nombre}: ante ambigüedad la noticia debe seguir siendo candidata"
    )


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_severity_fuera_de_rango_se_recorta_a_1_10(nombre):
    """Severidad 99 o -3 se recorta al rango [1, 10] (evita ValidationError de pydantic)."""
    raw = json.dumps({"results": [
        _item_triage(0, severity=99),
        _item_triage(1, severity=-3),
    ]})

    results = _parse_triage(nombre, raw, 2)

    assert results[0].estimated_severity == 10, f"{nombre}: severidad 99 debe recortarse a 10"
    assert results[1].estimated_severity == 1, f"{nombre}: severidad -3 debe recortarse a 1"


@pytest.mark.parametrize("nombre", PROVIDERS_XFAIL_OPENAI)
def test_triage_items_no_dict_no_lanzan_excepcion(nombre):
    """
    Si el modelo devuelve strings o números dentro de "results", el parser no
    debe tronar (esa es exactamente la clase de bug del fix C1).

    # POSIBLE BUG: en OpenAIProvider._parse_triage_response el except solo
    # captura (JSONDecodeError, KeyError); un item no-dict provoca
    # AttributeError ('str' object has no attribute 'get') y SÍ truena.
    # El fix C1 se aplicó a AnthropicProvider (captura AttributeError/TypeError)
    # pero no se replicó en OpenAIProvider. Este test falla para "openai".
    """
    raw = json.dumps({"results": ["texto suelto", 42]})

    try:
        results = _parse_triage(nombre, raw, 2)
    except Exception as e:  # pragma: no cover — solo para mensaje claro
        pytest.fail(
            f"{nombre}: el parser de triage no debe lanzar excepción ante items "
            f"no-dict; lanzó {type(e).__name__}: {e}"
        )

    # Comportamiento correcto: fallback de todas candidatas (no se pudo
    # interpretar ningún item de forma confiable).
    _assert_fallback_todas_candidatas(results, 2, f"{nombre} con items no-dict")


@pytest.mark.parametrize("nombre", PROVIDERS_XFAIL_OPENAI)
def test_triage_severity_como_string_no_lanza_excepcion(nombre):
    """
    severity "7" (string en vez de int) no debe tronar: min/max contra int
    lanza TypeError, y el parser debe absorberlo.

    # POSIBLE BUG: en OpenAIProvider._parse_triage_response el TypeError de
    # min(max("7", 5), 1) NO está capturado (solo JSONDecodeError/KeyError),
    # así que truena. AnthropicProvider sí lo captura y cae al fallback.
    # Este test falla para "openai".
    """
    raw = json.dumps({"results": [_item_triage(0, severity="7")]})

    try:
        results = _parse_triage(nombre, raw, 1)
    except Exception as e:  # pragma: no cover — solo para mensaje claro
        pytest.fail(
            f"{nombre}: el parser de triage no debe lanzar excepción ante "
            f"severity string; lanzó {type(e).__name__}: {e}"
        )

    assert len(results) == 1, f"{nombre}: debe devolver un resultado por noticia"
    assert isinstance(results[0], TriageResult)


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_triage_dict_sin_clave_results_devuelve_lista_vacia(nombre):
    """
    Un dict válido pero sin "results" (p.ej. el modelo devolvió un solo item
    suelto) produce lista vacía sin tronar — comportamiento actual documentado.
    """
    # POSIBLE BUG (de diseño, en AMBOS providers): la lista vacía hace que
    # TriageService no produzca candidatas para el chunk completo — las noticias
    # se descartan en silencio. Eso contradice la filosofía del propio fix C1
    # ("ante respuesta no interpretable, todas candidatas para no perder
    # alertas"): un JSON malformado cae al fallback seguro, pero un dict válido
    # con la clave equivocada (p.ej. {"resultados": [...]}) pierde todo el lote.
    # Se documenta el comportamiento actual; el comportamiento "seguro" sería
    # el mismo fallback de todas candidatas.
    raw = json.dumps({"index": 0, "decision": "candidata"})

    results = _parse_triage(nombre, raw, 1)

    assert results == [], (
        f"{nombre}: dict sin 'results' produce 0 resultados (sin excepción)"
    )


# ============================================================
# batch_triage end-to-end con cliente SDK mockeado
# ============================================================

def test_batch_triage_anthropic_con_cliente_mockeado_parsea_y_pide_tokens_suficientes():
    """
    batch_triage completo con el SDK de Anthropic simulado: arma el prompt,
    parsea la respuesta y — parte del fix de truncamiento — pide más de 2000
    max_tokens (2000 truncaba el JSON de 25 noticias y disparaba el fallback caro).
    """
    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider._model = "claude-sintetico"
    respuesta = MagicMock()
    respuesta.content = [MagicMock(text=json.dumps({"results": [_item_triage(0)]}))]
    provider._client = MagicMock()
    provider._client.messages.create.return_value = respuesta

    results = provider.batch_triage([{"titulo": "Balacera en Valle Oriente", "contenido": "..."}])

    assert len(results) == 1, "debió parsear el único resultado de la respuesta mockeada"
    assert results[0].decision == TriageDecision.CANDIDATE

    provider._client.messages.create.assert_called_once()
    kwargs = provider._client.messages.create.call_args.kwargs
    assert kwargs["max_tokens"] > 2000, (
        "max_tokens debe ser > 2000: con 2000 el JSON del triage de 25 noticias "
        "se truncaba y todo caía al fallback de 'todas candidatas' (caro)"
    )
    assert kwargs["temperature"] == 0, "la clasificación debe ser determinista (temperature=0)"


def test_batch_triage_anthropic_error_de_api_devuelve_fallback():
    """Si el SDK lanza (timeout, 500...), batch_triage devuelve el fallback, no propaga."""
    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider._model = "claude-sintetico"
    provider._client = MagicMock()
    provider._client.messages.create.side_effect = RuntimeError("API caída (sintético)")

    results = provider.batch_triage([{"titulo": "a"}, {"titulo": "b"}, {"titulo": "c"}])

    _assert_fallback_todas_candidatas(results, 3, "anthropic con error de API")


def test_batch_triage_openai_con_cliente_mockeado_parsea():
    """batch_triage completo con el SDK de OpenAI simulado."""
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider._model = "gpt-sintetico"
    respuesta = MagicMock()
    respuesta.choices = [MagicMock(message=MagicMock(content=json.dumps(
        {"results": [_item_triage(0, "descartada")]}
    )))]
    provider._client = MagicMock()
    provider._client.chat.completions.create.return_value = respuesta

    results = provider.batch_triage([{"titulo": "Nota de espectáculos", "contenido": "..."}])

    assert len(results) == 1
    assert results[0].decision == TriageDecision.DISCARDED
    provider._client.chat.completions.create.assert_called_once()
    kwargs = provider._client.chat.completions.create.call_args.kwargs
    assert kwargs.get("response_format") == {"type": "json_object"}, (
        "OpenAI debe pedir JSON mode (response_format json_object): es la primera "
        "línea de defensa contra respuestas no parseables en el triage"
    )


def test_batch_triage_openai_error_de_api_devuelve_fallback():
    """Si el SDK de OpenAI lanza, batch_triage devuelve el fallback, no propaga."""
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider._model = "gpt-sintetico"
    provider._client = MagicMock()
    provider._client.chat.completions.create.side_effect = RuntimeError("API caída (sintético)")

    results = provider.batch_triage([{"titulo": "a"}, {"titulo": "b"}])

    _assert_fallback_todas_candidatas(results, 2, "openai con error de API")


# ============================================================
# Parser de análisis profundo
# ============================================================

def _analysis_json(**overrides) -> str:
    """Respuesta sintética completa de análisis profundo (forma del prompt)."""
    data = {
        "is_relevant": True,
        "category": "seguridad",
        "severity": 8,
        "summary": "Balacera a 1 km de Costco Valle Oriente.",
        "exclusion_reason": "",
        "location": {
            "extracted": "Av. Lázaro Cárdenas y Dr. Atl, San Pedro",
            "normalized": "Av. Lázaro Cárdenas y Dr. Atl, San Pedro Garza García, NL",
            "is_specific": True,
        },
        "details": {"victims": 2, "traffic_impact": "high", "emergency_services": True},
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_parse_analysis_json_completo_mapea_todos_los_campos(nombre):
    """Un JSON completo de análisis profundo llena AnalysisResult campo a campo."""
    result = _parse_analysis(nombre, _analysis_json())

    assert result is not None, f"{nombre}: el JSON válido debió producir un AnalysisResult"
    assert result.is_relevant is True
    assert result.category == IncidentCategory.SEGURIDAD
    assert result.severity == 8
    assert result.summary.startswith("Balacera")
    assert result.location.extracted == "Av. Lázaro Cárdenas y Dr. Atl, San Pedro"
    assert result.location.is_specific is True
    assert result.victims == 2
    assert result.traffic_impact == TrafficImpact.HIGH
    assert result.emergency_services is True


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_parse_analysis_respuesta_none_devuelve_none(nombre):
    """Si la llamada al API falló, el análisis es None (sin excepción)."""
    assert _parse_analysis(nombre, None) is None, (
        f"{nombre}: respuesta None debe producir None"
    )


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_parse_analysis_json_malformado_devuelve_none(nombre):
    """JSON truncado/malformado en deep analysis devuelve None, no excepción."""
    assert _parse_analysis(nombre, '{"is_relevant": tru') is None, (
        f"{nombre}: JSON malformado debe producir None"
    )


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_parse_analysis_preserva_is_specific_false(nombre):
    """
    is_specific=false debe llegar intacto a LocationInfo — de esto depende el
    fix C4c (no geocodificar ubicaciones vagas; ver test_deep_analysis.py).
    """
    raw = _analysis_json(location={
        "extracted": "Monterrey",
        "normalized": "Monterrey, NL",
        "is_specific": False,
    })

    result = _parse_analysis(nombre, raw)

    assert result is not None
    assert result.location.is_specific is False, (
        f"{nombre}: is_specific=false del modelo debe preservarse (clave para C4c)"
    )
    assert result.location.extracted == "Monterrey"


@pytest.mark.parametrize("nombre", PROVIDERS)
def test_parse_analysis_categoria_y_traffic_invalidos_caen_a_default(nombre):
    """Valores fuera de enum degradan a OTRO / UNKNOWN en vez de tronar."""
    raw = _analysis_json(
        category="categoria_marciana",
        details={"victims": 0, "traffic_impact": "apocaliptico", "emergency_services": False},
    )

    result = _parse_analysis(nombre, raw)

    assert result is not None, f"{nombre}: enums inválidos no deben tirar el parseo"
    assert result.category == IncidentCategory.OTRO, (
        f"{nombre}: categoría desconocida debe caer a OTRO"
    )
    assert result.traffic_impact == TrafficImpact.UNKNOWN, (
        f"{nombre}: traffic_impact desconocido debe caer a UNKNOWN"
    )


@pytest.mark.parametrize("nombre", PROVIDERS_XFAIL_OPENAI_ANALYSIS)
def test_parse_analysis_location_como_string_no_lanza_excepcion(nombre):
    """
    El modelo devuelve "location": "Monterrey" (string, no el dict que pide el
    prompt). El parser NUNCA debe lanzar: o devuelve None (descarta la noticia,
    como hace anthropic) o un AnalysisResult degradado.

    # BUG REAL en openai: location_data.get("extracted") sobre un string lanza
    # AttributeError no capturado (openai_provider.py:168 solo captura
    # JSONDecodeError/KeyError) y, como DeepAnalysisService.analyze tampoco lo
    # captura, tira el ciclo completo de monitoreo. Mismo patrón del fix C1.
    """
    raw = _analysis_json(location="Monterrey")

    try:
        result = _parse_analysis(nombre, raw)
    except Exception as e:  # pragma: no cover — solo para mensaje claro
        pytest.fail(
            f"{nombre}: el parser de análisis no debe lanzar excepción ante "
            f"location no-dict; lanzó {type(e).__name__}: {e}"
        )

    assert result is None or result.location is not None, (
        f"{nombre}: ante location no-dict el contrato es None (descartar) o un "
        f"AnalysisResult con location degradada — nunca una excepción"
    )


@pytest.mark.parametrize("nombre", PROVIDERS_XFAIL_OPENAI_ANALYSIS)
def test_parse_analysis_severity_como_string_no_lanza_excepcion(nombre):
    """
    severity "8" (string) en el análisis profundo no debe tronar: min/max
    contra int lanza TypeError y el parser debe absorberlo (anthropic devuelve
    None; openai lo deja propagar — mismo bug C1 sin replicar).
    """
    raw = _analysis_json(severity="8")

    try:
        result = _parse_analysis(nombre, raw)
    except Exception as e:  # pragma: no cover — solo para mensaje claro
        pytest.fail(
            f"{nombre}: el parser de análisis no debe lanzar excepción ante "
            f"severity string; lanzó {type(e).__name__}: {e}"
        )

    assert result is None or 1 <= result.severity <= 10, (
        f"{nombre}: severity string debe terminar en None (descartar) o en un "
        f"valor recortado al rango [1, 10] — nunca en una excepción"
    )
