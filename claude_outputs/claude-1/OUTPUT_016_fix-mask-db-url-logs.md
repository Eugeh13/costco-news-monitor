# OUTPUT_016 — fix(security): mask DATABASE_URL password in logs

**Fecha:** 2026-04-25
**Worker:** claude-1
**Rama trabajada:** fix/mask-db-url-in-logs
**Commit(s):** `868fb12` (fix(security): mask DATABASE_URL password in logs)

## Problema

En logs de Railway aparecía en cada arranque del pipeline:

```
pipeline.start db=postgresql+asyncpg://postgres:Tr9mK2pL7xQ4vN8wB5jC3dF6gH1sE0aY@postgres.railway.internal:5432/railway
```

La contraseña de PostgreSQL se exponía en texto plano en cada log line.

**Causa:** `scripts/run_pipeline.py` línea 369 usaba `db_url.split("///")[-1]` como intento de enmascarar — pero este split solo elimina el scheme, no la contraseña.

## Fix aplicado

### Archivo nuevo: `src/core/utils.py`

```python
def mask_db_url(url: str) -> str:
    """Mask the password in a DATABASE_URL for safe logging."""
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", url)
```

### `scripts/run_pipeline.py`

```python
# Antes (línea 369):
log.info("pipeline.start", db=db_url.split("///")[-1])

# Después:
log.info("pipeline.start", db=mask_db_url(db_url))
```

**Resultado del log ahora:**
```
pipeline.start db=postgresql+asyncpg://postgres:***@postgres.railway.internal:5432/railway
```

## Otros lugares donde se loguea DATABASE_URL

Búsqueda exhaustiva con:
```
grep -rn "DATABASE_URL|database_url|db_url|db=" src/ scripts/ | grep -i "log|print"
```

**Solo un sitio encontrado:** `scripts/run_pipeline.py:369` — ya corregido.

## Archivos creados/modificados

| Archivo | Cambio |
|---------|--------|
| `src/core/utils.py` | Nuevo — función `mask_db_url()` |
| `scripts/run_pipeline.py` | Import de `mask_db_url` + aplicación en `pipeline.start` |
| `tests/core/test_utils.py` | Nuevo — 7 tests para `mask_db_url` |

## Tests

221/221 passed (7 nuevos en `tests/core/test_utils.py`)

**Tests nuevos:**
- `test_masks_password_asyncpg` — URL con `+asyncpg`
- `test_masks_password_plain_postgres` — URL postgres estándar
- `test_no_password_unchanged` — URL sin contraseña no se toca
- `test_sqlite_url_unchanged` — SQLite URL pasa sin modificación
- `test_empty_string` — string vacío no rompe
- `test_already_masked` — URL ya enmascarada no se doble-enmascara
- `test_long_password` — contraseña larga queda completamente oculta

## Commit hash verificado

```
git log origin/fix/mask-db-url-in-logs --oneline -1
868fb12 fix(security): mask DATABASE_URL password in logs
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/fix/mask-db-url-in-logs
