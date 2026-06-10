"""
Tests de app/services/geo_service.py.

Cubren los fixes de Fase 1 (commit 34c83e7) que eliminaron falsos positivos geo:

  1. _check_roads SOLO marca cercanía si las coordenadas geocodificadas están
     dentro del radio del Costco (caso de auditoría: vialidad mencionada en el
     texto pero el evento real a ~78 km → NO es cercanía).
  2. ZONE_COORDS ya no tiene claves genéricas ("monterrey"/"centro") y el
     fallback de zona usa la coincidencia MÁS específica (clave más larga).
  3. Cálculo de distancia geodésica con coordenadas conocidas:
       Costco Valle Oriente ↔ centro de Monterrey  ≈ 4.65 km
       Costco Valle Oriente ↔ Saltillo             ≈ 72.63 km
       Costco Carr. Nacional ↔ Saltillo            ≈ 77.75 km (el "78 km" auditado)
  4. Casos frontera: texto sin ubicación; punto exactamente en el borde del radio.

Sin red: el geocoder externo (Nominatim) siempre va mockeado o sustituido por
un doble local. La lógica que se prueba es 100% local (geopy.geodesic es
cálculo matemático, no hace requests).
"""

from __future__ import annotations

from typing import Optional
from unittest import mock

import pytest
from geopy.distance import geodesic

from app.config.locations import COSTCO_LOCATIONS, get_active_locations
from app.domain.models import Coordinates, CostcoLocation
from app.domain.ports import GeocodingService
from app.services.geo_service import GeoService, NominatimGeocoder, ZONE_COORDS


# ── Coordenadas de referencia (valores verificados con geopy.geodesic) ──────
CENTRO_MONTERREY = (25.6866, -100.3161)  # centroide que Nominatim devuelve para "Monterrey"
SALTILLO = (25.4232, -101.0053)
RADIO_KM = 5.0


class GeocoderFalso(GeocodingService):
    """Doble de prueba: devuelve coordenadas fijas (o None) sin tocar la red."""

    def __init__(self, coords: Optional[tuple[float, float]]) -> None:
        self._coords = coords
        self.llamadas: list[str] = []

    def geocode(self, location_text: str) -> Optional[tuple[float, float]]:
        self.llamadas.append(location_text)
        return self._coords


def _servicio(coords: Optional[tuple[float, float]]) -> GeoService:
    """GeoService con las tiendas reales activas y un geocoder falso."""
    return GeoService(GeocoderFalso(coords), get_active_locations(), radius_km=RADIO_KM)


def _costco_sintetico(lat: float, lon: float, vialidades: list[str] | None = None) -> CostcoLocation:
    return CostcoLocation(
        nombre="Costco Sintético",
        coords=Coordinates(lat=lat, lon=lon),
        direccion="Dirección de prueba",
        activo=True,
        vialidades_clave=vialidades or [],
    )


# ════════════════════════════════════════════════════════════════════════════
# 1. Fix de _check_roads: la vialidad mencionada no basta si las coords
#    geocodificadas están lejos
# ════════════════════════════════════════════════════════════════════════════

def test_vialidad_mencionada_pero_evento_a_78_km_no_es_cercania():
    """Caso reproducido de la auditoría: una nota menciona 'carretera nacional'
    pero el evento se geocodifica en Saltillo (~78 km del Costco Carr. Nacional,
    ~72.6 km del Costco Valle Oriente). Antes del fix esto disparaba alerta."""
    servicio = _servicio(SALTILLO)

    resultado = servicio.check_proximity(
        location_text="Saltillo, Coahuila",
        full_text="Volcadura sobre la carretera nacional deja dos lesionados en Saltillo",
    )

    assert resultado.is_within_radius is False, (
        "Una vialidad mencionada en el texto NO debe marcar cercanía cuando las "
        "coordenadas geocodificadas están a ~78 km del Costco"
    )
    assert resultado.matched_via != "vialidad", (
        "El match por vialidad debió descartarse por la distancia real"
    )
    # El resultado debe reportar el Costco más cercano con su distancia real
    assert resultado.distancia_km > RADIO_KM, (
        f"La distancia reportada ({resultado.distancia_km} km) debe ser la real, "
        "muy por encima del radio"
    )
    assert 70.0 <= resultado.distancia_km <= 80.0, (
        f"Saltillo está a ~72.6 km del Costco más cercano (Valle Oriente); "
        f"se reportó {resultado.distancia_km} km"
    )


