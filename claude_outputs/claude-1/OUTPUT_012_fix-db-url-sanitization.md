# OUTPUT_012 — Fix: sanitización de DATABASE_URL en fix_alembic_version_col.py

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** fix/db-url-sanitization
**Commit(s):** `9a330b5` (fix(deploy): sanitize DATABASE_URL in fix_alembic_version_col.py (BOM, zero-width, quotes))

## Problema

`scripts/fix_alembic_version_col.py` fallaba al conectar a Railway PostgreSQL con:

```
ClientConfigurationError: scheme is expected to be either "postgresql" or "postgres"
```

El `.replace('postgresql+asyncpg://', 'postgresql://')` corría sin error pero dejaba caracteres invisibles como prefijo del scheme. Railway puede inyectar estos caracteres cuando se copia la URL desde su dashboard:

| Carácter | Unicode | Síntoma |
|----------|---------|---------|
| BOM | `\ufeff` | `.startswith()` falla, scheme inválido |
| Zero-width space | `\u200b` | Invisible en logs, asyncpg rechaza |
| Comillas literales | `"` / `'` | Railway CLI export |
| Espacios / newline | `\s` | Variables de entorno mal formateadas |

## Fix aplicado

**`scripts/fix_alembic_version_col.py` — línea 14:**

```python
# Antes
url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')

# Después
raw = os.environ['DATABASE_URL'].strip().strip('"\'').lstrip('\ufeff\u200b')
url = raw.replace('postgresql+asyncpg://', 'postgresql://', 1)
if not url.startswith(('postgresql://', 'postgres://')):
    url = raw.replace('postgres+asyncpg://', 'postgresql://', 1)
print(f"[diag] scheme usado: {url.split('://')[0]!r}")
```

**Por qué funciona:**
- `.strip()` elimina espacios y newlines al inicio/fin
- `.strip('"\'')` elimina comillas literales que Railway CLI añade
- `.lstrip('\ufeff\u200b')` elimina BOM y zero-width space
- El fallback cubre el caso `postgres+asyncpg://` (alias sin "ql")
- `print` de diagnóstico visible en logs de Railway para verificación

## Nota: el dashboard no requería fix

`src/dashboard/database.py` pasa `DATABASE_URL` directamente a SQLAlchemy `create_async_engine`, que acepta `postgresql+asyncpg://` nativamente. Sin bug ahí.

## Tests

214/214 passed

## Commit hash verificado

```
git log origin/fix/db-url-sanitization --oneline -1
9a330b5 fix(deploy): sanitize DATABASE_URL in fix_alembic_version_col.py (BOM, zero-width, quotes)
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/fix/db-url-sanitization
