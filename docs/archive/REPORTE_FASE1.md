# Reporte de Integración — Fase 1

**Fecha:** 2026-04-19  
**Integrador:** v2-rewrite branch  
**Ramas revisadas:** `claude/1`, `claude/2`, `claude/3`  
**Estado:** Pre-merge — solo análisis, sin merges aplicados

---

## 1. Resumen por rama

### claude/1 — Infraestructura

| Métrica | Valor |
|---------|-------|
| Commits propios | 8 |
| Archivos tocados | 27 |
| Líneas añadidas | +1 204 |
| Líneas eliminadas | 0 |

**Commits:**

```
804b642  feat(tests): agregar test_config.py y test_models.py + fix log_level case-insensitive
646d55b  feat(alembic): init async-compatible + migración 0001_initial_schema
f4cda51  feat(schemas): agregar Pydantic v2 schemas Create/Read/Update
bd50969  feat(models): agregar modelos SQLAlchemy 2.x declarativos
8184df0  feat(core): agregar logger.py con structlog
04cba52  feat(core): agregar database.py con engine async SQLAlchemy 2.x
d3ba85c  feat(core): agregar config.py con Pydantic Settings v2
33c51ee  feat(infra): agregar pyproject.toml con dependencias del stack v2
```

**Archivos creados:**

```
pyproject.toml
alembic.ini / alembic/env.py / alembic/script.py.mako / alembic/README
alembic/versions/0001_initial_schema.py
src/__init__.py
src/core/__init__.py
src/core/config.py
src/core/database.py
src/core/logger.py
src/models/__init__.py  src/models/base.py
src/models/incident.py  src/models/alert.py
src/models/analysis_result.py  src/models/source.py
src/schemas/__init__.py  src/schemas/incident.py
src/schemas/alert.py  src/schemas/analysis_result.py
src/schemas/source.py
tests/__init__.py  tests/core/__init__.py
tests/core/test_config.py  tests/models/__init__.py
tests/models/test_models.py
```

---

### claude/2 — Scrapers

| Métrica | Valor |
|---------|-------|
| Commits propios | 6 |
| Archivos tocados | 17 |
| Líneas añadidas | +1 296 |
| Líneas eliminadas | 0 |

**Commits:**

```
d7b3db8  feat(scrapers): add tests/ suite + enforce timezone-aware published_at — 33/33 passing
5049299  feat(scrapers): add __init__.py — exports all scrapers + ALL_SCRAPERS registry
795e68f  feat(scrapers): add proteccion_civil.py + bomberos_nl.py — Google News RSS, 24h age filter
5f337d1  feat(scrapers): add info7.py + horizonte.py — RSS-first with HTML fallback
56dcdb3  feat(scrapers): add milenio.py — Última Hora + NL sections, selectolax, graceful fallback
dda9dda  feat(scrapers): add base.py — RawArticle model, BaseScraper ABC, httpx + tenacity retry
```

**Archivos creados:**

```
src/__init__.py
src/scrapers/__init__.py
src/scrapers/base.py
src/scrapers/_google_news_rss.py
src/scrapers/milenio.py
src/scrapers/info7.py
src/scrapers/horizonte.py
src/scrapers/proteccion_civil.py
src/scrapers/bomberos_nl.py
tests/__init__.py  tests/scrapers/__init__.py
tests/scrapers/fixtures.py  tests/scrapers/test_base.py
tests/scrapers/test_google_news_scrapers.py
tests/scrapers/test_horizonte.py
tests/scrapers/test_info7.py
tests/scrapers/test_milenio.py
```

---

### claude/3 — Analyzer + Notifier

| Métrica | Valor |
|---------|-------|
| Commits propios | 6 |
| Archivos tocados | 19 |
| Líneas añadidas | +1 352 |
| Líneas eliminadas | 0 |

**Commits:**

