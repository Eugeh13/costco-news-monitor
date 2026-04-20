# OUTPUT_001 — Hotfix: 8 campos faltantes en DecisionLog

**Agente:** claude-1 (infraestructura: core, models, alembic)  
**Rama:** `hotfix/model-fields`  
**Commit final:** `4b4090f`  
**Fecha:** 2026-04-19

---

## Tarea

Añadir 8 campos faltantes al modelo `DecisionLog` + migración `0003`, detectados como inconsistencia entre el modelo real (pipeline) y lo que el dashboard/metrics esperaban post-merge (Op C del integrador).

---

## Archivos modificados

| Archivo | Acción |
|---|---|
| `src/models/decision_log.py` | +8 campos en bloques lógicos |
| `alembic/versions/0003_add_missing_decision_log_fields.py` | Nueva migración creada |
| `tests/models/test_decision_log.py` | +7 tests nuevos (9 → 16 en el archivo) |

**Fuera de scope** (única excepción autorizada): `src/notifier/telegram.py` — parámetro `dry_run=False` en `send_alert`, requerido por `run_pipeline.py`. No se tocó nada de dashboard, metrics, scrapers, ni analyzer.

---

## Campos añadidos

| Campo | Tipo | Nullable | Default | Bloque |
|---|---|---|---|---|
| `article_content_snippet` | `Text` | Sí | `None` | Article metadata |
| `within_radius` | `Boolean` | Sí | `None` | Geolocation |
| `is_duplicate` | `Boolean` | Sí | `None` | Dedup |
| `total_tokens_input` | `Integer` | Sí | `None` | Performance / cost |
| `total_tokens_output` | `Integer` | Sí | `None` | Performance / cost |
| `total_latency_ms` | `Integer` | Sí | `None` | Performance / cost |
| `telegram_sent` | `Boolean` | **No** | `False` | Notification |
| `error_stage` | `String(100)` | Sí | `None` | Error |

---

## Migración 0003

```
$ DATABASE_URL="sqlite+aiosqlite:///./test_0003.db" python3 -m alembic upgrade head

INFO  Running upgrade  -> 0001_initial_schema
INFO  Running upgrade 0001_initial_schema -> 0002_add_decision_log_and_feedback
INFO  Running upgrade 0002_add_decision_log_and_feedback -> 0003_add_missing_decision_log_fields
```

Sin errores. Usa `batch_alter_table` para compatibilidad SQLite + PostgreSQL. `telegram_sent` usa `server_default=sa.false()` para satisfacer el `NOT NULL` en ambos motores.

---

## Tests

**Suite en scope (`tests/models/` + `tests/core/`):** 34/34 passing.

Nuevos tests en `test_decision_log.py`:

| Test | Qué verifica |
|---|---|
| `test_new_fields_default_to_none_or_false` | Defaults correctos sin suministrar los 8 campos |
| `test_article_content_snippet_stored` | Persistencia del snippet de contenido |
| `test_within_radius_and_is_duplicate` | Booleans de geo y dedup almacenados correctamente |
| `test_token_and_latency_tracking` | Campos Integer de tokens y latencia |
| `test_telegram_sent_explicit_true` | `telegram_sent` puede setearse a `True` |
| `test_error_stage_stored` | `error_stage` registra la etapa exacta del fallo |
| `test_all_8_new_fields_together` | Integración: los 8 campos en un solo row |

**Nota:** `tests/metrics/` falla con `InvalidRequestError: Table 'decision_log' already defined` — error pre-existente al hotfix. Los stubs de métricas redefinen `DecisionLog` sobre la misma `Base` que el modelo real. Está fuera de mi scope.

---

## Decisiones de diseño

- **`batch_alter_table`**: necesario para SQLite que no soporta `ALTER TABLE ADD COLUMN NOT NULL` sin default en todas las versiones. No-op en PostgreSQL.
- **`telegram_sent` NOT NULL**: único campo no-nullable de los 8 — representa un estado binario definitivo. Los demás son opcionales porque dependen de que el pipeline llegue a esa etapa.
- **`error_stage` separado de `error_message`**: permite `WHERE error_stage = 'geolocation'` para análisis de fallos por etapa sin hacer LIKE sobre el texto del mensaje.
- **Orden de campos**: insertados en los bloques semánticamente más cercanos para que dashboard y metrics los encuentren agrupados lógicamente.
