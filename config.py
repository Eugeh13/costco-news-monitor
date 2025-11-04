"""
Archivo de configuración para el sistema de monitoreo de noticias de alto impacto
en Monterrey, Nuevo León.
"""

# Coordenadas de las sucursales de Costco en Monterrey
COSTCO_LOCATIONS = {
    "Costco Carretera Nacional": {
        "lat": 25.5781498,
        "lon": -100.2512201,
        "direccion": "Carretera Nacional Km. 268 +500 5001, Monterrey, NL 64989",
        "vialidades_clave": [
            "carretera nacional", "carr. nacional", "carr nacional",
            "lincoln", "constitución", "prol. constitución",
            "prolongación constitución", "ruiz cortines", "adolfo ruiz cortines"
        ]
    },
    "Costco Cumbres": {
        "lat": 25.7295984,
        "lon": -100.3927985,
        "direccion": "Alejandro de Rodas 6767, Monterrey, NL 64344",
        "vialidades_clave": [
            "alejandro de rodas", "de rodas", "rodas",
            "raúl rangel frías", "rangel frías", "rangel frias",
            "cumbres", "paseo de los leones", "leones",
            "san jerónimo", "san jeronimo"
        ]
    },
    "Costco Valle Oriente": {
        "lat": 25.6396949,
        "lon": -100.317631,
        "direccion": "Av. Lázaro Cárdenas 800, San Pedro Garza García, NL 66269",
        "vialidades_clave": [
            "lázaro cárdenas", "lazaro cardenas", "cardenas",
            "fundadores", "av. fundadores", "avenida fundadores",
            "vasconcelos", "josé vasconcelos", "jose vasconcelos",
            "valle oriente", "valle", "san pedro", "garza garcía",
            "gómez morín", "gomez morin", "morones prieto"
        ]
    }
}

# Radio de búsqueda en kilómetros (reducido para mayor precisión)
RADIUS_KM = 3.0

# Palabras clave para cada categoría de noticia de alto impacto
KEYWORDS = {
    "accidente_vial": [
        "choque", "accidente", "volcadura", "atropello", "colisión", 
        "vuelco", "chocó", "volcó", "carambola", "tráiler",
        "cierre de avenida", "cierre de carretera", "tránsito cerrado",
        "lesionados en accidente", "heridos en choque", "vehículos involucrados"
    ],
    "incendio": [
        "incendio", "fuego", "llamas", "arde", "bomberos",
        "humo denso", "conflagración", "edificio en llamas",
        "local en llamas", "vehículo en llamas"
    ],
    "seguridad": [
        "balacera", "disparos", "tiroteo", "persecución", 
        "enfrentamiento", "baleado", "herido de bala", "hombres armados",
        "detonaciones", "rafagas", "ráfagas", "fuego cruzado",
        "resguardo policial", "acordonamiento", "zona acordonada"
    ],
    "bloqueo": [
        "bloqueo", "cierre", "cerrada", "manifestación", "protesta",
        "obstrucción", "tránsito cerrado", "bloqueada", "cerrado"
    ],
    "desastre_natural": [
        "inundación", "desbordamiento", "deslizamiento", "deslave",
        "tromba", "granizada", "tornado", "río desbordado"
    ]
}

# Palabras/frases que indican que NO es una noticia relevante (filtro de exclusión)
EXCLUSION_KEYWORDS = [
    # Noticias de espectáculos/farándula
    "actor", "actriz", "famoso", "celebridad", "artista", "cantante",
    "película", "serie", "concierto", "show", "estreno",
    
    # Noticias históricas/pasadas
    "hace años", "en el pasado", "recordamos", "aniversario",
    "historia de", "así fue", "revelan detalles",
    
    # Noticias políticas generales
    "declaraciones", "conferencia de prensa", "anuncia", "promete",
    "implementará", "planea", "propone",
    
    # Ubicaciones muy lejanas
    "pesquería", "cadereyta", "santiago", "allende", "montemorelos",
    "ciudad de méxico", "cdmx", "guanajuato", "jalisco", "tamaulipas"
]

# Fuentes de noticias
NEWS_SOURCES = [
    {
        "nombre": "Milenio Última Hora",
        "url": "https://www.milenio.com/ultima-hora",
        "tipo": "milenio"
    },
    {
        "nombre": "Milenio Monterrey",
        "url": "https://www.milenio.com/monterrey",
        "tipo": "milenio"
    },
    {
        "nombre": "INFO 7",
        "url": "https://www.info7.mx/",
        "tipo": "generic"
    },
    {
        "nombre": "El Horizonte",
        "url": "https://www.elhorizonte.mx/",
        "tipo": "generic"
    }
]

# Cuentas de Twitter/X para monitorear
TWITTER_ACCOUNTS = [
    # Cuentas generales de Monterrey
    {
        "handle": "pc_mty",
        "nombre": "Protección Civil Monterrey",
        "url": "https://twitter.com/pc_mty",
        "zona": "General"
    },
    {
        "handle": "mtytrafico",
        "nombre": "Tráfico MTY",
        "url": "https://twitter.com/mtytrafico",
        "zona": "General"
    },
    {
        "handle": "seguridadmtymx",
        "nombre": "Seguridad Monterrey",
        "url": "https://twitter.com/seguridadmtymx",
        "zona": "General"
    },
    {
        "handle": "QueSucedeEnMty",
        "nombre": "Que Sucede en Monterrey",
        "url": "https://twitter.com/QueSucedeEnMty",
        "zona": "General"
    },
    
    # Cuentas específicas de Carretera Nacional
    {
        "handle": "Kilometro264",
        "nombre": "Carretera Nacional",
        "url": "https://twitter.com/Kilometro264",
        "zona": "Carretera Nacional"
    },
    {
        "handle": "GN_Carreteras",
        "nombre": "Guardia Nacional Carreteras",
        "url": "https://twitter.com/GN_Carreteras",
        "zona": "Carretera Nacional"
    },
    
    # Cuentas específicas de Cumbres / San Pedro
    {
        "handle": "SSPCMonterrey",
        "nombre": "Seguridad y Protección Ciudadana",
        "url": "https://twitter.com/SSPCMonterrey",
        "zona": "Cumbres"
    },
    {
        "handle": "Rescate911SP",
        "nombre": "Rescate 911 San Pedro",
        "url": "https://twitter.com/Rescate911SP",
        "zona": "Cumbres / Valle Oriente"
    },
    
    # Cuentas específicas de Valle Oriente / Lázaro Cárdenas
    {
        "handle": "TraficoenMty",
        "nombre": "Tráfico en Monterrey",
        "url": "https://twitter.com/TraficoenMty",
        "zona": "Valle Oriente / Lázaro Cárdenas"
    },
    {
        "handle": "SanPedroNL",
        "nombre": "Municipio de San Pedro",
        "url": "https://twitter.com/SanPedroNL",
        "zona": "Valle Oriente"
    }
]




# Configuración de notificaciones
NOTIFICATION_CONFIG = {
    "console": True,
    "telegram": True
}



# Archivo para almacenar noticias ya procesadas
PROCESSED_NEWS_FILE = "processed_news.txt"

