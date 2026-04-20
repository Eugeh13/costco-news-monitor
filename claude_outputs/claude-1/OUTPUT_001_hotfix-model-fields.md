# OUTPUT_001 — Hotfix: 8 campos faltantes en DecisionLog (Op C)

**Rama:** `hotfix/model-fields`  
**Commit:** `746194b`  
**Fecha:** 2026-04-19  
**Autor:** claude-1 (infraestructura)

---

## Resumen de cambios

Se añadieron 8 campos faltantes al modelo `DecisionLog` que el dashboard y la capa de métricas esperaban pero no existían post-merge. Se creó la migración `0003` para materializarlos en base de datos. Los tests en scope (34) quedaron 100% verdes.

**Archivos modificados:**
| Archivo | Acción |
|---|---|
| `src/models/decision_log.py` | Añadidos 8 campos en 4 bloques lógicos |
| `alembic/versions/0003_add_missing_decision_log_fields.py` | Nueva migración creada |
| `tests/models/test_decision_log.py` | 7 tests nuevos (9 → 16 en el archivo, 34 en suite) |

---

## Campos agregados

| Campo | Tipo SQLAlchemy | Nullable | Default | Bloque lógico |
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

## Verificación de migración

```
$ DATABASE_URL="sqlite+aiosqlite:///./test_0003.db" python3 -m alembic upgrade head

INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial_schema -> 0002_add_decision_log_and_feedback
INFO  [alembic.runtime.migration] Running upgrade 0002_add_decision_log_and_feedback -> 0003_add_missing_decision_log_fields
```

Migración ejecutó sin errores en SQLite. Compatible con PostgreSQL (batch_alter_table es no-op en Postgres y usa ALTER TABLE nativo).

---

## Tests pasando

**Suite en scope:** `tests/models/` + `tests/core/` → **34/34 passing**

**Nuevos tests (7) en `tests/models/test_decision_log.py`:**

| Test | Qué verifica |
|---|---|
| `test_new_fields_default_to_none_or_false` | Los 8 campos tienen defaults correctos sin suministrarlos |
| `test_article_content_snippet_stored` | `article_content_snippet` persiste y se recupera |
| `test_within_radius_and_is_duplicate` | `within_radius=True`, `is_duplicate=False` son almacenados |
| `test_token_and_latency_tracking` | `total_tokens_input/output` y `total_latency_ms` se persisten como Integer |
| `test_telegram_sent_explicit_true` | `telegram_sent` puede setearse a `True` explícitamente |
| `test_error_stage_stored` | `error_stage` almacena el nombre de la etapa donde ocurrió el error |
| `test_all_8_new_fields_together` | Integración: los 8 campos en un solo row |

**Nota sobre `tests/metrics/`:** Los tests de métricas fallan con `InvalidRequestError: Table 'decision_log' is already defined` — error pre-existente al hotfix. Los stubs en `tests/metrics/stubs.py` redefinen `DecisionLog` sobre la misma `Base` que el modelo real. Está fuera de scope de este hotfix.

---

## Decisiones de diseño

1. **`batch_alter_table` en lugar de `op.add_column` directo:** Se usó `op.batch_alter_table` para garantizar compatibilidad con SQLite, que no soporta `ALTER TABLE ... ADD COLUMN` con `NOT NULL` sin default en todas las versiones. Con `server_default=sa.false()` en `telegram_sent`, funciona en ambos motores.

2. **Orden de campos:** Los nuevos campos se insertan en los bloques lógicos más cercanos semánticamente (ej: `within_radius` va junto a los campos de geo, `is_duplicate` tiene su propio bloque, `telegram_sent` en notificación). Esto facilita que el dashboard los encuentre agrupados.

3. **`telegram_sent` NOT NULL con default=False:** Único campo no-nullable de los 8, porque representa un estado binario definitivo (¿se envió o no?) que siempre tiene respuesta. Los demás son opcionales porque dependen de que el pipeline llegue a esa etapa.

4. **`error_stage` separado de `error_message`:** `error_message` ya existía para el texto del error. `error_stage` es un `String(100)` que identifica *en qué etapa* ocurrió el error, permitiendo queries eficientes como `WHERE error_stage = 'geolocation'`.
