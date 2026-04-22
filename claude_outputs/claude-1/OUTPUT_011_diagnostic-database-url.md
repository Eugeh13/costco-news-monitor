# OUTPUT_011 — Diagnóstico: DATABASE_URL .replace() no funciona

**Fecha:** 2026-04-22
**Worker:** claude-1
**Tipo:** Diagnóstico operativo — SIN commits (tarea no modifica repo)
**Rama:** claude/1 (sin cambios)

## Problema reportado

`scripts/fix_alembic_version_col.py` falla al conectar a Railway PostgreSQL con:

```
ClientConfigurationError: scheme is expected to be either "postgresql" or "postgres"
```

A pesar de que el script hace `.replace('postgresql+asyncpg://', 'postgresql://')` antes de pasar la URL a `asyncpg.connect()`.

## Investigación

### 1. El dashboard NO tiene bug

`src/dashboard/database.py` pasa `DATABASE_URL` directamente a SQLAlchemy `create_async_engine`. SQLAlchemy **acepta `postgresql+asyncpg://` nativamente** — no necesita `.replace()` ni ninguna modificación. El dashboard conecta correctamente.

### 2. El script sí necesita el replace — pero falla con caracteres invisibles

`asyncpg.connect()` nativo solo acepta `postgresql://` o `postgres://`. El `.replace()` es necesario.

**Causa raíz identificada:** Railway a veces inyecta caracteres invisibles en variables de entorno copiadas desde su dashboard:

| Carácter | Unicode | Origen común |
|----------|---------|--------------|
| BOM | `\ufeff` | Copy-paste desde editor Windows |
| Zero-width space | `\u200b` | Copy-paste desde browser Railway dashboard |
| Comillas literales | `"` o `'` | Railway CLI export con `"postgresql+asyncpg://..."` |

El `.replace()` **corre sin error** pero deja el carácter invisible como prefijo, por ejemplo:
```
'\ufeffpostgresql://...'   ← asyncpg rechaza porque el scheme es '\ufeffpostgresql'
```

## Fix: sanitización robusta en fix_alembic_version_col.py

**Línea 14 actual:**
```python
url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
```

**Reemplazar por:**
```python
raw = os.environ['DATABASE_URL'].strip().strip('"\'').lstrip('\ufeff\u200b')
url = raw.replace('postgresql+asyncpg://', 'postgresql://', 1)
if not url.startswith(('postgresql://', 'postgres://')):
    url = raw.replace('postgres+asyncpg://', 'postgresql://', 1)
print(f"[diag] scheme usado: {url.split('://')[0]!r}")
```

**Por qué funciona:**
- `.strip()` elimina espacios y newlines
- `.strip('"\'')` elimina comillas literales que Railway CLI puede añadir
- `.lstrip('\ufeff\u200b')` elimina BOM y zero-width space
- El `print` de diagnóstico permite verificar el scheme en logs de Railway

## One-liner para lanzar el dashboard apuntando a Railway (sin editar .env)

El dashboard **no requiere modificar la URL** — SQLAlchemy la acepta tal cual:

```bash
# Opción A — si tienes Railway CLI instalado
DATABASE_URL="$(railway variables get DATABASE_URL)" uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000

# Opción B — si ya tienes .env local con la URL de Railway
python -m uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000
```

No hay que cambiar nada en `.env` ni en el código del dashboard.

## Archivos relevantes

| Archivo | Estado |
|---------|--------|
| `scripts/fix_alembic_version_col.py` | Fix pendiente de aplicar (línea 14) |
| `src/dashboard/database.py` | Sin bug — no requiere cambios |

## Decisión sobre commits

Este era un diagnóstico operativo — **sin cambios al repo**. El fix a `fix_alembic_version_col.py` puede aplicarse en una tarea separada si se confirma que es necesario correr ese script en Railway.
