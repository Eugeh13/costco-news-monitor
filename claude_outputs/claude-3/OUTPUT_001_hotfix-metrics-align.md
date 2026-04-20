# OUTPUT_001 — Hotfix metrics-align (Op C)

**Fecha:** 2026-04-19  
**Rama:** `hotfix/metrics-align`  
**Objetivo:** Re-verificar `src/metrics/` contra el modelo real actualizado + bonus aggregators  
**Estado:** Completo

---

## Resumen de cambios

### Verificación de nombres de campo

Crucé todas las queries SQL de `aggregators.py` y `quality.py` contra `src/models/decision_log.py` (rama `v2-rewrite`) usando la tabla de divergencias de `INCONSISTENCIA_DASHBOARD.md`. El commit `f76c709` ya había corregido los nombres críticos.

**Resultado: ningún rename adicional necesario.** Los campos en uso coinciden exactamente con el modelo real:

| Campo en aggregators/quality | Nombre real en `decision_log.py` | Estado |
|------------------------------|----------------------------------|--------|
| `stage_reached` | `stage_reached` | ✓ correcto |
| `final_decision` | `final_decision` | ✓ correcto |
| `source_name` | `source_name` | ✓ correcto |
| `incident_type` | `incident_type` | ✓ correcto (no `classified_type`) |
| `severity_score` | `severity_score` | ✓ correcto (no `classified_severity`) |
| `total_tokens_input` | `total_tokens_input` | ✓ correcto (pending hotfix/model-fields) |
| `total_tokens_output` | `total_tokens_output` | ✓ correcto (pending hotfix/model-fields) |
| `total_latency_ms` | `total_latency_ms` | ✓ correcto (pending hotfix/model-fields) |
| `decision_log_id` (FK en human_feedback) | `decision_log_id` | ✓ correcto |
| `should_have_been` | `should_have_been` | ✓ correcto |

**Campos que NO aparecen en mis queries** (renombrados en el modelo real, ya no relevantes):

| Nombre stub/FASE_A.md original | Nombre real | ¿Aparece en mis queries? |
|--------------------------------|-------------|--------------------------|
| `classified_severity` | `severity_score` | No — uso `severity_score` |
| `classified_type` | `incident_type` | No — uso `incident_type` |
| `classified_reasoning` | `ai_reasoning` | No — no referenciado |
| `geo_distance_meters` | `nearest_costco_dist_m` | No — no referenciado |
| `geo_closest_costco` | `nearest_costco` | No — no referenciado |
| `triage_reasoning` | `triage_reason` | No — no referenciado |
| `article_published_at` | `published_at` | No — no referenciado |

---

## Tabla de archivos modificados

| Archivo | Tipo de cambio |
|---------|----------------|
| `tests/metrics/stubs.py` | Añadidos 8 campos de hotfix/model-fields; comentarios de nombres reales |
| `src/metrics/aggregators.py` | +3 bonus aggregators al final |
| `src/metrics/__init__.py` | +3 exports de bonus aggregators |
| `tests/metrics/test_aggregators.py` | _log() helper ampliado; +6 tests de bonus |
| `claude_outputs/claude-3/OUTPUT_001_hotfix-metrics-align.md` | Este archivo |

---

## Renames aplicados en este hotfix

**Ninguno.** El commit `f76c709` ya alineó todos los nombres. Este hotfix confirmó la alineación y agregó los campos faltantes a los stubs.

---

## Bonus: 3 nuevos aggregators

Todos usan `try/except` para degradar a cero cuando las columnas no existen (pre-merge de `hotfix/model-fields`).

### `counts_within_vs_outside_radius(session) → dict[str, int]`

```sql
SELECT within_radius, COUNT(*) AS n
FROM decision_log
WHERE within_radius IS NOT NULL
GROUP BY within_radius
```

Retorna `{"within": N, "outside": N}`. Útil para medir qué fracción de noticias geolocalizadas caen dentro del radio de 3 km de algún Costco.

### `duplicate_rate(session) → float`

```sql
SELECT SUM(CASE WHEN is_duplicate THEN 1 ELSE 0 END) AS dupes,
       COUNT(*) AS total
FROM decision_log
WHERE is_duplicate IS NOT NULL
```

Retorna fracción 0.0–1.0. Permite detectar si una fuente genera muchos duplicados o si el contenido se repite en otras.

### `alerts_actually_sent(session) → int`

```sql
SELECT COUNT(*) AS n FROM decision_log WHERE telegram_sent = 1
```

Cuenta alertas reales (no dry-run). Complementa `counts_by_final_decision` que cuenta decisiones `alerted` aunque `dry_run=True` las haya bloqueado.

---

## Actualización de stubs

`tests/metrics/stubs.py` ahora incluye los 8 campos que claude-1 añade en `hotfix/model-fields`:

```python
article_content_snippet  # Text nullable
within_radius            # Boolean nullable
is_duplicate             # Boolean nullable
total_tokens_input       # Integer nullable
total_tokens_output      # Integer nullable
total_latency_ms         # Integer nullable
telegram_sent            # Boolean, default=False, nullable=False
error_stage              # String(100) nullable
```

Los enums (`StageReached`, `FinalDecision`) usan los valores reales del modelo (no los del stub/FASE_A.md original).

---

## Tests pasando

```
tests/metrics/test_aggregators.py  — 18 passed  (+6 vs f76c709)
tests/metrics/test_quality.py      —  8 passed
tests/metrics/test_report.py       —  3 passed
─────────────────────────────────────────────
Total                               — 29 passed / 0 failed
```

---

## Commit hash final

`d29bac6`
