# OUTPUT_008 — Nuevo scheduler v2 para Railway

**Fecha:** 2026-04-22
**Worker:** claude-1
**Rama trabajada:** feat/railway-scheduler
**Commit(s):** `75345aa` (feat(railway): replace v1 scheduler with v2 async pipeline scheduler)

## Qué hace el nuevo scheduler

`scheduler.py` es un loop asyncio que:

1. Al arrancar: corre el pipeline inmediatamente (sin esperar)
2. Mide el tiempo que tardó la corrida
3. Duerme `max(0, 7200 - elapsed)` segundos para mantener ritmo constante de 2h
4. Repite indefinidamente
5. Cualquier excepción en una corrida es capturada y loggeada — el scheduler **nunca muere** por un error del pipeline

Entry-point importado: `from scripts.run_pipeline import main as run_pipeline_main` — llamado con `await run_pipeline_main()`.

Logging a `stdout` con formato `%(asctime)s [%(levelname)s] %(message)s` para que Railway lo capture sin configuración adicional.

## Cómo se diferencia del v1

| Aspecto | v1 (scheduler.py anterior) | v2 (nuevo) |
|---------|---------------------------|------------|
| I/O model | Síncrono (`time.sleep`) | Asyncio (`asyncio.sleep`) |
| Pipeline | `main.build_pipeline()` (v1, ya no existe) | `scripts.run_pipeline.main()` (v2) |
| Configuración | `app.config.settings` (v1, ya no existe) | Sin dependencias de configuración propia |
| Modo nocturno | Pausa 23:00–06:00 CST | Corre 24/7 durante fase de pruebas |
| Intervalo | Dinámico (aumenta si no hay cambios) | Fijo 2h |
| Errores | `traceback.print_exc()` sin recovery | `log.exception()` + continúa |
| Railway-friendly | No (importa módulos v1 rotos) | Sí (stdout logging, no import errors) |

## Función de entry-point usada

```python
from scripts.run_pipeline import main as run_pipeline_main  # async def main() -> None
await run_pipeline_main()
```

Confirmado: `run_pipeline.py` tiene `async def main()` en línea 367, sin argparse (verificado con grep).

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `scheduler.py` | Reemplazado completamente (112 líneas → 55 líneas) |

## Tests

185/185 passed

## Commit hash verificado

```
git log origin/feat/railway-scheduler --oneline -1
75345aa feat(railway): replace v1 scheduler with v2 async pipeline scheduler
```

## URL de la rama

https://github.com/Eugeh13/costco-news-monitor/tree/feat/railway-scheduler
