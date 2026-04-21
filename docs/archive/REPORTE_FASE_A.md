# Reporte de Integración — Fase A

**Fecha:** 2026-04-19  
**Ramas revisadas:** `fase-a/pipeline`, `fase-a/dashboard`, `fase-a/metrics`  
**Estado:** Pre-merge — solo análisis, sin merges aplicados

---

## 1. Resumen por rama

### fase-a/pipeline (claude-1)

| Métrica | Valor |
|---------|-------|
| Commits propios | 7 |
| Archivos tocados | 11 |
| Líneas añadidas | +1 154 |
| Líneas modificadas | −10 (telegram.py) |

**Commits:**
```
fe2b3cd  docs(scripts): agregar README.md con instrucciones de uso del pipeline CLI
4d40024  feat(tests): test_decision_logger.py + test_decision_log.py — 16/16 passing
b2167f0  feat(scripts): agregar run_pipeline.py — CLI completo
1fc1baa  feat(notifier): agregar dry_run=False a send_alert
4d68e30  feat(core): agregar decision_logger.py — create_run() + log_processed_article() UPSERT
ca61ade  feat(alembic): migración 0002 — tablas decision_log y human_feedback
663557e  feat(models): agregar DecisionLog y HumanFeedback con enums StageReached/FinalDecision
c77c87a  feat(infra): mover aiosqlite a main dependencies
```

**Archivos creados/modificados:**
```
pyproject.toml                                      (modificado)
scripts/README.md                                   (nuevo)
scripts/run_pipeline.py                             (nuevo)
src/core/decision_logger.py                         (nuevo)
src/models/decision_log.py                          (nuevo)
src/models/human_feedback.py                        (nuevo)
src/models/__init__.py                              (modificado)
src/notifier/telegram.py                            (modificado — dry_run)
alembic/versions/0002_add_decision_log_and_feedback.py  (nuevo)
tests/core/test_decision_logger.py                  (nuevo)
tests/models/test_decision_log.py                   (nuevo)
```

---

### fase-a/dashboard (claude-2)

| Métrica | Valor |
|---------|-------|
| Commits propios | 4 |
| Archivos tocados | 15 |
| Líneas añadidas | +1 647 |
| Líneas modificadas | −1 (pyproject.toml) |

**Commits:**
```
e0a3524  docs(dashboard): add README — rutas, atajos de teclado, filtros
f223fff  feat(dashboard): add tests/dashboard/ — 24 tests, in-memory SQLite
dfac6ed  feat(dashboard): add main.py, routes.py, templates, static CSS — 5 endpoints
cb7b605  feat(deps): add jinja2, python-multipart, aiosqlite a main deps
```

**Archivos creados/modificados:**
```
pyproject.toml                       (modificado)
src/dashboard/__init__.py            (nuevo)
src/dashboard/_model_stubs.py        (nuevo — temporal, se elimina post-merge)
src/dashboard/database.py            (nuevo)
src/dashboard/main.py                (nuevo)
src/dashboard/routes.py              (nuevo)
src/dashboard/README.md              (nuevo)
src/dashboard/static/style.css       (nuevo)
src/dashboard/templates/base.html    (nuevo)
src/dashboard/templates/detail.html  (nuevo)
src/dashboard/templates/index.html   (nuevo)
src/dashboard/templates/runs.html    (nuevo)
tests/dashboard/__init__.py          (nuevo)
tests/dashboard/conftest.py          (nuevo)
tests/dashboard/test_routes.py       (nuevo)
```

---

### fase-a/metrics (claude-3)

| Métrica | Valor |
|---------|-------|
| Commits propios | 2 |
| Archivos tocados | 12 |
| Líneas añadidas | +1 007 |
| Líneas modificadas | 0 |

**Commits:**
```
8766bde  chore(metrics): limpiar imports no usados + ejemplo de output en README
0169b7e  feat(metrics): agregar capa de métricas y reporte de calidad
```