def test_check_roads_acepta_vialidad_si_coords_estan_dentro_del_radio():
    """Si las coords geocodificadas SÍ caen dentro del radio, la vialidad
    mencionada es señal válida y la distancia reportada es la real (no 0.5)."""
    servicio = _servicio(None)
    # Punto a ~1 km del Costco Valle Oriente
    punto_cercano = (25.6540, -100.3260)
    dist_esperada = geodesic(punto_cercano, (25.6455, -100.3255)).kilometers

    resultado = servicio._check_roads(
        "Persecución sobre lázaro cárdenas a la altura de valle oriente",
        coords=punto_cercano,
    )

    assert resultado.is_within_radius is True, (
        "Vialidad mencionada + coords dentro del radio debe contar como cercanía"
    )
    assert resultado.matched_via == "vialidad", "El match debió etiquetarse como 'vialidad'"
    assert abs(resultado.distancia_km - dist_esperada) <= 0.5, (
        f"Con coords disponibles la distancia debe ser la real (~{dist_esperada:.2f} km), "
        f"no el placeholder 0.5; se obtuvo {resultado.distancia_km} km"
    )


def test_check_roads_only_sin_coords_usa_la_mencion_como_unica_senal():
    """Sin coordenadas (la IA no extrajo ubicación), la mención de una vialidad
    clave sigue contando, con distancia simbólica 0.5 km y coords del Costco."""
    servicio = _servicio(None)

    resultado = servicio.check_roads_only(
        "Asalto a transeúnte en avenida lázaro cárdenas frente a plaza"
    )

    assert resultado.is_within_radius is True, (
        "La mención de una vialidad clave sin coords debe marcar cercanía"
    )
    assert resultado.matched_via == "vialidad", "El match debió ser por vialidad"
    assert resultado.distancia_km == 0.5, (
        "Sin coords, la distancia es el placeholder documentado de 0.5 km"
    )
    assert resultado.costco_nombre == "Costco Valle Oriente", (
        "'lázaro cárdenas' es vialidad clave del Costco Valle Oriente"
    )
    assert resultado.event_coords is not None, (
        "Sin coords del evento se usan las del Costco como aproximación"
    )


def test_texto_sin_vialidades_no_marca_cercania():
    """check_roads_only con texto que no menciona ninguna vialidad clave."""
    servicio = _servicio(None)

    resultado = servicio.check_roads_only("Detienen a sospechoso en Tampico, Tamaulipas")

    assert resultado.is_within_radius is False, (
        "Texto sin vialidades clave no debe marcar cercanía"
    )
    assert resultado.matched_via == "", "No debió haber ningún tipo de match"


# ════════════════════════════════════════════════════════════════════════════
# 2. Fix de ZONE_COORDS: sin claves genéricas y matching por la más específica
# ════════════════════════════════════════════════════════════════════════════

def test_zone_coords_no_contiene_claves_genericas():
    """El fix eliminó 'monterrey' y 'centro': su centroide cae dentro del radio
    de Costco Valle Oriente y generaba alertas falsas para CUALQUIER nota que
    mencionara la ciudad."""
    assert "monterrey" not in ZONE_COORDS, (
        "ZONE_COORDS no debe tener la clave genérica 'monterrey' (falsos positivos)"
    )
    assert "centro" not in ZONE_COORDS, (
        "ZONE_COORDS no debe tener la clave genérica 'centro' (falsos positivos)"
    )


def test_zone_coords_solo_tiene_zonas_especificas_fuera_o_dentro_pero_intencionales():
    """Ninguna clave del fallback debe ser un sustring genérico de la ciudad.
    Todas deben ser municipios/zonas concretas."""
    for clave in ZONE_COORDS:
        assert "monterrey" not in clave, (
            f"La clave '{clave}' reintroduce el genérico 'monterrey' en el fallback"
        )


