# Fase A — Observabilidad del motor de recopilación de noticias

> **Actualizado 2026-04-19 post-merge:** nombres de campos alineados con el modelo real tras Op C de `INCONSISTENCIA_DASHBOARD.md`

## Objetivo general

El producto es un motor de recopilación asertiva de noticias. El caso de uso de Costco Monterrey es solo el primer escenario de validación. Esta fase construye la infraestructura para MEDIR qué tan bien funciona el motor hoy, antes de optimizarlo.

## Principio de diseño

No estamos construyendo producto final — estamos construyendo instrumentación para entender el sistema. Prioricen: simplicidad, visibilidad, feedback humano rápido.

## División del trabajo

Tres capas en paralelo, con un CONTRATO DE DATOS compartido que todas respetan.

### fase-a/pipeline (claude-1)
Script ejecutable end-to-end + logging estructurado de decisiones.

### fase-a/dashboard (claude-2)
Interfaz web para revisar cada decisión del motor con feedback humano.

### fase-a/metrics (claude-3)
Módulo de métricas + generador de reporte de calidad.

## Contrato de datos (OBLIGATORIO para los 3)

### Tabla `decision_log` (SQLAlchemy model, va en src/models/decision_log.py)

Cada vez que el motor procesa una noticia, se guarda UN registro con:

| Campo | Tipo | Descripción |
|---|---|---|
| id | int PK | auto |
| run_id | UUID | identifica una corrida completa del pipeline |
| created_at | datetime tz | cuándo se procesó |
| source_name | str | fuente de la noticia (milenio, info7, etc) |
| article_url | str unique | URL original |
| article_title | str | título |
| published_at | datetime tz nullable | fecha de publicación |
| article_content_snippet | text | primeras ~500 chars |
| stage_reached | enum | hasta dónde llegó: scraped, triage, deep_analysis, geolocation, dedup, notification, error |
| triage_passed | bool nullable | ¿pasó el triage inicial? |
| triage_reason | text nullable | por qué pasó o no |
| incident_type | str nullable | tipo del analyzer |
| severity_score | int nullable | 1-10 |
| ai_reasoning | text nullable | razonamiento del classifier |
| geo_address | str nullable | ubicación detectada |
| geo_lat | float nullable | |
| geo_lon | float nullable | |
| nearest_costco | str nullable | nombre de sucursal más cercana |
| nearest_costco_dist_m | float nullable | distancia en metros |
| within_radius | bool nullable | ¿dentro del radio de 3km? |
| is_duplicate | bool nullable | ¿el dedup lo marcó? |
| final_decision | enum | alerted, irrelevant, out_of_radius, duplicate, no_geo, error, pending |
| error_stage | str nullable | si falló, en qué etapa |
| error_message | text nullable | si falló, mensaje |
| total_tokens_input | int nullable | suma de tokens input LLM |
| total_tokens_output | int nullable | suma de tokens output LLM |
| total_latency_ms | int nullable | latencia total en ms |
| telegram_sent | bool default false | ¿se mandó alerta real? |

### Tabla `human_feedback` (va en src/models/human_feedback.py)

Se crea cuando tú revisas una decisión en el dashboard.

| Campo | Tipo | Descripción |
|---|---|---|
| id | int PK | |
| decision_log_id | FK → decision_log.id | decisión revisada |
| created_at | datetime tz | cuándo se revisó |
| was_correct | bool | ¿la decisión final fue correcta? |
| should_have_been | enum nullable | si estuvo mal: should_have_alerted, should_have_dismissed, wrong_type, wrong_severity, wrong_location |
| notes | text nullable | comentario libre |

## Base de datos para Fase A

Usar **SQLite local** (archivo `costco_motor.db` en la raíz). No PostgreSQL. Facilita testing y revisión.

Agregar migración Alembic nueva (`0002_add_decision_log_and_feedback.py`) con las 2 tablas.

La config debe permitir override fácil con `DATABASE_URL=sqlite+aiosqlite:///./costco_motor.db` en `.env`.

## Dependencias compartidas

- Todas las capas usan `aiosqlite` (agregar a pyproject.toml)
- Dashboard usa FastAPI (ya declarado) + `jinja2` + `python-multipart`
- Metrics puede usar `rich` para tablas bonitas en terminal

## Lo que NO se hace en Fase A

- No desplegamos nada
- No mandamos alertas reales por Telegram (el telegram.py se invoca pero con flag `dry_run=True` por default)
- No escribimos tests exhaustivos de integración — sí tests unitarios básicos por capa
- No refinamos el classifier — eso es Fase B
- No agregamos fuentes nuevas — eso es Fase posterior

## Criterios de aceptación

Al final de Fase A:

1. `python scripts/run_pipeline.py` corre una vez el motor contra fuentes reales y guarda todo en SQLite
2. `uvicorn src.dashboard.main:app --reload` levanta una web en localhost:8000 donde veo noticias procesadas
3. Puedo marcar 👍/👎 en cada decisión y el feedback se guarda
4. `python scripts/generate_report.py` produce `REPORTE_CALIDAD.md` con métricas precisas

## Orden de integración (post-desarrollo)

Igual que antes: fase-a/pipeline → fase-a/metrics → fase-a/dashboard. Pipeline primero porque los otros dos leen de su decision_log.
