"""
Costco store locations for Nuevo León.

Each location defines coordinates, address, and nearby road names
used for proximity matching when geocoding fails.
"""

from app.domain.models import Coordinates, CostcoLocation


COSTCO_LOCATIONS: list[CostcoLocation] = [
    CostcoLocation(
        nombre="Costco Carretera Nacional",
        coords=Coordinates(lat=25.5780, lon=-100.2510),
        direccion="Km 268+500, Carr Nacional 501, Bosques de Valle Alto, 64989 Monterrey, N.L.",
        activo=True,
        vialidades_clave=[
            "carretera nacional", "carr. nacional", "carr nacional",
            "bosques de valle alto", "valle alto",
            "lincoln", "constitución", "prol. constitución",
            "prolongación constitución", "ruiz cortines", "adolfo ruiz cortines",
            "km 268", "kilómetro 268",
        ],
    ),
    CostcoLocation(
        nombre="Costco Valle Oriente",
        coords=Coordinates(lat=25.6455, lon=-100.3255),
        direccion="Av Lázaro Cárdenas 800, Zona Valle Oriente, 66269 San Pedro Garza García, N.L.",
        activo=True,
        vialidades_clave=[
            "lázaro cárdenas", "lazaro cardenas", "lázaro cárdenas 800",
            "fundadores", "av. fundadores", "avenida fundadores",
            "vasconcelos", "josé vasconcelos", "jose vasconcelos",
            "valle oriente", "san pedro garza", "garza garcía",
            "gómez morín", "gomez morin", "morones prieto",
            "río la silla", "rio la silla",
        ],
    ),
    CostcoLocation(
        nombre="Costco Sendero (Escobedo)",
        coords=Coordinates(lat=25.7950, lon=-100.2780),
        direccion="Av Sendero Divisorio, Privadas de Anáhuac, Gral. Escobedo, N.L.",
        activo=False,  # Under construction — estimated opening: mid 2026
        vialidades_clave=[
            "sendero", "sendero divisorio", "av sendero",
            "privadas de anáhuac", "privadas de anahuac", "anáhuac",
            "escobedo", "general escobedo",
            "morenita mía", "morenita mia",
        ],
    ),
    CostcoLocation(
        nombre="Costco Cumbres",
        coords=Coordinates(lat=25.7296, lon=-100.3928),
        direccion="Alejandro de Rodas 6767, Cumbres, 64344 Monterrey, N.L.",
        activo=False,  # Not in current monitoring scope
        vialidades_clave=[
            "alejandro de rodas", "de rodas", "rodas",
            "rangel frías", "rangel frias", "cumbres",
            "paseo de los leones", "leones",
        ],
    ),
]


def get_active_locations() -> list[CostcoLocation]:
    """Returns only the Costco locations currently being monitored."""
    return [loc for loc in COSTCO_LOCATIONS if loc.activo]


def get_all_locations() -> list[CostcoLocation]:
    """Returns all locations (for the dashboard API)."""
    return COSTCO_LOCATIONS