def test_fallback_de_zona_usa_la_coincidencia_mas_especifica():
    """Con claves traslapadas, gana la MÁS larga: 'san pedro garza garcía'
    debe ganarle a 'garza garcía' y a 'san pedro'. Se usa un diccionario
    sintético con coordenadas distintas por clave para poder distinguir
    cuál ganó (en el real las tres claves de San Pedro comparten coords)."""
    zonas_sinteticas = {
        "san pedro": (1.0, 1.0),
        "garza garcía": (2.0, 2.0),
        "san pedro garza garcía": (3.0, 3.0),
    }

    with mock.patch("app.services.geo_service.Nominatim") as nominatim_cls:
        # Nominatim mockeado: nunca toca red y "falla" para forzar el fallback
        nominatim_cls.return_value.geocode.return_value = None
        geocoder = NominatimGeocoder()

        with mock.patch.dict(
            "app.services.geo_service.ZONE_COORDS", zonas_sinteticas, clear=True
        ):
            coords = geocoder.geocode("balacera en san pedro garza garcía, NL")

    assert coords == (3.0, 3.0), (
        f"Debió ganar la clave más específica 'san pedro garza garcía'; "
        f"se obtuvo {coords}"
    )


def test_texto_monterrey_generico_no_geolocaliza_por_fallback():
    """'Monterrey' a secas ya no tiene entrada en el fallback: si Nominatim
    falla, geocode() debe devolver None en vez de un centroide que caía dentro
    del radio de Valle Oriente."""
    with mock.patch("app.services.geo_service.Nominatim") as nominatim_cls:
        nominatim_cls.return_value.geocode.return_value = None
        geocoder = NominatimGeocoder()

        coords = geocoder.geocode("Monterrey")

    assert coords is None, (
        "Un texto genérico 'Monterrey' sin zona específica no debe resolverse "
        "por el fallback de ZONE_COORDS"
    )


def test_nota_generica_de_monterrey_no_cae_en_radio_de_valle_oriente():
    """Pipeline completo con geocoder que no resuelve: una nota que solo dice
    'Monterrey' y no menciona vialidades clave NO debe marcar cercanía."""
    servicio = _servicio(None)  # geocoder no resuelve nada

    resultado = servicio.check_proximity(
        location_text="Monterrey",
        full_text="Reportan riña en un bar de Monterrey; hay tres detenidos",
    )

    assert resultado.is_within_radius is False, (
        "Una nota genérica de 'Monterrey' sin zona ni vialidad no debe geolocalizar "
        "dentro del radio de ningún Costco"
    )
    assert resultado.costco_nombre == "", (
        "Sin coords ni vialidad no debe asociarse ningún Costco"
    )


def test_geocodificador_si_consulta_nominatim_antes_del_fallback():
    """El fallback de zona solo aplica cuando Nominatim falla; si Nominatim
    resuelve, se usan sus coordenadas precisas."""
    with mock.patch("app.services.geo_service.Nominatim") as nominatim_cls:
        resultado_nominatim = mock.Mock(latitude=25.65, longitude=-100.33)
        nominatim_cls.return_value.geocode.return_value = resultado_nominatim
        geocoder = NominatimGeocoder()

        coords = geocoder.geocode("Av Lázaro Cárdenas 800, San Pedro")

    assert coords == (25.65, -100.33), (
        "Con Nominatim disponible deben usarse sus coordenadas precisas, "
        "no el fallback de zona"
    )


