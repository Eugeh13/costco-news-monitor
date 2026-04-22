# OUTPUT_010 — Fix: requirements.txt para Railpack + eliminar nixpacks.toml

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** fix/railway-requirements
**Commit(s):** `c8c885f` (fix(deploy): add requirements.txt for Railpack, remove deprecated nixpacks.toml)

## Problema

Railpack (sistema de build actual de Railway) prefiere `requirements.txt` sobre `pyproject.toml`. Sin `requirements.txt`, omite la instalación de dependencias y el worker falla con:

```
ModuleNotFoundError: No module named 'structlog'
```

`nixpacks.toml` era un archivo del sistema previo (Nixpacks, deprecated) y estaba siendo completamente ignorado por Railpack.

## Fix

### Archivo creado: `requirements.txt`

17 dependencias exactas de `pyproject.toml` `[project.dependencies]`:

```
sqlalchemy[asyncio]>=2.0
alembic>=1.13
asyncpg>=0.29
pydantic>=2.6
pydantic-settings>=2.2
fastapi>=0.111
uvicorn[standard]>=0.29
anthropic>=0.25
structlog>=24.1
httpx>=0.27
tenacity>=8.2
feedparser>=6.0
pytz>=2024.1
selectolax>=0.3
aiosqlite>=0.20
rich>=13.0
jinja2>=3.1
python-multipart>=0.0.9
```

No se incluyen dependencias de `[project.optional-dependencies].dev` (pytest, mypy, ruff) — solo producción.

### Archivo eliminado: `nixpacks.toml`

Eliminado con `git rm`. Nixpacks está deprecated en Railway; el archivo era ignorado.

### Procfile

Sin cambios — ya estaba correcto: `worker: python3.11 scheduler.py`

## Validación local con venv temporal

```bash
python3 -m venv /tmp/railway-test-venv
/tmp/railway-test-venv/bin/pip install -r requirements.txt
```

Resultado: `Successfully installed` — 47 paquetes instalados sin errores.

## Tests

185/185 passed

## Commit hash verificado

```
git log origin/fix/railway-requirements --oneline -1
c8c885f fix(deploy): add requirements.txt for Railpack, remove deprecated nixpacks.toml
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/fix/railway-requirements
