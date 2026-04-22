# OUTPUT_006 — Fix: compatibilidad de migraciones con PostgreSQL

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** fix/migrations-postgres-compat
**Commit(s):** `5fa259b` (fix(migrations): replace datetime('now') with CURRENT_TIMESTAMP for PostgreSQL compat)

> **Nota de protocolo GOVERNANCE.md Paso 3:** El OUTPUT se escribe después del push (Paso 9)
> para incluir el hash real verificado contra origin, evitando el anti-patrón de reportar
> "pendiente".

## Problema

Al correr migraciones contra PostgreSQL de Railway, la migración `0002` fallaba con:

```
asyncpg.exceptions.UndefinedFunctionError: function datetime(unknown) does not exist
HINT: No function matches the given name and argument types.
```

`datetime('now')` es sintaxis exclusiva de SQLite. PostgreSQL no tiene esa función.

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `alembic/versions/0002_add_decision_log_and_feedback.py` | 4 ocurrencias de `datetime('now')` → `CURRENT_TIMESTAMP` |

## Reemplazo aplicado

```
datetime('now')  →  CURRENT_TIMESTAMP
```

`CURRENT_TIMESTAMP` es ANSI SQL estándar — funciona en SQLite 3.x, PostgreSQL 14+, y cualquier RDBMS moderno.

Las 4 líneas afectadas eran `server_default` de columnas de timestamp en las tablas `decision_log` y `human_feedback`:

```python
# Antes
server_default=sa.text("(datetime('now'))"),

# Después
server_default=sa.text("(CURRENT_TIMESTAMP)"),
```

## Otros patrones SQLite-específicos buscados

| Patrón | Resultado |
|--------|-----------|
| `AUTOINCREMENT` | No encontrado |
| `DEFAULT '0'` / `DEFAULT '1'` | No encontrado |
| `sa.false()` / `sa.true()` | Presentes en 0003 — son SQLAlchemy cross-DB, no SQLite-específicos ✓ |

Solo `datetime('now')` requería fix.

## Validación

- `alembic upgrade head` contra SQLite fresco: **todas las migraciones corrieron sin error**
- pytest (sin tests/metrics): **185/185 passed**

## Commit hash verificado

```
git log origin/fix/migrations-postgres-compat --oneline -1
5fa259b fix(migrations): replace datetime('now') with CURRENT_TIMESTAMP for PostgreSQL compat
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/fix/migrations-postgres-compat
