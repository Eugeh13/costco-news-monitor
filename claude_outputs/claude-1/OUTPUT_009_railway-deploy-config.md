# OUTPUT_009 — Fix: configuración de deploy Railway para v2

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** fix/railway-deploy-config
**Commit(s):** `c52c897` (fix(deploy): update Railway config for v2 (Procfile, nixpacks, remove server.py))

## Problema

Railway desplegó el worker pero falló con:

```
ModuleNotFoundError: No module named 'structlog'
```

Causa: `Procfile` y `nixpacks.toml` eran de v1 y no instalaban las dependencias de `pyproject.toml`.

## Fix Procfile

```
# Antes
web: python server.py

# Después
worker: python3.11 scheduler.py
```

- `web:` → `worker:` porque el scheduler no sirve HTTP
- `server.py` → `scheduler.py` (v2)

## Fix nixpacks.toml

| Aspecto | Antes | Después |
|---------|-------|---------|
| Python version | `python312` | `python311` (coincide con `runtime.txt`) |
| Install cmd | `pip install -r requirements.txt` | `pip install -e .` (usa `pyproject.toml`) |
| Playwright | `playwright install chromium` | Eliminado (v2 no lo usa) |
| Fases | setup mezclado con install cmds | Separado en `[phases.setup]` y `[phases.install]` |
| Start cmd | `python server.py` | `python3.11 scheduler.py` |

## Archivo eliminado: server.py

`server.py` ya **no existía** en `v2-rewrite` — fue eliminado en un merge previo. El `git rm` fue innecesario (confirmado con `ls server.py` antes de ejecutar).

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `Procfile` | `web: python server.py` → `worker: python3.11 scheduler.py` |
| `nixpacks.toml` | python311, pip install -e ., sin playwright, fases correctas |

## Tests

185/185 passed

## Commit hash verificado

```
git log origin/fix/railway-deploy-config --oneline -1
c52c897 fix(deploy): update Railway config for v2 (Procfile, nixpacks, remove server.py)
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/fix/railway-deploy-config