**Archivos creados:**
```
pyproject.toml                    (modificado)
scripts/generate_report.py        (nuevo)
src/metrics/__init__.py           (nuevo)
src/metrics/README.md             (nuevo)
src/metrics/aggregators.py        (nuevo)
src/metrics/quality.py            (nuevo)
src/metrics/report.py             (nuevo)
tests/metrics/__init__.py         (nuevo)
tests/metrics/stubs.py            (nuevo)
tests/metrics/test_aggregators.py (nuevo)
tests/metrics/test_quality.py     (nuevo)
tests/metrics/test_report.py      (nuevo)
```

---

## 2. Solapamiento entre ramas

### Archivos tocados por más de una rama

| Archivo | pipeline | dashboard | metrics | ¿Conflicto real? |
|---------|:--------:|:---------:|:-------:|------------------|
| `pyproject.toml` | ✓ | ✓ | ✓ | **Sí** — las 3 ramas añaden deps distintas al mismo bloque |
| `scripts/generate_report.py` | — | — | ✓ | No — solo en metrics |
| `scripts/run_pipeline.py` | ✓ | — | — | No — solo en pipeline |

### Mapa de dominios sin solapamiento

```
fase-a/pipeline  →  src/models/decision_log.py, src/models/human_feedback.py,
                    src/core/decision_logger.py, alembic/0002, scripts/run_pipeline.py,
                    src/notifier/telegram.py (dry_run)

fase-a/dashboard →  src/dashboard/ (completo), tests/dashboard/

fase-a/metrics   →  src/metrics/ (completo), tests/metrics/,
                    scripts/generate_report.py
```

### Conflicto concreto en `pyproject.toml`

Cada rama añade deps distintas al mismo bloque `[project] dependencies`:

| Dep | pipeline | dashboard | metrics |
|-----|:--------:|:---------:|:-------:|
| `aiosqlite>=0.20` | ✓ (mueve a main) | ✓ (añade a main) | — |
| `jinja2>=3.1` | — | ✓ | — |
| `python-multipart>=0.0.9` | — | ✓ | — |
| `rich>=13.0` | — | — | ✓ |

El merge secuencial pipeline→dashboard→metrics producirá conflictos en `pyproject.toml`. Resolución manual requerida en los merges 2 y 3 (ver Sección 5).

---

## 3. Review de código por rama

### fase-a/pipeline ✅ Sólido con un issue menor

**Lo bueno:**
- `decision_logger.py` implementa UPSERT por `(run_id, article_url)` — correcto, permite reintentar un pipeline sin duplicar registros
- `_allowed` filter en `log_processed_article()` descarta campos inválidos silenciosamente — evita excepciones por typos en callers
- `run_pipeline.py` maneja `dry_run` correctamente como flag CLI, pasa `dry_run=True` al `TelegramClient`
- Migración 0002 coherente con el modelo SA2

**Problema menor — `telegram.py` fuera de scope:**

El diff modifica `src/notifier/telegram.py`, que es un archivo de Fase 1 compartido:

```diff
+ dry_run: bool = False,
```

El cambio es correcto y necesario (requerido por FASE_A.md), pero al mergear entrará en conflicto si dashboard o metrics también lo tocaron. Verificado: solo pipeline lo modifica — no hay conflicto real, solo ruido en el review.

---

### fase-a/dashboard ⚠️ Funcional pero con stubs que divergen del modelo real

**Lo bueno:**
- `routes.py` usa `try/except ImportError` para importar desde los modelos reales o caer al stub — diseño defensivo inteligente para desarrollo en paralelo
- 24 tests con SQLite en memoria, independientes del pipeline
- UI dark con atajos de teclado (`j/k` para navegar, `y/n` para feedback) — bien pensado para revisión rápida
- `database.py` separado del `core/database.py` principal — el dashboard puede usar su propio DB URL sin afectar el engine global

**Problema crítico — Enums en `_model_stubs.py` NO coinciden con los modelos reales de pipeline:**

Los stubs fueron escritos siguiendo la especificación de `FASE_A.md`, pero pipeline implementó valores distintos:

