# OUTPUT_004 — ops/manual-run-script: dev_run.sh + OPERATIONS.md

**Fecha:** 2026-04-20  
**Rama:** `ops/manual-run-script` (base: `origin/v2-rewrite`)  
**Commit:** `b310fe5`  
**Estado:** Completo

---

## Archivos creados

| Archivo | Descripción |
|---------|-------------|
| `scripts/dev_run.sh` | Script wrapper para corridas manuales diurnas |
| `docs/OPERATIONS.md` | Guía de operaciones (corridas manuales + cron nocturno) |

---

## scripts/dev_run.sh

### Comportamiento

```
./scripts/dev_run.sh           # modo quick (default)
./scripts/dev_run.sh --quick   # NEWS_MAX_AGE_HOURS=3, ~30s, barato
./scripts/dev_run.sh --full    # NEWS_MAX_AGE_HOURS=6, ~2-5min
```

1. Hace `cd /Users/mac/code/costco-v2` — funciona desde cualquier directorio
2. Carga `.env` con `set -a; source .env; set +a` — sin necesidad de `export` manual
3. Exporta `NEWS_MAX_AGE_HOURS` según el modo
4. Corre `scripts/run_pipeline.py` con output colorido en terminal
5. Al terminar: consulta SQLite y muestra 3 métricas de la corrida

### Resumen DB al final (ejemplo de output)

```
=== DB state ===
Total records: 320
Records last 10 min: 8
Cost last 10 min (USD): 0.0023
```

---

## docs/OPERATIONS.md

Creado porque NO existía en `v2-rewrite`. Contiene:
- Uso de `dev_run.sh` (--quick / --full) con descripción de cada modo
- Lo que hace el script (cd, .env, resumen DB)
- Referencia al cron nocturno (22:00–08:00, cada 2h)
- Comando `crontab -l` para verificar

**Nota para el integrator:** Si `claude-1` crea `OPERATIONS.md` en su rama de forma independiente, habrá conflicto de merge. Resolver tomando la versión de claude-1 y añadiendo la sección `## Corridas manuales en desarrollo` de este archivo.

---

## Decisiones de implementación

- **`set -e` y `set -u`**: el script aborta inmediatamente si cualquier comando falla o si se usa una variable no definida. Evita corridas silenciosas con errores parciales.
- **`MODE="${1:---quick}"`**: el primer argumento es opcional; si no se pasa, usa `--quick`. No se valida el argumento explícitamente — si se pasa algo desconocido como `--turbo`, el script cae en el bloque `else` y usa modo quick (comportamiento conservador).
- **`/usr/local/bin/python3`**: path absoluto para evitar problemas con `python3` del sistema vs el virtualenv cuando se llama desde cron o desde un directorio distinto. Si el proyecto migra a `uv`/`venv` habrá que ajustar.
- **Here-doc SQLite**: el summary de DB usa un heredoc dentro del script bash para pasar múltiples queries a `sqlite3`. No requiere instalar nada extra.

---

## Pendiente (no en esta tarea)

- Si el proyecto migra a PostgreSQL, el bloque `=== DB state ===` necesitará adaptar las queries (cambiar `sqlite3` por `psql` y la sintaxis de `datetime('now', '-10 minutes')`).
- El campo `cost_estimated_usd` en `decision_log` actualmente puede ser NULL para las filas clasificadas (hallazgo de OUTPUT_003). El `SUM()` de NULL devuelve NULL, no 0 — se verá `Cost last 10 min (USD): ` vacío hasta que se arregle T2.3.
