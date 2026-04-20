# OUTPUT_001 — Preparación Opción C: ramas hotfix + FASE_A.md actualizado

**Fecha:** 2026-04-19  
**Tarea:** Preparar ramas hotfix para resolver inconsistencia stub vs modelo real  
**Estado:** Completo — listo para que los 3 workers arranquen

---

## Qué se hizo

### 1. Ramas hotfix creadas y pusheadas a origin

| Worktree | Rama | Base | Para quién |
|----------|------|------|------------|
| `claude-1` | `hotfix/model-fields` | `v2-rewrite` | claude-1 |
| `claude-2` | `hotfix/dashboard-align` | `v2-rewrite` | claude-2 |
| `claude-3` | `hotfix/metrics-align` | `v2-rewrite` | claude-3 |

### 2. FASE_A.md actualizado (commit `2dbdcbd`)

7 campos renombrados en la tabla `decision_log` para reflejar los nombres reales del modelo:

| Antes (stub/spec original) | Ahora (modelo real) |
|----------------------------|---------------------|
| `article_published_at` | `published_at` |
| `triage_reasoning` | `triage_reason` |
| `classified_type` | `incident_type` |
| `classified_severity` | `severity_score` |
| `classified_reasoning` | `ai_reasoning` |
| `geo_closest_costco` | `nearest_costco` |
| `geo_distance_meters` | `nearest_costco_dist_m` |

Enums actualizados:
- `stage_reached`: ahora refleja valores reales (`scraped`, `triage`, `deep_analysis`, `geolocation`, `dedup`, `notification`, `error`)
- `final_decision`: ahora refleja valores reales (`alerted`, `irrelevant`, `out_of_radius`, `duplicate`, `no_geo`, `error`, `pending`)

Nota de actualización añadida al inicio del documento.

### 3. Sistema de outputs creado

`claude_outputs/` con subcarpetas por agente + README con convención de nombres.

---

## Instrucciones para cada worker

### claude-1 — `hotfix/model-fields`

**Objetivo:** Añadir 8 campos faltantes al modelo `DecisionLog` + migración `0003`.

**Campos a añadir en `src/models/decision_log.py`:**

```python
article_content_snippet: Mapped[str | None] = mapped_column(Text)
within_radius:           Mapped[bool | None] = mapped_column(Boolean)
is_duplicate:            Mapped[bool | None] = mapped_column(Boolean)
total_tokens_input:      Mapped[int | None]  = mapped_column(Integer)
total_tokens_output:     Mapped[int | None]  = mapped_column(Integer)
total_latency_ms:        Mapped[int | None]  = mapped_column(Integer)
telegram_sent:           Mapped[bool]        = mapped_column(Boolean, default=False, nullable=False)
error_stage:             Mapped[str | None]  = mapped_column(String(100))
```

**Migración:** `alembic/versions/0003_add_missing_decision_log_fields.py`  
(8 `op.add_column("decision_log", ...)` + `downgrade()` con `op.drop_column`)

**Tests:** Actualizar `tests/models/test_decision_log.py` para cubrir los nuevos campos.

**Output esperado:** Guardar resultado en `claude_outputs/claude-1/OUTPUT_001_hotfix-model-fields.md`

---

### claude-2 — `hotfix/dashboard-align`

**Objetivo:** Alinear dashboard con el modelo real. Eliminar `_model_stubs.py`.

**Tareas:**

1. **`tests/dashboard/conftest.py`**
   - Cambiar `from src.dashboard._model_stubs import _Base, DecisionLog, HumanFeedback`
   - Por `from src.core.database import Base` y `from src.models.decision_log import DecisionLog, ...`
   - Actualizar seed data: renombrar campos y valores de enum según tabla de arriba
   - `_Base.metadata.create_all` → `Base.metadata.create_all`

2. **`tests/dashboard/test_routes.py`**
   - Cambiar import de stubs por import de modelos reales

3. **`src/dashboard/routes.py`**
   - Eliminar `try/except ImportError` — usar imports directos desde `src.models.*`
   - Corregir `_decision_class()`: `"alert_sent"` → `"alerted"`
   - Revisar templates: cualquier referencia a campos del stub debe actualizarse

4. **`src/dashboard/main.py`**
   - Eliminar `try/except ImportError` — usar import directo desde `src.models.decision_log`

5. **`src/dashboard/_model_stubs.py`** → `git rm`

**Tests esperados:** 24/24 passing  
**Output esperado:** `claude_outputs/claude-2/OUTPUT_001_hotfix-dashboard-align.md`

---

### claude-3 — `hotfix/metrics-align`

**Objetivo:** Verificar que `src/metrics/aggregators.py` usa nombres de columna correctos tras los cambios de Op C (claude-3 ya corrigió `decision_logs` → `decision_log` en `f76c709`, pero hay que re-verificar contra el modelo actualizado).

**Tareas:**

1. Revisar todas las queries SQL en `aggregators.py` — confirmar que los nombres de columna coinciden con el modelo real actualizado (`severity_score`, `incident_type`, `triage_reason`, etc.)
2. Actualizar cualquier referencia a `classified_severity`, `geo_distance_meters`, etc. si las hay
3. Correr `tests/metrics/` — deben seguir 23/23

**Output esperado:** `claude_outputs/claude-3/OUTPUT_001_hotfix-metrics-align.md`

---

## Contexto de por qué existe este hotfix

Ver `INCONSISTENCIA_DASHBOARD.md` en la raíz para el análisis completo.

**Resumen:** El stub de dashboard (`_model_stubs.py`) siguió la spec de `FASE_A.md` fielmente, pero el modelo real implementado por claude-1 usó nombres distintos y omitió 8 campos. Op C = claude-1 añade los campos faltantes + claude-2 alinea el dashboard + claude-3 verifica metrics.

---

## Estado del test suite antes del hotfix

```
tests/core/      — 6  passed
tests/models/    — 16 passed
tests/scrapers/  — 33 passed
tests/analyzer/  — 43 passed
tests/notifier/  — 8  passed
tests/metrics/   — 23 passed
tests/dashboard/ — 4  passed / 20 FAILED
─────────────────────────────────────────
Total            — 133 passed / 20 failed
```

**Objetivo post-hotfix:** 153+ passed / 0 failed