| Enum | `_model_stubs.py` (dashboard) | `decision_log.py` (pipeline) |
|------|-------------------------------|-------------------------------|
| `StageReached` | `triaged`, `classified`, `geolocated`, `deduped`, `alerted`, `dismissed` | `scraped`, `triage`, `deep_analysis`, `geolocation`, `dedup`, `notification`, `error` |
| `FinalDecision` | `alert_sent`, `dismissed_not_relevant`, `dismissed_too_far`, `dismissed_duplicate`, `dismissed_low_severity`, `error` | `irrelevant`, `duplicate`, `out_of_radius`, `no_geo`, `alerted`, `error`, `pending` |

Cuando el merge de pipeline traiga los modelos reales, el `try/except ImportError` en `routes.py` va a usar los modelos reales — pero el CSS (`_decision_class`) y los filtros HTML asumen los valores del stub:

```python
# routes.py — asume "alert_sent", pipeline produce "alerted"
def _decision_class(decision: str) -> str:
    if decision == "alert_sent":   # ← nunca va a matchear
        return "dec-alert"
```

Los registros de tipo `alerted` aparecerán como `dismissed` en la UI después del merge.

---

### fase-a/metrics 🚨 Dos problemas críticos

**Lo bueno:**
- `generate_report.py` CLI usa `rich` para progress spinner y output coloreado — buena UX
- Estructura modular limpia: `aggregators.py` (queries) → `quality.py` (métricas derivadas) → `report.py` (render Markdown)
- `generate_markdown_report()` exportado limpiamente desde `__init__.py`

**Problema crítico 1 — Nombre de tabla incorrecto en todas las queries SQL:**

El modelo de pipeline define `__tablename__ = "decision_log"` (singular), la migración 0002 crea la tabla `"decision_log"`. Pero todas las queries raw de `aggregators.py` usan `decision_logs` (plural):

```python
# aggregators.py — tabla incorrecta en todas las funciones
text("SELECT final_decision, COUNT(*) FROM decision_logs GROUP BY final_decision")
text("SELECT AVG(latency_ms) FROM decision_logs")
text("SELECT SUM(input_tokens), SUM(output_tokens) FROM decision_logs")
```

Esto produce `OperationalError: no such table: decision_logs` en runtime. Hay que reemplazar `decision_logs` → `decision_log` en todo `aggregators.py`.

**Problema crítico 2 — `counts_by_stage()` consulta la tabla `Incident`, no `decision_log`:**

```python
async def counts_by_stage(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Incident.status, func.count().label("n"))
        .group_by(Incident.status)
    )
```

Esta función importa y consulta `src.models.incident.Incident` (modelo de Fase 1), no el `DecisionLog`. `Incident.status` es el estado de persistencia del incidente (`pending_analysis`, `analyzed`, etc.) — no el stage del pipeline. El reporte de calidad va a mostrar métricas del modelo equivocado.

Debe reemplazarse por una query sobre `decision_log.stage_reached`.

---

## 4. Recomendación de orden de merge

```
fase-a/pipeline  →  fase-a/metrics  →  fase-a/dashboard
```

**Justificación:**

| Paso | Rama | Razón |
|------|------|-------|
| 1 | `fase-a/pipeline` | Define los modelos reales (`DecisionLog`, `HumanFeedback`) y la migración 0002. Todo lo demás depende de estos. |
| 2 | `fase-a/metrics` | Solo lee de `decision_log`. No tiene stubs, no depende del dashboard. Más simple de resolver. |
| 3 | `fase-a/dashboard` | Tiene el `_model_stubs.py` que hay que eliminar post-merge y los enums que hay que ajustar. Va al último para tener los modelos reales ya disponibles. |

> **Nota:** FASE_A.md indica `pipeline → metrics → dashboard` — este orden coincide.

---

## 5. Conflictos esperados y cómo resolverlos

### Conflicto 1 — `pyproject.toml` (3 ramas modifican el mismo bloque) — MERGE 2 y 3

**Cuándo:** Al mergear fase-a/dashboard y fase-a/metrics sobre fase-a/pipeline.

**Resolución:** Al resolver el conflicto, el bloque `[project] dependencies` final debe quedar:

