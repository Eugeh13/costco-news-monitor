# Documentación del Sistema: Costco News Monitor

## Propósito del Proyecto
Sistema de monitoreo de incidentes de alto impacto (accidentes viales, incendios, situaciones de seguridad, desastres naturales, etc.) cerca de sucursales de Costco en la zona metropolitana de Monterrey, NL.

Utiliza IA avanzada (LLMs como OpenAI/Anthropic) para leer, interpretar y geolocalizar noticias en tiempo real, evaluando su severidad e impacto en el tráfico.

## Ubicaciones Activas
1. **Costco Carretera Nacional**: Km 268+500, Bosques de Valle Alto, Monterrey.
2. **Costco Valle Oriente**: Av Lázaro Cárdenas 800, San Pedro Garza García.
3. **Costco Sendero (Escobedo)**: Inactivo temporalmente (en construcción).
4. **Costco Cumbres**: Inactivo (fuera de scope).

## Arquitectura del Sistema (Clean Architecture)

El sistema pasó de una "God Class" monolítica (`main_ai.py`) a una **Clean Architecture**. Todo el código fuente está alojado en `app/`.

### Estructura de Directorios

```text
costco-news-monitor/
├── app/
│   ├── domain/                  # Modelos Pydantic v2 (Alert, NewsItem) e interfaces abstractas. NINGUNA dependencia externa.
│   ├── config/                  # Módulos de configuración (Settings, Locations, Keywords).
│   ├── infrastructure/          # Conexiones con el mundo exterior:
│   │   ├── ai/                  # OpenAI & Anthropic Providers, Prompts (Sistema/Usuario).
│   │   ├── notifications/       # Telegram Notifier.
│   │   ├── persistence/         # PostgreSQL Repository & FileStorage (deduplicación).
│   │   └── sources/             # Google RSS, GNews, RSS Directo, y DeepReader (Crawl4AI/Newspaper).
│   ├── services/                # Lógica del negocio: Geocoding (GeoService), Hasher, Triage, Deep Analysis, y Pipeline principal.
│   └── api/                     # REST API FastAPI (Endpoints para el Dashboard: /api/incidents, /api/locations, /api/stats, /health).
├── docs/                        # Documentación complementaria.
├── main.py                      # Punto de entrada para ejecución única. Conecta las dependencias de la arquitectura.
├── scheduler.py                 # Worker daemon. Funciona con Smart Polling e implementa el Modo Nocturno (23:00 a 06:00 CST).
├── server.py                    # Levanta FastAPI (uvicorn) en el hilo principal y el `scheduler.py` como background daemon thread. (Usado por Railway).
├── Procfile                     # Configuración de despliegue para Railway.
├── nixpacks.toml                # Instrucciones de compilación para Railway.
├── requirements.txt             # Dependencias optimizadas.
└── .env                         # Variables de entorno.
```

## Patrones de Diseño Utilizados

1. **Inyección de Dependencias**: El archivo `main.py` actúa como la *Composition Root*. Allí se instancian las clases concretas (e.g. `OpenAIProvider`, `PostgresRepository`) y se inyectan en los servicios y el `MonitoringPipeline`. El Pipeline no sabe qué proveedor de IA está usando, sólo sabe que tiene un objeto que cumple la interfaz de `AIProvider`.
2. **Puertos y Adaptadores**: `app/domain/ports.py` dicta cómo deben interactuar todos los servicios externos (AI, Database, Notifiers).
3. **Smart Polling (Content Hasher)**: Si el hash de las noticias extraídas es exacto al del ciclo anterior, el sistema espera y retrasa su próximo check (de 5 hasta 15 minutos), ahorrando el 100% del consumo de tokens y llamadas a la BD. En modo nocturno se apaga completamente.
4. **Resiliencia (Fallback Strategies)**:
    - Geo-localización: `NominatimGeocoder` intenta buscar geolocalización exacta, seguido por matching usando vialidades clave predefinidas, y finalmente detectando coordenadas de la zona municipal central.
    - Deep Read: Usa en orden jerárquico el Headless Browser de `Crawl4Ai` -> `Newspaper` -> API `GNews` -> `Requests/BeautifulSoup`.

## Before and After (Refactorización)

### Comparativa Arquitectural

