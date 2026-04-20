# Dashboard — Fase A Observabilidad

Interfaz web para revisar decisiones del motor de noticias y capturar feedback humano.

## Requisitos

```
DATABASE_URL=sqlite+aiosqlite:///./costco_motor.db   # default
```

La DB la crea el pipeline (`scripts/run_pipeline.py`). El dashboard es solo lectura + feedback.

## Correr

```bash
uvicorn src.dashboard.main:app --reload
# → http://localhost:8000
```

Al arrancar imprime cuántos `decision_log` hay en la DB.

## Acceder

| Ruta | Descripción |
|---|---|
| `http://localhost:8000/` | Lista paginada de decisiones |
| `http://localhost:8000/runs` | Corridas del pipeline |
| `http://localhost:8000/health` | JSON con estado + conteo |
| `http://localhost:8000/docs` | Swagger UI automático |

## Flujo de revisión

1. Abre `/` → tabla de decisiones
2. Filtra por run_id, decisión final, o "solo sin revisar"
3. Haz click en **Revisar** para ver el detalle completo
4. Usa los atajos de teclado o el formulario para guardar feedback

## Atajos de teclado (vista de detalle)

| Tecla | Acción |
|---|---|
| `1` | Marcar como **correcta** + ir al siguiente sin revisar |
| `2` | Marcar como **incorrecta** + abrir formulario de detalle |
| `3` | **Skip** (sin guardar) + ir al siguiente |
| `←` | Ir al log anterior |
| `→` | Ir al siguiente log |

Los atajos no se activan si el cursor está en un campo de texto/select.

## Filtros disponibles

- **Corrida** — dropdown con últimas 10 run_ids
- **Decisión final** — multi-select (`alert_sent`, `dismissed_*`, `error`)
- **Solo sin revisar** — oculta los que ya tienen feedback

## Modelos de datos usados

- `decision_log` — creado por `fase-a/pipeline` (claude-1)
- `human_feedback` — creado al guardar feedback desde el dashboard

Hasta que `fase-a/pipeline` se integre, el dashboard carga stubs desde
`src/dashboard/_model_stubs.py`. Después del merge, ese archivo se borra.

## Tests

```bash
pytest tests/dashboard/ -v
```

24 tests, SQLite en memoria, sin dependencias externas.