def test_fallback_de_zona_aplica_tambien_cuando_nominatim_lanza_excepcion():
    """El camino real de fallo de Nominatim en producción es una excepción
    (timeout, GeocoderUnavailable), no un None silencioso: el `except` del
    geocoder debe absorberla en ambos intentos (con y sin sufijo) y aun así
    resolver por zona."""
    with mock.patch("app.services.geo_service.Nominatim") as nominatim_cls:
        nominatim_cls.return_value.geocode.side_effect = RuntimeError(
            "timeout sintético de Nominatim"
        )
        geocoder = NominatimGeocoder()

        coords = geocoder.geocode("operativo en Santa Catarina")

    assert coords == ZONE_COORDS["santa catarina"], (
        "Si Nominatim LANZA (no solo devuelve None), el fallback de zona debe "
        f"seguir resolviendo 'santa catarina'; se obtuvo {coords}"
    )
    assert nominatim_cls.return_value.geocode.call_count == 2, (
        "Deben intentarse los dos sufijos de geocodificación antes del fallback"
    )


# ════════════════════════════════════════════════════════════════════════════
# 3. Cálculo de distancia con coordenadas conocidas
# ════════════════════════════════════════════════════════════════════════════

def test_distancia_centro_monterrey_a_costco_valle_oriente():
    """El centroide de Monterrey está a ~4.65 km del Costco Valle Oriente
    (dentro del radio de 5 km — justo por eso el genérico era peligroso)."""
    servicio = _servicio(CENTRO_MONTERREY)

    resultado = servicio.check_proximity(
        location_text="Macroplaza, Monterrey",
        # El texto también menciona una vialidad: el match por geocoding
        # (Estrategia 1) debe ganar y etiquetarse como tal.
        full_text="Choque en el centro, cerca de lázaro cárdenas",
    )

    assert resultado.is_within_radius is True, (
        "El centro de Monterrey (~4.65 km) está dentro del radio de 5 km de Valle Oriente"
    )
    assert resultado.costco_nombre == "Costco Valle Oriente", (
        f"El Costco dentro del radio es Valle Oriente; se obtuvo '{resultado.costco_nombre}'"
    )
    assert abs(resultado.distancia_km - 4.65) <= 0.5, (
        f"Distancia centro MTY ↔ Costco Valle Oriente esperada ≈4.65 km (±0.5); "
        f"se obtuvo {resultado.distancia_km} km"
    )
    assert resultado.matched_via == "geocoding", (
        "Con coords dentro del radio el match debe ser por geocoding, no por vialidad"
    )
    assert resultado.event_coords is not None and resultado.event_coords.as_tuple() == CENTRO_MONTERREY, (
        "El resultado debe conservar las coordenadas del evento"
    )


def test_distancia_saltillo_a_costco_valle_oriente():
    """Saltillo está a ~72.63 km del Costco Valle Oriente (el más cercano de
    los activos) y a ~77.75 km del de Carretera Nacional: fuera de radio."""
    servicio = _servicio(SALTILLO)

    resultado = servicio.check_proximity(
        location_text="Saltillo, Coahuila",
        full_text="Aseguran vehículo robado en Saltillo",  # sin vialidades clave
    )

    assert resultado.is_within_radius is False, (
        "Saltillo (~72.6 km) está muy fuera del radio de 5 km"
    )
    assert resultado.costco_nombre == "Costco Valle Oriente", (
        "El Costco activo más cercano a Saltillo es Valle Oriente "
        f"(72.6 km vs 77.7 km de Carr. Nacional); se obtuvo '{resultado.costco_nombre}'"
    )
    assert abs(resultado.distancia_km - 72.63) <= 0.5, (
        f"Distancia Saltillo ↔ Costco Valle Oriente esperada ≈72.63 km (±0.5); "
        f"se obtuvo {resultado.distancia_km} km"
    )


def test_distancias_de_referencia_de_las_tiendas_activas():
    """Sanidad de configuración: las coordenadas de las dos tiendas activas en
    locations.py producen las distancias documentadas en la auditoría."""
    activos = {loc.nombre: loc for loc in get_active_locations()}
    assert "Costco Valle Oriente" in activos, "Valle Oriente debe estar activo"
    assert "Costco Carretera Nacional" in activos, "Carr. Nacional debe estar activo"

    vo = activos["Costco Valle Oriente"].coords.as_tuple()
    cn = activos["Costco Carretera Nacional"].coords.as_tuple()

    assert abs(geodesic(vo, CENTRO_MONTERREY).kilometers - 4.65) <= 0.5, (
        "Costco Valle Oriente debe estar a ≈4.65 km del centro de Monterrey"
    )
    assert abs(geodesic(cn, SALTILLO).kilometers - 77.75) <= 0.5, (
        "Costco Carr. Nacional debe estar a ≈77.75 km de Saltillo (el caso '78 km')"
    )


