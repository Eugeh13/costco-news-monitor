# OUTPUT_007 — Fix: ancho de columna alembic_version para PostgreSQL

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** fix/alembic-version-col-width
**Commit(s):** `60f08e2` (fix(migrations): add script to fix alembic_version column width for PostgreSQL)

## Problema

Al correr migraciones contra PostgreSQL de Railway:

```
StringDataRightTruncationError: value too long for type character varying(32)
[SQL: UPDATE alembic_version SET version_num='0002_add_decision_log_and_feedback' ...]
```

Causa: Alembic crea `alembic_version` con `VARCHAR(32)` por defecto. Los nombres de migración en este proyecto superan ese límite:

| Nombre de migración | Longitud |
|---------------------|----------|
| `0002_add_decision_log_and_feedback` | 35 chars ❌ |
| `0003_add_missing_decision_log_fields` | 37 chars ❌ |
| `0004_add_geolocation_fields` | 28 chars ✓ |
| `0005_add_token_cache_and_cost_fields` | 36 chars ❌ |

SQLite ignora las restricciones de longitud VARCHAR; PostgreSQL las hace cumplir estrictamente.

## Fix

Archivo creado: `scripts/fix_alembic_version_col.py`

Script pre-flight que se ejecuta **antes** de `alembic upgrade head`. Lógica:

1. Conecta a PostgreSQL vía `asyncpg` leyendo `DATABASE_URL` del `.env`
2. Consulta `information_schema.columns` para ver el ancho actual de `version_num`
3. Si la tabla **no existe**: la crea con `VARCHAR(128)` y constraint PK
4. Si la tabla **existe con < 128 chars**: ejecuta `ALTER COLUMN ... TYPE VARCHAR(128)`
5. Si ya tiene **≥ 128 chars**: no hace nada (idempotente)

## Uso

```bash
# Antes de las migraciones en Railway:
python3 scripts/fix_alembic_version_col.py
python3 -m alembic upgrade head
```

## Archivos creados/modificados

| Archivo | Cambio |
|---------|--------|
| `scripts/fix_alembic_version_col.py` | NUEVO — script pre-flight idempotente |

## Tests

185/185 passed (el script no toca código de tests; validación de sintaxis con `ast.parse` confirmó que el archivo es sintácticamente correcto).

## Commit hash verificado

```
git log origin/fix/alembic-version-col-width --oneline -1
60f08e2 fix(migrations): add script to fix alembic_version column width for PostgreSQL
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/fix/alembic-version-col-width
