"""
Keyword dictionaries for news categorization.

Used as hints for the AI triage — NOT as hard filters.
The AI makes the final relevance decision.
"""

IMPACT_KEYWORDS: dict[str, list[str]] = {
    "accidente_vial": [
        "choque", "accidente", "volcadura", "atropello", "colisión",
        "vuelco", "chocó", "volcó", "carambola", "tráiler",
        "cierre de avenida", "cierre de carretera", "tránsito cerrado",
        "lesionados en accidente", "heridos en choque", "vehículos involucrados",
    ],
    "incendio": [
        "incendio", "fuego", "llamas", "arde", "bomberos",
        "humo denso", "conflagración", "edificio en llamas",
        "local en llamas", "vehículo en llamas",
    ],
    "seguridad": [
        "balacera", "disparos", "tiroteo", "persecución",
        "enfrentamiento", "baleado", "herido de bala", "hombres armados",
        "detonaciones", "rafagas", "ráfagas", "fuego cruzado",
        "resguardo policial", "acordonamiento", "zona acordonada",
    ],
    "bloqueo": [
        "bloqueo", "cierre", "cerrada", "manifestación", "protesta",
        "obstrucción", "tránsito cerrado", "bloqueada", "cerrado",
    ],
    "desastre_natural": [
        "inundación", "desbordamiento", "deslizamiento", "deslave",
        "tromba", "granizada", "tornado", "río desbordado",
    ],
}

EXCLUSION_KEYWORDS: list[str] = [
    # Entertainment / celebrity news
    "actor", "actriz", "famoso", "celebridad", "artista", "cantante",
    "película", "serie", "concierto", "show", "estreno",
    # Historical / past events
    "hace años", "en el pasado", "recordamos", "aniversario",
    "historia de", "así fue", "revelan detalles",
    # General politics (not relevant to operations)
    "declaraciones", "conferencia de prensa", "anuncia", "promete",
    "implementará", "planea", "propone",
    # Distant locations (clearly outside monitoring zone)
    "pesquería", "cadereyta", "santiago", "allende", "montemorelos",
    "ciudad de méxico", "cdmx", "guanajuato", "jalisco", "tamaulipas",
]


def check_high_impact(text: str) -> tuple[bool, str | None]:
    """
    Check if text contains high-impact keywords.

    Returns:
        (has_impact, category_name) — category is None if no match.
    """
    text_lower = text.lower()

    # Exclusions first
    for word in EXCLUSION_KEYWORDS:
        if word in text_lower:
            return False, None

    # Check impact keywords
    for category, words in IMPACT_KEYWORDS.items():
        for word in words:
            if word in text_lower:
                return True, category

    return False, None