| Componente | 🔴 Antes (Monolítico) | 🟢 Después (Clean Architecture) |
|------------|-----------------------|---------------------------------|
| **Orquestación** | `main_ai.py` (**God Class** de 500+ líneas). Manejaba scraping, IA, geolocalización, base de datos y envío de alertas. | `app/services/pipeline.py` (Solo orquesta). Delega responsibilities a servicios inyectados. No contiene lógica quemada. |
| **Modelos de Datos** | Diccionarios informales (`dict`) o clases dispersas en `scraper.py`. No proveían type safety. | **Pydantic v2** (`app/domain/models.py`). Estructuras fuertes con validación nativa (`NewsItem`, `Alert`, `AnalysisResult`). |
| **Fuentes de Noticias** | Agrupadas en if/else statements dentro de la clase base del scraper. Difíciles de testear o apagar independientemente. | `app/infrastructure/sources/`. 4 módulos independientes: `google_rss.py`, `gnews_source.py`, `rss_direct.py`, `deep_reader.py`. |
| **IA (OpenAI/Anthropic)** | Llamadas API + prompts quemados en strings largos dentro de `ai_analyzer.py`. | Uso de Interfaces (`AIProvider`). Prompts centralizados en `prompts.py`. Soporte nativo para OpenAI y Anthropic conectables/desconectables sin romper el código. |
| **Bases de Datos** | Conexiones psycopg2 directas (`database.py`) sin Context Managers. Múltiples errores y bloqueos por conexiones abiertas (repetición redundante de `conn.close()`). | Repositorio formal (`PostgresRepository`) cumpliendo contrato de Interfaz. Uso estricto de Context Managers para commits y rollbacks seguros. |
| **Consumo de Lógica/Tokens** | Ejecución ciega. Si fallaba o si no había noticias nuevas, forzaba análisis repitiendo y consumiendo tokens y ciclos de BD cada 30 minutos. | `ContentHasher` activo. Evalúa un hash en memoria, y si las noticias no cambiaron, detiene el pipeline en seco consumiendo **0 tokens** informando mediante "Smart Polling". |
| **Configuración y Entorno** | Importes regados de `dotenv` a través de 6 archivos y configuraciones duras en un gran archivo flat llamado `config.py`. | Centralización en `pydantic-settings` (`app/config/settings.py`) asegurando que el despliegue truene **antes** en start up si falta una variable de entorno crucial. |
| **Despliegue a la Nube / API** | Scripts de shell bash inoficiales y uso de crontabs que complicaban los contenedores Docker en Railway. | **FastAPI** activo. `server.py` carga API + Worker en paralelo controlados via el `Procfile`. Preparada para dar servicio a un frontend web a través de la API en `/api/*` y mantener el Worker escuchando de fondo. |

## Historial de Cambios Mayores
*Esta bitácora deberá ser actualizada por la IA de manera imperativa cada vez que se realicen modificaciones arquitectónicas o expansiones de funcionalidades.*

- **[02/Abr/2026 a 03/Abr/2026] Refactorización Extrema Hacia Clean Architecture**:
    - Disolución y borrado permanente de 11 flat files originales (ej: `main_ai.py`, `scraper.py`, `ai_analyzer.py`, `geolocation.py`, `database.py`, etc.).
    - Creación e implementación de Pydantic v2 en `domain/models.py`.
    - Eliminación del filtrado rígido por *Keywords*; ahora se utilizan como *"hints"* de contexto para el LLM.
    - Cambio a inyección de dependencias dictadas desde un solo Entry Point maestro (`main.py`).
    - Actualización predeterminada a `gpt-5-mini`.
    - Extracción, corrección, testeo y centralización de la lógica de ubicación (GeoService), garantizando el enfoque sobre Carretera Nacional, Valle Oriente y el área del próximo proyecto Sendero Escobedo.
- **[03/Abr/2026] Integración de Capa API (FastAPI) y Servidor Híbrido**:
    - Agregado de FastAPI en `app/api/` para servir un dashboard front-end futuro mediante abstracciones hacia la Base de Datos.
    - Creación de `server.py` que inicia la REST API como servidor `uvicorn` paralela al worker de recabo diario `scheduler.py` garantizando la concurrencia eficiente en la nube de Railway usando threads nativos.
    - Carga estricta de variables de entono para las operaciones del Procfile.
