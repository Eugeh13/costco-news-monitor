"""
Tests de app/services/content_hasher.py.

ContentHasher decide si el lote de noticias cambió entre corridas para poder
saltarse el pipeline (0 tokens de IA) cuando todo es idéntico.

Comportamiento real de la implementación (leído del código):
  - El hash es md5 de los TÍTULOS ordenados alfabéticamente y unidos con "|".
  - SOLO participa `titulo`: contenido, url, fuente y fecha quedan fuera.
  - NO hay normalización: mayúsculas, acentos y espacios cuentan tal cual
    (cualquier diferencia literal en un título se detecta como cambio).
  - El orden del lote NO importa (se ordena antes de hashear).
  - La primera corrida siempre cuenta como cambio.
  - `consecutive_no_change` incrementa con cada corrida idéntica y se
    reinicia a 0 cuando hay cambio.
"""

from __future__ import annotations

import pytest

from app.domain.models import NewsItem
from app.services.content_hasher import ContentHasher


def _noticia(titulo: str, **kwargs) -> NewsItem:
    """Crea un NewsItem sintético; solo el título es relevante para el hash."""
    return NewsItem(titulo=titulo, **kwargs)


# ════════════════════════════════════════════════════════════════════════════
# Determinismo: mismo lote → mismo hash
# ════════════════════════════════════════════════════════════════════════════

def test_primera_corrida_siempre_cuenta_como_cambio():
    hasher = ContentHasher()
    lote = [_noticia("Balacera en avenida Lázaro Cárdenas")]

    assert hasher.has_changed(lote) is True, (
        "La primera corrida no tiene hash previo: siempre debe procesarse"
    )
    assert hasher.consecutive_no_change == 0, (
        "Tras la primera corrida el contador de 'sin cambio' debe ser 0"
    )


def test_mismo_lote_dos_veces_no_cuenta_como_cambio():
    hasher = ContentHasher()
    lote = [
        _noticia("Balacera en avenida Lázaro Cárdenas", fuente="el norte"),
        _noticia("Detienen a dos en Valle Oriente", fuente="milenio"),
    ]

    hasher.has_changed(lote)
    segundo = hasher.has_changed(lote)

    assert segundo is False, (
        "Un lote idéntico al anterior no debe contarse como cambio "
        "(el pipeline debe poder saltarse)"
    )


def test_el_mismo_texto_produce_el_mismo_hash_entre_instancias():
    """_compute es determinista: dos hashers distintos con los mismos títulos
    producen exactamente el mismo hash."""
    lote_a = [_noticia("Robo a comercio en San Pedro"), _noticia("Choque en Gómez Morín")]
    lote_b = [_noticia("Robo a comercio en San Pedro"), _noticia("Choque en Gómez Morín")]

    hash_a = ContentHasher._compute(lote_a)
    hash_b = ContentHasher._compute(lote_b)

    assert hash_a == hash_b, "Los mismos títulos deben producir el mismo hash siempre"


def test_el_orden_del_lote_no_afecta_el_hash():
    """Los títulos se ordenan antes de hashear: recibir las mismas noticias en
    otro orden (típico entre fetches de RSS) no debe re-disparar el pipeline."""
    hasher = ContentHasher()
    n1 = _noticia("Asalto en Carretera Nacional")
    n2 = _noticia("Bloqueo vial en Fundadores")
    n3 = _noticia("Cateo en Santa Catarina")

    hasher.has_changed([n1, n2, n3])
    cambio = hasher.has_changed([n3, n1, n2])

    assert cambio is False, (
        "El mismo conjunto de títulos en distinto orden no debe contar como cambio"
    )


# ════════════════════════════════════════════════════════════════════════════
# Sensibilidad: qué SÍ cuenta como cambio
# ════════════════════════════════════════════════════════════════════════════

def test_titulos_distintos_cuentan_como_cambio():
    hasher = ContentHasher()
    hasher.has_changed([_noticia("Riña en bar del centro")])

    cambio = hasher.has_changed([_noticia("Persecución termina en Cumbres")])

    assert cambio is True, "Un título nuevo debe detectarse como cambio"


def test_no_hay_normalizacion_mayusculas_acentos_y_espacios_cuentan():
    """La implementación NO normaliza: cualquier diferencia literal en el
    título (mayúsculas, acentos, espacios extra) produce un hash distinto y
    por tanto cuenta como cambio. Es la semántica conservadora correcta para
    un detector de cambios (preferible re-procesar a perder una nota)."""
    base = "Balacera en Lázaro Cárdenas"
    hash_base = ContentHasher._compute([_noticia(base)])

    variantes = {
        "mayúsculas": "balacera en lázaro cárdenas",
        "acentos": "Balacera en Lazaro Cardenas",
        "espacios": "Balacera en  Lázaro Cárdenas ",
    }
    for nombre, variante in variantes.items():
        hash_variante = ContentHasher._compute([_noticia(variante)])
        assert hash_variante != hash_base, (
            f"Diferencia de {nombre} en el título debe producir un hash distinto "
            "(no existe normalizador en la implementación actual)"
        )