```
99b5ffa  feat(tests): add 51 tests for analyzer + notifier — mock Anthropic SDK, Nominatim, Telegram
883371b  feat(notifier): add async TelegramClient — MarkdownV2 alerts, inline keyboard, 429+5xx retry
640d23a  feat(analyzer): add semantic dedup — SHA-256 of normalised title+url, TTLCache 24h
ccae868  feat(analyzer): add geolocator — extract_locations (haiku), Nominatim geocode (1 req/s)
4d61af1  feat(analyzer): add async Classifier — triage (haiku) + deep_analyze (sonnet) + tenacity
73398da  feat(analyzer): add Pydantic v2 types — IncidentInput, IncidentClassification, GeoLocation
```

**Archivos creados:**

```
requirements.txt  pytest.ini
src/__init__.py
src/analyzer/__init__.py  src/analyzer/types.py
src/analyzer/classifier.py  src/analyzer/dedup.py
src/analyzer/geolocator.py
src/notifier/__init__.py  src/notifier/telegram.py
tests/__init__.py  tests/conftest.py
tests/analyzer/__init__.py  tests/analyzer/test_classifier.py
tests/analyzer/test_dedup.py  tests/analyzer/test_geolocator.py
tests/analyzer/test_types.py
tests/notifier/__init__.py  tests/notifier/test_telegram.py
```

---

## 2. Solapamiento entre ramas

### Archivos tocados por más de una rama

| Archivo | claude/1 | claude/2 | claude/3 | ¿Conflicto real? |
|---------|:--------:|:--------:|:--------:|------------------|
| `src/__init__.py` | ✓ | ✓ | ✓ | No — vacío en las 3 ramas |
| `tests/__init__.py` | ✓ | ✓ | ✓ | No — vacío en las 3 ramas |

**Conclusión:** No hay conflictos de contenido entre ramas. Todos los módulos nuevos van a rutas únicas. El merge será limpio en términos de git.

### Mapa de dominios sin solapamiento

```
claude/1  →  pyproject.toml, alembic/, src/core/, src/models/, src/schemas/
claude/2  →  src/scrapers/
claude/3  →  src/analyzer/, src/notifier/, requirements.txt, pytest.ini
```

---

## 3. Review de código por rama

### claude/1 — Infraestructura

#### ✅ Sólido

**`src/core/config.py`**
- Pydantic Settings v2 con `SettingsConfigDict(case_sensitive=False)` — correcto
- `field_validator("log_level", mode="before")` hace `.upper()` antes de parsear el enum — robusto
- `field_validator("database_url")` auto-coerce de `postgresql://` a `postgresql+asyncpg://` — evita errores silenciosos al configurar
- Secretos sólo vía variables de entorno o `.env`, nunca hardcodeados

**`src/core/database.py`**
- `lru_cache(maxsize=1)` en `_build_engine` y `_build_sessionmaker` — engine singleton correctamente implementado
- `pool_pre_ping=True` — recuperación automática ante conexiones muertas
- `expire_on_commit=False` — necesario para async con SA2
- `get_session` como FastAPI `Depends` con `try/commit/except/rollback` — patrón correcto

**`src/models/incident.py`**
- SA2 con `Mapped[T]` y `mapped_column` — tipado estricto
- `IncidentType`, `Severity`, `IncidentStatus` como `str(enum.Enum)` — serializables sin conversión extra
- `content_hash` con `unique=True, index=True` — base para dedup en DB (complementa dedup in-memory de claude/3)
- Relaciones con `cascade="all, delete-orphan"` apropiado

**`src/core/logger.py`**
- structlog configurado correctamente según stack obligatorio

**Migración Alembic**
- `0001_initial_schema.py` define los 4 enums PostgreSQL (`incidenttype`, `severity`, `incidentstatus`) + 4 tablas coherentes con los modelos SA2
- `downgrade()` elimina en orden correcto respetando FK

#### ⚠️ Le falta

- **`pyproject.toml` incompleto para claude/2:** faltan `feedparser>=6.0`, `pytz>=2024.1`, `selectolax>=0.3` — las dependencias que los scrapers usan y que no están declaradas. Sin esto `pip install -e .` produce un entorno roto.

---

### claude/2 — Scrapers

#### ✅ Sólido

