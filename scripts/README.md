# scripts/run_pipeline.py

CLI para ejecutar un ciclo completo del pipeline de monitoreo Costco Monterrey y guardar las decisiones en base de datos.

## Requisitos

```bash
pip install -e ".[dev]"   # o instalar las deps de pyproject.toml
```

## Uso básico

```bash
# SQLite local (sin configuración, ideal para desarrollo)
python scripts/run_pipeline.py

# Con PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/costco python scripts/run_pipeline.py
```

## Variables de entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./costco_motor.db` | Cadena de conexión SQLAlchemy async |
| `ANTHROPIC_API_KEY` | No* | — | Key para triage + deep_analysis. Sin ella se saltan las etapas de IA |
| `TELEGRAM_BOT_TOKEN` | No | — | Token del bot. Sin él no se construye el cliente Telegram |
| `TELEGRAM_CHAT_ID` | No | — | Chat destino. Requerido junto con `TELEGRAM_BOT_TOKEN` |

> *Sin `ANTHROPIC_API_KEY` el pipeline corre igual pero salta triage/análisis y registra `no_api_key` en el log.

Las variables pueden estar en un archivo `.env` en la raíz del proyecto.

## Qué hace el script

1. Crea las tablas si no existen (útil en primera ejecución con SQLite)
2. Genera un `run_id` UUID único para este ciclo
3. Ejecuta cada scraper de `ALL_SCRAPERS` en secuencia
4. Por cada artículo:
   - **Dedup**: si el título+URL ya fue procesado en las últimas 24h → `duplicate`
   - **Triage** (Claude Haiku): si no es relevante para Costco Monterrey → `irrelevant`
   - **Deep analysis** (Claude Sonnet): clasifica tipo, severidad, impacto en operaciones
   - **Geolocalización**: extrae lugares, geocodifica via Nominatim, calcula distancia a cada Costco
   - **Radio check**: si ningún Costco está a ≤3 km → `out_of_radius`
   - **Umbral de severidad**: si severidad < 5 → `irrelevant`
   - **Notificación** (`dry_run=True`): loguea el mensaje pero no lo envía a Telegram
5. Cada paso se persiste en `decision_log` (UPSERT por `run_id` + `article_url`)
6. Imprime un resumen al final

## Ejemplo de salida

```
════════════════════════════════════════════════════
  Pipeline run: 3f4a1b2c-...
  Elapsed:      42.3s
  Scrapers:     5 OK / 0 error
  Articles:     87 procesados

  Distribución por stage/decisión:
    alerted                  2
    irrelevant              61
    duplicate                9
    out_of_radius            8
    no_geo                   5
    below_threshold          2
════════════════════════════════════════════════════
```

## Ver decisiones guardadas

```bash
# SQLite
sqlite3 costco_motor.db "SELECT run_id, source_name, stage_reached, final_decision, article_title FROM decision_log LIMIT 20;"

# Con pgcli / psql (PostgreSQL)
SELECT run_id, source_name, stage_reached, final_decision, article_title
FROM decision_log
ORDER BY created_at DESC
LIMIT 20;
```

## Notas

- El pipeline **nunca se detiene** por un error en un artículo individual; el error se registra como `final_decision=error` y se continúa con el siguiente.
- Las alertas **siempre corren en dry_run=True** desde este script. Para enviar alertas reales, usar el scheduler (`scheduler.py`) con las variables de entorno completas.
- El caché de dedup es in-memory con TTL de 24h. Se resetea al inicio de cada ejecución del script para evitar acumulación entre ciclos manuales.
