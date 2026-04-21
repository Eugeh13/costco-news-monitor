# Inconsistencia detectada — Dashboard stub vs modelo real

**Fecha:** 2026-04-19  
**Contexto:** Post-merge de `fase-a/dashboard` sobre `v2-rewrite`.  
**Estado actual:** Merges aplicados, stubs aún presentes, 20/24 tests de dashboard fallando. Los otros 95 tests del suite están verdes.

---

## Causa raíz

`routes.py` ahora resuelve el `try/except ImportError` exitosamente con los **modelos reales** (ya disponibles tras el merge de `fase-a/pipeline`). Sin embargo, `tests/dashboard/conftest.py` crea la base de datos en memoria usando `_Base.metadata` del stub — un schema diferente.

Error en runtime de tests:
```
sqlite3.OperationalError: no such column: decision_log.published_at
```

El stub llama ese campo `article_published_at`. Las rutas consultan `published_at` (nombre del modelo real).

---

## Mapa completo de divergencias

### Campos renombrados

| Stub `_model_stubs.py` | Modelo real `decision_log.py` |
|------------------------|-------------------------------|
| `article_published_at` | `published_at` |
| `triage_reasoning` | `triage_reason` |
| `classified_type` | `incident_type` |
| `classified_severity` | `severity_score` |
| `classified_reasoning` | `ai_reasoning` |
| `geo_closest_costco` | `nearest_costco` |
| `geo_distance_meters` | `nearest_costco_dist_m` |

### Campos que existen en el stub pero NO en el modelo real

| Campo stub | Descripción |
|------------|-------------|
| `article_content_snippet` | Snippet del artículo |
| `within_radius` | ¿Dentro del radio de 3km? |
| `is_duplicate` | ¿Marcado como duplicado? |
| `total_tokens_input` | Tokens input LLM |
| `total_tokens_output` | Tokens output LLM |
| `total_latency_ms` | Latencia total en ms |
| `telegram_sent` | ¿Se mandó alerta por Telegram? |
| `error_stage` | Etapa donde ocurrió el error |

> Nota: estos campos sí están en la especificación de `FASE_A.md`. El modelo real los omitió.

### Enums divergentes

#### `StageReached`

| Stub | Modelo real |
|------|-------------|
| `triaged` | `scraped` |
| `classified` | `triage` |
| `geolocated` | `deep_analysis` |
| `deduped` | `geolocation` |
| `alerted` | `dedup` |
| `dismissed` | `notification` |
| — | `error` |

#### `FinalDecision`

| Stub | Modelo real |
|------|-------------|
| `alert_sent` | `alerted` |
| `dismissed_not_relevant` | `irrelevant` |
| `dismissed_too_far` | `out_of_radius` |
| `dismissed_duplicate` | `duplicate` |
| `dismissed_low_severity` | (no existe) |
| — | `no_geo` |
| — | `pending` |

---

## Archivos afectados

| Archivo | Problema |
|---------|----------|
| `src/dashboard/_model_stubs.py` | Debe eliminarse, pero primero resolver divergencias |
| `src/dashboard/main.py` | Tiene `try/except` para stub — ya resuelve con modelo real, limpiar |
| `src/dashboard/routes.py` | Tiene `try/except` para stub — ya resuelve con modelo real, limpiar. Además `_decision_class()` asume `"alert_sent"` (stub) en vez de `"alerted"` (real) |
| `tests/dashboard/conftest.py` | Importa `_Base`, `DecisionLog`, `HumanFeedback` del stub. Seed data usa nombres de campos del stub |
| `tests/dashboard/test_routes.py` | Importa `DecisionLog`, `HumanFeedback` del stub |

---

## Opciones de resolución

### Opción A — Actualizar el modelo real (recomendada)

Claude-1 añade los campos faltantes a `src/models/decision_log.py` y genera migración `0003_add_missing_decision_log_fields.py`.

**Campos a añadir al modelo real:**

```python
article_content_snippet: Mapped[str | None] = mapped_column(Text)
within_radius: Mapped[bool | None] = mapped_column(Boolean)
is_duplicate: Mapped[bool | None] = mapped_column(Boolean)
total_tokens_input: Mapped[int | None] = mapped_column(Integer)
total_tokens_output: Mapped[int | None] = mapped_column(Integer)
total_latency_ms: Mapped[int | None] = mapped_column(Integer)
telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
error_stage: Mapped[str | None] = mapped_column(String(100))
```

**Campos a renombrar** (requiere `ALTER TABLE` en migración o columna nueva + deprecar vieja):

| Actual | Debe ser |
|--------|----------|
| `published_at` | `article_published_at` |
| `triage_reason` | `triage_reasoning` |
| `incident_type` | `classified_type` |
| `severity_score` | `classified_severity` |
| `ai_reasoning` | `classified_reasoning` |
| `nearest_costco` | `geo_closest_costco` |
| `nearest_costco_dist_m` | `geo_distance_meters` |

**Ventaja:** El modelo real queda alineado con FASE_A.md. Los tests de dashboard funcionan sin cambios.  
**Desventaja:** Requiere nueva migración y cambios en `run_pipeline.py` que ya usa los nombres actuales.

---

### Opción B — Adaptar dashboard al modelo real (más rápido)

Actualizar `conftest.py`, seed data y templates para usar los nombres del modelo real tal como está.

**Cambios necesarios en dashboard:**

1. `conftest.py` — cambiar import de `_Base` a `from src.core.database import Base`, actualizar seed data renombrando campos y valores de enum
2. `test_routes.py` — cambiar import a `from src.models.decision_log import DecisionLog, ...`
3. `routes.py` — eliminar `try/except`, usar imports directos, corregir `_decision_class()` (`"alert_sent"` → `"alerted"`)
4. `main.py` — eliminar `try/except`, usar import directo
5. Templates HTML — revisar si referencian `classified_severity`, `geo_closest_costco`, etc. y actualizar
6. Eliminar `src/dashboard/_model_stubs.py`

**Ventaja:** No toca modelos ni migraciones.  
**Desventaja:** El modelo real no tiene campos útiles como `telegram_sent`, `total_latency_ms`, `within_radius` — el dashboard mostrará menos información de la planeada en FASE_A.md.

---

## Estado del test suite completo

```
tests/core/          — 6 passed
tests/models/        — 16 passed  (5 originales + 11 nuevos de decision_log)
tests/scrapers/      — 33 passed
tests/analyzer/      — 43 passed
tests/notifier/      — 8 passed
tests/metrics/       — 23 passed
tests/dashboard/     — 4 passed / 20 FAILED  ← problema aquí
─────────────────────────────────────────────
Total                — 133 passed / 20 failed
```

---

## Recomendación

**Opción A** es la correcta a largo plazo — el stub sigue la especificación de `FASE_A.md` más fielmente. Claude-1 debería haber incluido esos campos desde el inicio.

**Opción B** es viable si quieres desbloquear el merge hoy y posponer la discusión de schema para Fase B.

En ambos casos, una vez resuelta la opción elegida, el paso final es:

```bash
git rm src/dashboard/_model_stubs.py
# + commit de limpieza
git push origin v2-rewrite
```
