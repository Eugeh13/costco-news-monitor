# OUTPUT_003 — Cierre Día 1: Semana 1 completa + Semana 2 70%

**Fecha:** 20 abril 2026  
**Integrador:** claude-integrator  
**Branch:** v2-rewrite  
**Tests al cierre:** 214/214 passing

---

## Merges completados hoy (en orden)

| # | Rama | Commit | Tests post-merge | Notas |
|---|------|--------|-----------------|-------|
| 1 | `week1/caching-dedup` | d9f491a | 188/188 | T1.3 + T1.7 |
| 2 | `week1/geolocator-tooluse` | 379c94f | 188/188 | T1.2 + T1.4 + T1.8 + T1.9 + T1.10 |
| 3 | `week1/scrapers-filters` | 27505f7 | 194/194 | T1.5 + T1.6 |
| 4 | `week2/api-and-tokens` | — | 205/205 | T2.3 + token infra + migración 0005 |
| 5 | `week2/decision-logger-tokens-fix` | 2185323 | 210/210 | token capture fix |
| 6 | `week2/dashboard-base` | 6ef18e0 | 214/214 | T2.1–T2.9 dashboard MVP |

`week1/scrapers-filters` estuvo ausente de origin inicialmente — merged en segunda sesión tras confirmación de claude-2.

---

## Migraciones Alembic aplicadas

| Migración | Descripción |
|-----------|-------------|
| `0004_add_geolocation_fields` | 4 campos geo en `analysis_results` |
| `74b26b81` | 4 campos geo en `decision_log` (fix schema mismatch) |
| `0005_add_token_cache_and_cost_fields` | `total_tokens_cache_read`, `total_tokens_cache_creation`, `cost_estimated_usd` en `decision_log` |

---

## Corridas de validación

### Corrida A — pre-filtros (run ff0be828)
- 200 artículos · 4 alertas · 673s · geo 82% (9/11)

### Corrida B — todos los filtros (run 610e6552)
- 16 artículos (-92%) · 0 alertas (incidentes previos en dedup) · 133s
- `approximate_location` poblado: 4/4 · confidence ≥ 0.5: 3/4

### Corrida C — post token-fix (run 0c052a0c)
- 10 artículos · 10 duplicados (sin LLM calls) · 39s
- Token fix verificado en run de test de claude-1: $0.0187 capturado

---

## Bugs encontrados y resueltos

### Bug 1: DB dedup false-positive (200/200)
- **Causa:** pipeline logueaba artículo a `decision_log` (scraped) antes de llamar `is_duplicate_db()`, que encontraba el registro recién insertado
- **Fix:** parámetro `exclude_run_id` en `dedup.py` + pasado desde `run_pipeline.py`
- **Archivo:** `src/analyzer/dedup.py`, `scripts/run_pipeline.py`

### Bug 2: Geolocator markdown fences
- **Causa:** LLM devolvía JSON envuelto en ` ```json ``` `, rompiendo `json.loads()`
- **Fix:** reescritura completa con Anthropic `tool_use` API (T1.2)
- **Archivo:** `src/analyzer/geolocator.py`

### Bug 3: Schema mismatch decision_log vs analysis_results
- **Causa:** claude-1 agregó 4 campos geo a `analysis_results` pero el pipeline escribe a `decision_log`
- **Fix:** migración `74b26b81` — mismos 4 campos en `decision_log` + pipeline llama `geolocate_incident()` directamente

---

## Estado de tareas del plan

| Semana | Tareas | Estado |
|--------|--------|--------|
| Semana 1 (T1.1–T1.11) | 11/11 | ✅ COMPLETA |
| Semana 2 (T2.1–T2.10) | 10/10 | ✅ COMPLETA |

Entregado en ~4-5 hrs reales vs 10-11 hrs estimadas para Semana 1 sola.

---

## Decisiones arquitectónicas tomadas

1. **Pipeline llama `geolocate_incident()` directamente** (no `extract_locations()`) — captura `GeolocationResult` completo para poblar campos enriquecidos
2. **`analysis_results` no se usa** — pipeline vive completamente en `decision_log`; consolidación va a BACKLOG Semana 3
3. **`week1/scrapers-filters` ausente de origin** inicialmente — merged sin conflictos, confirmado por claude-2

---

## Issues conocidos al cierre

| Issue | Severidad | Destino |
|-------|-----------|---------|
| `/api/incidents` devuelve 0 con `within_radius_only=true` porque registros históricos tienen `within_radius=NULL` | Media | Se resuelve con fix de geolocator (Semana 3) |
| Nominatim resuelve a centroides genéricos (Escobedo @ 8km en lugar de ~3km) | Alta | BACKLOG — SEMANA 3 URGENTE |
| Milenio/Info7/Horizonte: 403/404 persistentes, 0 artículos | Baja | BACKLOG — decidir Semana 3 |
| Costo exacto sin medir (tokens instrumentados pero corridas previas sin datos) | Baja | Se popula desde próxima corrida con LLM |

---

## Siguiente: Semana 2 restante (pendiente)

De PLAN_30_DIAS.md Semana 2, todo T2.x está marcado como completado.  
Semana 3 arranca con fix de geolocator como prioridad 1.

Referencia: `docs/GEOLOCATOR_FIX_RESEARCH.md` (claude-3, commit directo a v2-rewrite).