**`src/scrapers/base.py`**
- `RawArticle` con `@field_validator("published_at")` que rechaza datetimes naive — garantiza que todo el pipeline trabaja con tz-aware
- `BaseScraper` ABC con `source_name` property + `fetch()` abstractos — contrato claro
- `_get()` con `@retry(retry_if_exception_type(...), stop_after_attempt(3), wait_exponential)` — resiliente sin sobrecarga

**`src/scrapers/_google_news_rss.py`**
- Helper compartido para `proteccion_civil` y `bomberos` — DRY correcto
- `_extract_outlet()` extrae el nombre del medio desde el título de Google News (`"Noticia - Milenio"` → `"Milenio"`) — detalle útil para trazabilidad

**`src/scrapers/info7.py` y `horizonte.py`**
- Patrón RSS-first → HTML fallback bien ejecutado
- Múltiples selectores CSS con fallback graceful (`_ARTICLE_SELECTORS`, `_TITLE_SELECTORS`) — resiliente a cambios de layout

**`src/scrapers/__init__.py`**
- `ALL_SCRAPERS: list[BaseScraper]` como registry — el loop de Phase 2 solo necesita iterar esta lista

**Tests**
- 33 tests con fixtures de HTML/RSS realistas — buena cobertura

#### ⚠️ Le falta

- **Sin filtro de keywords por relevancia:** los scrapers traen todo el contenido de las secciones (deportes, política, economía...). El filtrado queda delegado íntegramente al LLM — arquitecturalmente es válido, pero puede inflar costos de API en fuentes ruidosas como Info7.
- `feedparser`, `pytz`, `selectolax` no declarados en `pyproject.toml` (responsabilidad del integrador al mergear claude/1).

---

### claude/3 — Analyzer + Notifier

#### ✅ Sólido

**`src/analyzer/classifier.py`**
- Two-stage con modelos diferenciados: `claude-haiku-4-5-20251001` para triage (barato, rápido) y `claude-sonnet-4-6` para deep analyze (preciso) — diseño económicamente correcto
- `tool_choice={"type": "tool", "name": ...}` — fuerza output estructurado, elimina parsing frágil de texto libre
- `_is_5xx()` + tenacity solo reintenta en errores de servidor — no reintenta 4xx (auth, rate-limit) innecesariamente
- `triage()` devuelve `False` en ausencia de `tool_use` block — falla cerrada (safe default)

**`src/analyzer/dedup.py`**
- Normalización: lowercase → strip non-alpha → remove stopwords → stemming simple → sort stems → SHA-256
- Ordenar los stems antes del hash colapsa variaciones de orden de palabras al mismo digest
- `TTLCache(maxsize=10_000, ttl=86_400)` — 24h en memoria, costo cero, sin dependencia externa

**`src/analyzer/geolocator.py`**
- `asyncio.Lock` a nivel de módulo para respetar 1 req/s de Nominatim — correcto
- `is_within_radius()` y `distance_to_costcos()` como funciones puras sincrónicas — testeables sin mocks

**`src/notifier/telegram.py`**
- `TelegramClient` como async context manager — gestión de `httpx.AsyncClient` limpia
- `_esc()` con `frozenset` de caracteres MarkdownV2 — escapa correctamente
- Retry 429 respeta `retry_after` del header de Telegram — no hace flood ban

#### 🚨 Problemas críticos

**A) `IncidentType` incompatible con claude/1 — BLOQUEANTE en Phase 2**

Los valores del enum difieren entre capas:

| `src/analyzer/types.py` (claude/3) | `src/models/incident.py` (claude/1) |
|------------------------------------|--------------------------------------|
| `ACCIDENT = "accident"` | `accidente_vial = "accidente_vial"` |
| `FIRE = "fire"` | `incendio = "incendio"` |
| `SHOOTING = "shooting"` | `seguridad = "seguridad"` |
| `ROADBLOCK = "roadblock"` | `bloqueo = "bloqueo"` |
| `FLOOD = "flood"` | `desastre_natural = "desastre_natural"` |
| `OTHER = "other"` | `otro = "otro"` |

Cuando Phase 2 intente persistir un `IncidentClassification` en la tabla `incidents`, los valores del enum no pasarán la validación del tipo PostgreSQL. Requiere un mapper explícito o unificar los enums antes de mergear.