```toml
dependencies = [
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "asyncpg>=0.29",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "anthropic>=0.25",
    "structlog>=24.1",
    "httpx>=0.27",
    "tenacity>=8.2",
    "feedparser>=6.0",
    "pytz>=2024.1",
    "selectolax>=0.3",
    "aiosqlite>=0.20",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "rich>=13.0",
]
```

Y eliminar `aiosqlite` del bloque `dev` (ya está en main).

---

### Conflicto 2 — Tabla `decision_logs` vs `decision_log` en metrics (CRÍTICO — pre-merge)

**Archivo:** `src/metrics/aggregators.py`

**Resolución:** Reemplazar `decision_logs` → `decision_log` en todas las queries. Claude-3 debe corregirlo en `fase-a/metrics` antes del merge:

```python
# Reemplazar en TODAS las ocurrencias de aggregators.py
"FROM decision_logs"  →  "FROM decision_log"
"FROM decision_logs " →  "FROM decision_log "
```

También verificar `total_tokens_input`, `total_tokens_output` y `latency_ms` — confirmar que los nombres de columna coinciden con el modelo de pipeline:
- pipeline usa: `total_tokens_input`, `total_tokens_output`, `total_latency_ms` (si existen)
- metrics asume: `input_tokens`, `output_tokens`, `latency_ms`

---

### Conflicto 3 — `counts_by_stage()` consulta modelo incorrecto (CRÍTICO — pre-merge)

**Archivo:** `src/metrics/aggregators.py`

**Resolución:** Reemplazar la función para que consulte `decision_log.stage_reached`:

```python
async def counts_by_stage(session: AsyncSession) -> dict[str, int]:
    try:
        result = await session.execute(
            text(
                "SELECT stage_reached, COUNT(*) AS n "
                "FROM decision_log "
                "GROUP BY stage_reached"
            )
        )
        return {str(row.stage_reached): row.n for row in result}
    except Exception:
        return {}
```

---

### Conflicto 4 — Enums `StageReached` / `FinalDecision` en dashboard stubs (CRÍTICO — post-merge pipeline)

**Cuándo:** Inmediatamente después de mergear fase-a/pipeline, antes de mergear fase-a/dashboard.

**Archivos afectados:**
- `src/dashboard/_model_stubs.py` — eliminar completo (ya no se necesita)
- `src/dashboard/routes.py` — actualizar `_decision_class()` y filtros HTML

**Resolución:**

```python
# routes.py — actualizar _decision_class con valores reales de pipeline
def _decision_class(decision: str) -> str:
    if decision == "alerted":       # era "alert_sent"
        return "dec-alert"
    if decision == "error":
        return "dec-error"
    return "dec-dismissed"
```

Los filtros en los templates HTML que usen `alert_sent`, `dismissed_*` también necesitan actualizarse a los valores reales: `irrelevant`, `duplicate`, `out_of_radius`, `no_geo`, `alerted`, `error`, `pending`.

---

## 6. Resumen ejecutivo

| # | Severidad | Problema | Rama | Acción |
|---|-----------|----------|------|--------|
| 1 | 🚨 Crítico | Tabla `decision_logs` (plural) en todas las queries de metrics | fase-a/metrics | Corregir en rama antes del merge |
| 2 | 🚨 Crítico | `counts_by_stage()` consulta `Incident`, no `decision_log` | fase-a/metrics | Corregir en rama antes del merge |
| 3 | 🚨 Crítico | Enums `StageReached`/`FinalDecision` del stub no coinciden con modelos reales | fase-a/dashboard | Corregir post-merge de pipeline |
| 4 | ⚠️ Medio | `pyproject.toml` conflicto en merge 2 y 3 | las 3 | Resolver manualmente con tabla consolidada |
| 5 | ℹ️ Info | `telegram.py` modificado en pipeline (fuera de scope original) | fase-a/pipeline | Sin acción — cambio correcto y necesario |

**Orden de merge: `fase-a/pipeline` → `fase-a/metrics` → `fase-a/dashboard`**

Los conflictos 1 y 2 deben resolverse en `fase-a/metrics` **antes de mergear**. El conflicto 3 se resuelve post-merge de pipeline, antes de mergear dashboard.
