# OUTPUT_013 — Fix: dashboard carga .env automáticamente y sanitiza DATABASE_URL

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** fix/dashboard-loads-env
**Commit(s):** pendiente

## Problema

El dashboard (`src/dashboard/main.py`) fallaba con:

```
Could not parse SQLAlchemy URL from string 'None'
```

o equivalente cuando se lanzaba con `uvicorn` sin hacer `export DATABASE_URL=...` manualmente. `src/dashboard/database.py` leía `DATABASE_URL` de `os.environ` pero no llamaba `load_dotenv()` — por lo que el `.env` del proyecto nunca se cargaba al arrancar el servidor.

El mismo problema existía en `alembic/env.py`, resuelto provisionalmente con `export $(grep...)` pero no sostenible para uso diario.

## Fix aplicado

### `src/dashboard/database.py`

- Agregado `from dotenv import load_dotenv` y `load_dotenv()` al inicio del módulo
- Aplicada sanitización de URL (strip BOM, zero-width space, comillas, espacios) antes de pasarla a `create_async_engine` — consistente con el fix de `fix_alembic_version_col.py`

```python
# Antes
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./costco_motor.db")

# Después
load_dotenv()
_raw_url = os.getenv("DATABASE_URL", "")
if _raw_url:
    _raw_url = _raw_url.strip().strip('"\'').lstrip('\ufeff\u200b')
_DATABASE_URL = _raw_url or "sqlite+aiosqlite:///./costco_motor.db"
```

### `alembic/env.py`

- Agregado `from dotenv import load_dotenv` y `load_dotenv()` antes de importar modelos
- Agregada sanitización de URL (strip BOM, zero-width space, comillas, espacios) en la lectura de `DATABASE_URL`
- Elimina definitivamente el workaround de `export $(grep -v '^#' .env | xargs)`

### `pyproject.toml` + `requirements.txt`

- Agregado `python-dotenv>=1.0` como dependencia de producción
- `fix_alembic_version_col.py` ya la usaba (importada sin estar en deps) — ahora es oficial

## Resultado de validación del dashboard

```
HTTP 200 - dashboard OK
```

Dashboard arrancó con `.env` apuntando a SQLite local sin ningún `export` previo.

## Uso después del fix

```bash
# Apuntar a Railway (en .env):
# DATABASE_URL=postgresql+asyncpg://...

python3 -m uvicorn src.dashboard.main:app --host 0.0.0.0 --port 8000
# El .env se carga automáticamente — sin export dances
```

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/dashboard/database.py` | `load_dotenv()` + sanitización de URL |
| `alembic/env.py` | `load_dotenv()` + sanitización de URL |
| `pyproject.toml` | `python-dotenv>=1.0` en `[project.dependencies]` |
| `requirements.txt` | `python-dotenv>=1.0` |

## Tests

214/214 passed

## Commit hash verificado

pendiente