**B) Coordenadas de Costco incorrectas en `geolocator.py`**

Los valores hardcodeados no coinciden con los del `CLAUDE.md` (autoritativos):

| Sucursal | CLAUDE.md | `geolocator.py` | Delta aprox. |
|----------|-----------|-----------------|--------------|
| Carretera Nacional | 25.6026, -100.2640 | 25.5780, -100.2510 | ~2.8 km |
| Cumbres | 25.7353, -100.4022 | 25.7296, -100.3928 | ~1.0 km |
| Valle Oriente | 25.6457, -100.3072 | 25.6455, -100.3255 | ~1.6 km |

Con el radio de 3 km definido en el proyecto, un desplazamiento de 2.8 km puede filtrar incorrectamente incidentes reales cerca de Carretera Nacional.

#### ⚠️ Problemas menores

**`requirements.txt` — debe eliminarse**

Incluye dependencias prohibidas y legacy del stack v1:

```
openai>=1.0          # CLAUDE.md dice explícitamente NO OpenAI
twscrape==0.17.0     # stack v1, no pertenece a v2
newspaper3k>=0.2.8   # stack v1
crawl4ai>=0.2.0      # stack v1
playwright>=1.30     # stack v1
psycopg2-binary      # reemplazado por asyncpg en v2
gnews>=0.3.0         # stack v1
```

Además entra en conflicto directo con `pyproject.toml` (claude/1) para definir las dependencias del proyecto.

**`pytest.ini` — redundante**

Claude/1 ya define en `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```
El `pytest.ini` de claude/3 duplica esto. Al mergear existirán los dos y pytest usará `pytest.ini` con precedencia, ignorando `pyproject.toml` — comportamiento confuso.

**stdlib `logging` en lugar de `structlog`**

`classifier.py`, `geolocator.py` y `telegram.py` usan `import logging; logger = logging.getLogger(__name__)`. El stack definido en `CLAUDE.md` requiere `structlog`. Inconsistente con claude/1 y claude/2.

---

## 4. Orden de merge recomendado

```
claude/1  →  claude/2  →  claude/3
```

### Justificación

| Paso | Rama | Razón |
|------|------|-------|
| 1 | `claude/1` | Es la fundación: `pyproject.toml`, `Base` SA2, `Settings`, `database.py`. Ninguna otra rama puede instalarse sin esto. |
| 2 | `claude/2` | Los scrapers son completamente independientes del analyzer. Solo dependen de `httpx`, `structlog` y `tenacity` — todos declarados en pyproject.toml de claude/1. No tocan modelos ni schemas. |
| 3 | `claude/3` | El analyzer y notifier son la capa más alta. `src/analyzer/types.py` es auto-contenido (no importa desde claude/1 ni claude/2), pero conceptualmente consume la salida de los scrapers y produce datos para los modelos. |

---

## 5. Conflictos esperados y cómo resolverlos

### Conflicto 1 — `IncidentType` mismatch (CRÍTICO)

**Cuándo aparece:** Phase 2, al conectar el resultado del `Classifier` con la persistencia en DB.

**Archivos afectados:**
- `src/analyzer/types.py` — define `IncidentType` con valores en inglés
- `src/models/incident.py` — define `IncidentType` con valores en español
- `alembic/versions/0001_initial_schema.py` — enum PostgreSQL con valores en español

**Resolución:** Añadir un mapper en la capa de servicio (Phase 2). No modificar los enums existentes para no invalidar la migración ya generada ni los tests de cada rama.

```python
# src/services/incident_mapper.py  (a crear en Phase 2)
from src.analyzer.types import IncidentType as AnalyzerType
from src.models.incident import IncidentType as ModelType

_ANALYZER_TO_MODEL: dict[AnalyzerType, ModelType] = {
    AnalyzerType.ACCIDENT:  ModelType.accidente_vial,
    AnalyzerType.FIRE:      ModelType.incendio,
    AnalyzerType.SHOOTING:  ModelType.seguridad,
    AnalyzerType.ROADBLOCK: ModelType.bloqueo,
    AnalyzerType.FLOOD:     ModelType.desastre_natural,
    AnalyzerType.OTHER:     ModelType.otro,
}

def map_incident_type(analyzer_type: AnalyzerType) -> ModelType:
    return _ANALYZER_TO_MODEL[analyzer_type]
```