def test_agregar_una_noticia_al_lote_cuenta_como_cambio():
    hasher = ContentHasher()
    n1 = _noticia("Robo de vehículo en Apodaca")
    hasher.has_changed([n1])

    cambio = hasher.has_changed([n1, _noticia("Operativo en Escobedo")])

    assert cambio is True, "Una noticia adicional en el lote debe contar como cambio"


def test_titulo_duplicado_en_el_lote_cambia_el_hash():
    """sorted() conserva duplicados: ['a'] y ['a','a'] son lotes distintos."""
    hasher = ContentHasher()
    n = _noticia("Choque múltiple en Morones Prieto")
    hasher.has_changed([n])

    cambio = hasher.has_changed([n, _noticia("Choque múltiple en Morones Prieto")])

    assert cambio is True, (
        "Un título duplicado agranda el lote y debe detectarse como cambio"
    )


def test_titulo_con_pipe_no_debe_colisionar_con_lote_separado():
    """['Balacera en Valle Oriente|VIDEO'] y ['Balacera en Valle Oriente',
    'VIDEO'] son lotes DISTINTOS y deben producir hashes distintos. Era un
    BUG REAL (join por '|' sin escapar); corregido con separador \\x1f el
    2026-06-10."""
    hash_un_titulo = ContentHasher._compute(
        [_noticia("Balacera en Valle Oriente|VIDEO")]
    )
    hash_dos_titulos = ContentHasher._compute(
        [_noticia("Balacera en Valle Oriente"), _noticia("VIDEO")]
    )

    assert hash_un_titulo != hash_dos_titulos, (
        "Lotes distintos no deben compartir hash: el separador '|' sin escape "
        "hace ambiguo el encoding del lote"
    )


# ════════════════════════════════════════════════════════════════════════════
# Qué campos participan en el hash (solo titulo, por diseño)
# ════════════════════════════════════════════════════════════════════════════

def test_solo_el_titulo_participa_en_el_hash():
    """Cambiar contenido, url o fuente manteniendo los títulos NO cuenta como
    cambio: el hash se calcula exclusivamente sobre los títulos.
    # POSIBLE BUG (de diseño, intencional según el docstring del módulo): si
    # una fuente corrige el CUERPO de una nota sin tocar el título, el pipeline
    # se salta el ciclo. Se acepta como compromiso costo/beneficio (ahorro de
    # tokens), pero se documenta aquí explícitamente."""
    hasher = ContentHasher()
    hasher.has_changed([
        _noticia("Detienen a presunto extorsionador", contenido="v1", url="http://a", fuente="x"),
    ])

    cambio = hasher.has_changed([
        _noticia(
            "Detienen a presunto extorsionador",
            contenido="versión 2 totalmente reescrita",
            url="http://otro-dominio",
            fuente="otra fuente",
            source_type="gnews",
        ),
    ])

    assert cambio is False, (
        "Con títulos idénticos, cambios en contenido/url/fuente no participan del hash"
    )


# ════════════════════════════════════════════════════════════════════════════
# Contador de ciclos sin cambio
# ════════════════════════════════════════════════════════════════════════════

def test_contador_de_ciclos_sin_cambio_incrementa_y_se_reinicia():
    hasher = ContentHasher()
    lote = [_noticia("Vandalizan negocio en Guadalupe")]

    hasher.has_changed(lote)            # primera corrida
    hasher.has_changed(lote)            # sin cambio (1)
    hasher.has_changed(lote)            # sin cambio (2)
    assert hasher.consecutive_no_change == 2, (
        "Dos corridas idénticas consecutivas deben dejar el contador en 2"
    )

    hasher.has_changed([_noticia("Nuevo hecho en San Nicolás")])
    assert hasher.consecutive_no_change == 0, (
        "Al detectar cambio el contador debe reiniciarse a 0"
    )


def test_lote_vacio_es_consistente():
    """Dos corridas seguidas sin noticias: la primera es 'cambio' (no hay hash
    previo), la segunda ya no."""
    hasher = ContentHasher()

    primera = hasher.has_changed([])
    segunda = hasher.has_changed([])

    assert primera is True, "La primera corrida (aunque vacía) debe procesarse"
    assert segunda is False, "Dos lotes vacíos consecutivos son idénticos: sin cambio"