# ════════════════════════════════════════════════════════════════════════════
# 4. Casos frontera
# ════════════════════════════════════════════════════════════════════════════

def test_texto_sin_ubicacion_devuelve_resultado_vacio():
    """Geocoder sin resultado + texto sin vialidades → ProximityResult neutro."""
    servicio = _servicio(None)

    resultado = servicio.check_proximity(
        location_text="",
        full_text="Capturan a presunto responsable; investigación en curso",
    )

    assert resultado.is_within_radius is False, "Sin ubicación no puede haber cercanía"
    assert resultado.costco_nombre == "", "Sin ubicación no debe asociarse ningún Costco"
    assert resultado.distancia_km == 0.0, "Sin ubicación la distancia debe quedar en 0.0"
    assert resultado.event_coords is None, "Sin ubicación no debe haber coords del evento"


def test_ubicacion_exactamente_en_el_borde_del_radio_cuenta_como_dentro():
    """La comparación es inclusiva (dist <= radio): un punto exactamente a
    5.0 km del Costco debe contar como dentro del radio."""
    base = (25.0, -100.0)
    costco = _costco_sintetico(*base)
    punto_borde = geodesic(kilometers=RADIO_KM).destination(base, bearing=0)
    geocoder = GeocoderFalso((punto_borde.latitude, punto_borde.longitude))
    servicio = GeoService(geocoder, [costco], radius_km=RADIO_KM)

    resultado = servicio.check_proximity("punto en el borde", "sin vialidades")

    assert resultado.is_within_radius is True, (
        "Un punto exactamente a 5.0 km debe contar como dentro (comparación <=)"
    )
    assert abs(resultado.distancia_km - RADIO_KM) <= 0.01, (
        f"La distancia en el borde debe reportarse ≈{RADIO_KM} km; "
        f"se obtuvo {resultado.distancia_km} km"
    )


def test_ubicacion_apenas_fuera_del_radio_cuenta_como_fuera():
    """Un punto a 5.05 km (apenas pasado el borde) debe quedar fuera, y el
    resultado debe reportar igualmente cuál es el Costco más cercano."""
    base = (25.0, -100.0)
    costco = _costco_sintetico(*base)
    punto_fuera = geodesic(kilometers=RADIO_KM + 0.05).destination(base, bearing=0)
    geocoder = GeocoderFalso((punto_fuera.latitude, punto_fuera.longitude))
    servicio = GeoService(geocoder, [costco], radius_km=RADIO_KM)

    resultado = servicio.check_proximity("punto apenas fuera", "sin vialidades")

    assert resultado.is_within_radius is False, (
        "Un punto a 5.05 km debe quedar fuera del radio de 5.0 km"
    )
    assert resultado.costco_nombre == costco.nombre, (
        "Aun fuera de radio debe reportarse el Costco más cercano"
    )
    assert resultado.distancia_km > RADIO_KM, (
        f"La distancia reportada debe superar el radio; se obtuvo {resultado.distancia_km} km"
    )


def test_solo_se_monitorean_tiendas_activas():
    """Sanidad de configuración: get_active_locations() filtra activo=True.
    Sendero (en construcción) y Cumbres (fuera de alcance) no deben entrar."""
    activos = get_active_locations()
    nombres = {loc.nombre for loc in activos}

    assert all(loc.activo for loc in activos), "Todas las tiendas activas deben tener activo=True"
    assert "Costco Sendero (Escobedo)" not in nombres, (
        "Sendero está en construcción (activo=False) y no debe monitorearse"
    )
    assert "Costco Cumbres" not in nombres, (
        "Cumbres está fuera del alcance actual (activo=False)"
    )
    assert len(activos) < len(COSTCO_LOCATIONS), (
        "Debe haber al menos una tienda inactiva filtrada"
    )