---

### Conflicto 2 — Coordenadas incorrectas en `geolocator.py` (CRÍTICO)

**Cuándo aparece:** En producción, silenciosamente — incidentes reales pueden quedar fuera del radio.

**Archivo afectado:** `src/analyzer/geolocator.py`, líneas del dict `COSTCO_LOCATIONS`

**Resolución:** Corregir antes o inmediatamente después de mergear claude/3:

```python
# Reemplazar en src/analyzer/geolocator.py
COSTCO_LOCATIONS: dict[str, tuple[float, float]] = {
    "Costco Carretera Nacional": (25.6026, -100.2640),  # CLAUDE.md autoritativo
    "Costco Cumbres":            (25.7353, -100.4022),
    "Costco Valle Oriente":      (25.6457, -100.3072),
}
```

---

### Conflicto 3 — `requirements.txt` vs `pyproject.toml`

**Cuándo aparece:** Al instalar el proyecto — dos fuentes de verdad para dependencias.

**Resolución:** Eliminar `requirements.txt` después de mergear claude/3:

```bash
git rm requirements.txt
```

Si se quiere mantener como referencia de instalación rápida, reemplazarlo por uno mínimo que delegue al pyproject:

```
# requirements.txt (solo para entornos sin pip editable install)
-e .
```

---

### Conflicto 4 — `pytest.ini` duplicado

**Cuándo aparece:** Al correr `pytest` — `pytest.ini` tiene precedencia sobre `pyproject.toml` y puede causar comportamiento inconsistente.

**Resolución:** Eliminar `pytest.ini` después de mergear claude/3:

```bash
git rm pytest.ini
```

La configuración en `pyproject.toml` de claude/1 es equivalente y más completa.

---

### Conflicto 5 — Dependencias de scrapers ausentes en `pyproject.toml`

**Cuándo aparece:** Al instalar y correr los scrapers de claude/2.

**Resolución:** Después de mergear claude/1, editar `pyproject.toml` antes de mergear claude/2:

```toml
# Añadir a [project] dependencies en pyproject.toml
"feedparser>=6.0",
"pytz>=2024.1",
"selectolax>=0.3",
```

---

### Conflicto 6 — stdlib `logging` en claude/3 (menor)

**Cuándo aparece:** En observabilidad — los logs del analyzer y notifier no seguirán el formato estructurado del resto del sistema.

**Resolución:** Reemplazar en `classifier.py`, `geolocator.py`, `telegram.py` post-merge:

```python
# Reemplazar
import logging
logger = logging.getLogger(__name__)

# Por
import structlog
logger = structlog.get_logger(__name__)
```

---

## 6. Resumen ejecutivo

| # | Severidad | Problema | Rama | Acción |
|---|-----------|----------|------|--------|
| 1 | 🚨 Crítico | `IncidentType` enum incompatible DB ↔ analyzer | claude/1 + claude/3 | Mapper en Phase 2 |
| 2 | 🚨 Crítico | Coordenadas Costco incorrectas en geolocator | claude/3 | Corregir antes de merge |
| 3 | ⚠️ Medio | `requirements.txt` con `openai` + deps v1 | claude/3 | `git rm requirements.txt` |
| 4 | ⚠️ Medio | `pyproject.toml` falta `feedparser`, `pytz`, `selectolax` | claude/1 | Editar post-merge claude/1 |
| 5 | ⚠️ Medio | `pytest.ini` duplica config de `pyproject.toml` | claude/3 | `git rm pytest.ini` |
| 6 | ℹ️ Menor | stdlib `logging` en lugar de `structlog` | claude/3 | Refactor post-integración |

**Orden de merge: `claude/1` → `claude/2` → `claude/3`**

Ninguno de los conflictos impide el merge en sí — git no reportará conflictos. Los problemas 1 y 2 son semánticos y se manifestarán en tiempo de ejecución si no se corrigen.
