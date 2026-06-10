# Costco News Monitor

Bot de monitoreo de noticias de seguridad cerca de las tiendas Costco de Monterrey, N.L. — **Costco Valle Oriente** (San Pedro Garza García) y **Costco Carretera Nacional** (sur de Monterrey). Recolecta noticias de múltiples fuentes en ciclos de 5–15 minutos, las clasifica con IA (triage + análisis profundo), verifica que el evento ocurra dentro de un radio de 5 km de alguna tienda y envía alertas por Telegram. Los incidentes confirmados se persisten en PostgreSQL para un dashboard REST (FastAPI).

Incluye además un módulo independiente de **contexto delictivo mensual** (`crime_report.py`) que genera un digest con cifras oficiales del SESNSP para los municipios donde hay Costco.

> **Estado actual:** el despliegue en Railway está **desactivado a propósito** desde ~junio 2026. Para reencenderlo, ver el [RUNBOOK — Reactivar Railway](#-runbook--reactivar-railway).

---

## Arquitectura

Clean Architecture en capas: `app/domain` (modelos y puertos, sin dependencias externas) → `app/services` (lógica de negocio) → `app/infrastructure` (fuentes, IA, Telegram, PostgreSQL) → `app/api` (FastAPI). `main.py` es el único lugar donde se instancian implementaciones concretas.

### Flujo del pipeline (cada ciclo)

```
FUENTES
├── Google News RSS   (queries zona metropolitana MTY, vía requests+UA)
├── RSS directos      (Vanguardia; Milenio eliminado — ya no publica RSS)
├── Nitter (Twitter/X) (11 cuentas PC/seguridad/tráfico, fallback de instancias)
└── GNews             (DESHABILITADA por default — redundante con Google RSS
                       y con fallo SSL en urllib; ver gnews_source.py)
        │
        ▼
[1] Recolección (todas las fuentes, errores aislados por fuente)
        │
        ▼
[2] Hash de cambio (ContentHasher, separador \x1f)
        │   sin cambios → ciclo termina, 0 tokens consumidos
        ▼
[3] Filtro temporal (≤ MAX_AGE_HOURS = 1h, tz America/Chicago)
        │
        ▼
[4] Dedup (processed_news.txt + duplicados en PostgreSQL)
        │   + hint de keywords de alto impacto (señal suave, no filtra)
        ▼
[5] Triage IA en batch (Anthropic u OpenAI, chunks de 25)
        │   descartadas → se marcan procesadas (no se re-paga IA)
        ▼
[6] Análisis profundo por candidata
    ├── lectura completa del artículo (MultiStrategyReader)
    ├── análisis IA: categoría, severidad 1-10, víctimas, tráfico
    ├── geo: Nominatim + fallback por zonas → ¿a ≤ 5 km de un Costco?
    │       (matching de vialidades clave por tienda como respaldo)
    ▼
[7] Alerta Telegram (si falla el envío NO se marca procesada → reintento)
        │
        ▼
[8] PostgreSQL (tabla noticias + vistas para dashboard)
```

### Procesos (server.py)

`server.py` corre **tres hilos en un solo proceso** (es lo que ejecuta Railway, ver `Procfile`):

- **API FastAPI** (hilo principal, uvicorn, puerto `$PORT`): `/health`, `/api/incidents`, `/api/locations`, `/api/stats`.
- **Worker** (`scheduler.py`): pipeline con intervalo dinámico (5→15 min si no hay cambios), pausa nocturna 23:00–06:00 CST, limpieza diaria del archivo de procesadas. Ninguna excepción de ciclo mata el loop; cada ciclo registra un latido en `app/infrastructure/heartbeat.py`.
- **Watchdog**: revisa el heartbeat cada 2 minutos; si el worker lleva 2 chequeos seguidos sin latido (fuera de la tolerancia: sueño planeado + 3× intervalo máximo, con gracia de arranque de 10 min), hace `os._exit(1)` para que Railway reinicie el contenedor. Esto es necesario porque Railway **no** monitorea `/health` en runtime: el 503 del endpoint es observabilidad, la recuperación real es el watchdog.

### Digest mensual SESNSP (fuera del pipeline)

`crime_report.py` descarga en **streaming** el CSV municipal oficial del SESNSP (~380 MB, "Incidencia Delictiva del Fuero Común, Nueva Metodología"), descubre la URL vigente en datos.gob.mx (y como el portal lista el corte con rezago, sondea con HEAD los meses posteriores hasta el actual y usa el más nuevo que exista, avisando si el rezago supera 2 meses), filtra Monterrey (19039) y San Pedro Garza García (19019), y produce un digest comparativo (mes vs mes anterior, vs año anterior, acumulado anual) de: robo de vehículo, robo a negocio, violencia letal (homicidio doloso + feminicidio) y extorsión. Se corre manual con `crime_report.py`, y el worker lo intenta automáticamente cada mes a partir del día `CRIME_DIGEST_DAY` (el SESNSP publica ~día 20; un marcador persistente `YYYY-MM` evita reenvíos en el mismo mes).

### Estructura del proyecto

```
costco-news-monitor/
├── server.py              # Entrada en Railway: API + worker + watchdog
├── scheduler.py           # Loop del worker (intervalos dinámicos, modo nocturno)
├── main.py                # Wiring de dependencias + ejecución única del pipeline
├── crime_report.py        # CLI del digest mensual SESNSP
├── app/
│   ├── domain/            # Modelos Pydantic y puertos (interfaces)
│   ├── config/            # settings.py, locations.py (tiendas), keywords.py
│   ├── services/          # pipeline, triage, deep_analysis, geo, hasher, crime_digest
│   ├── infrastructure/
│   │   ├── ai/            # AnthropicProvider / OpenAIProvider + prompts
│   │   ├── sources/       # google_rss, rss_direct, nitter, gnews (off), sesnsp, deep_reader
│   │   ├── notifications/ # TelegramNotifier / ConsoleNotifier
│   │   ├── persistence/   # PostgresRepository (pool), FileStorage
│   │   └── heartbeat.py   # Latido del worker para /health y watchdog
│   └── api/               # FastAPI: rutas health/incidents/locations/stats
├── tests/                 # Suite pytest (red bloqueada en conftest.py)
├── database_schema.sql    # Tabla noticias + vistas del dashboard
├── Procfile / nixpacks.toml / runtime.txt   # Despliegue Railway
└── docs/                  # Documentación complementaria
```

---

## Correr en local

Requisitos: Python 3.12 (en Railway; el venv local funciona igual), PostgreSQL opcional.

```bash
cd /Users/mac/costco-news-monitor

# 1. Entorno virtual (ya existe en el repo)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements-dev.txt   # pytest (solo desarrollo)

# 2. Configuración
#    Crear .env en la raíz (lo lee pydantic-settings automáticamente)
```

### Variables de entorno (`.env`)

Todas las variables vigentes de `app/config/settings.py` (case-insensitive). Sin Telegram configurado las alertas salen por consola; sin `DATABASE_URL` no se persiste nada (el bot sigue funcionando).

| Variable | Default | Secreto | Propósito |
|---|---|:---:|---|
| `AI_PROVIDER` | `openai` | — | Proveedor de IA: `anthropic` u `openai`. **En producción se usa `anthropic`.** |
| `AI_MODEL` | *(vacío)* | — | Modelo específico. Si se omite: `claude-haiku-4-5-20251001` (anthropic) o `gpt-5-mini` (openai). |
| `ANTHROPIC_API_KEY` | *(vacío)* | **Sí** | API key de Anthropic (requerida si `AI_PROVIDER=anthropic`). |
| `OPENAI_API_KEY` | *(vacío)* | **Sí** | API key de OpenAI (requerida si `AI_PROVIDER=openai`). |
| `TELEGRAM_BOT_TOKEN` | *(vacío)* | **Sí** | Token del bot de Telegram. Sin él, alertas a consola. |
| `TELEGRAM_CHAT_ID` | *(vacío)* | **Sí** | Chat/grupo destino de las alertas. |
| `DATABASE_URL` | *(vacío)* | **Sí** | Cadena de conexión PostgreSQL. Vacía = sin persistencia. |
| `GNEWS_ENABLED` | `false` | — | Reactiva la fuente GNews (deshabilitada: redundante + fallo SSL). |
| `RADIUS_KM` | `5.0` | — | Radio de alerta alrededor de cada Costco. |
| `MAX_AGE_HOURS` | `1` | — | Ventana temporal: solo noticias de la última hora. |
| `TRIAGE_CHUNK_SIZE` | `25` | — | Tamaño de batch para el triage IA. |
| `PROCESSED_NEWS_FILE` | `processed_news.txt` | — | Archivo de dedup de URLs ya procesadas. |
| `MIN_POLL_INTERVAL_MINUTES` | `5` | — | Intervalo mínimo entre ciclos. |
| `MAX_POLL_INTERVAL_MINUTES` | `15` | — | Intervalo máximo (se alarga si no hay cambios). |
| `NIGHT_PAUSE_START` | `23` | — | Hora (CST) de inicio de la pausa nocturna. |
| `NIGHT_PAUSE_END` | `6` | — | Hora (CST) de fin de la pausa nocturna. |
| `CRIME_DIGEST_ENABLED` | `true` | — | Activa el envío mensual automático del digest SESNSP desde el worker. |
| `CRIME_DIGEST_DAY` | `25` | — | Día del mes a partir del cual se intenta el digest (9:00 CST; un marcador `YYYY-MM` evita reenvíos). |
| `PORT` | `8000` | — | Puerto de la API (Railway lo inyecta; no va en settings.py, lo lee server.py). |

### Comandos

```bash
# Un solo ciclo del pipeline (prueba rápida)
.venv/bin/python main.py

# Modo servidor: API + worker continuo + watchdog (lo que corre Railway)
.venv/bin/python server.py

# Digest mensual de criminalidad SESNSP
.venv/bin/python crime_report.py                   # descarga oficial + consola
.venv/bin/python crime_report.py --csv datos.csv   # usa un CSV local
.venv/bin/python crime_report.py --telegram        # además lo envía por Telegram
```

Si la BD es nueva, aplicar el esquema: `psql "$DATABASE_URL" -f database_schema.sql`.

---

## Tests

```bash
.venv/bin/python -m pytest        # toda la suite corre en < 1 s
```

- **Red bloqueada**: `tests/conftest.py` parchea `socket` para que cualquier conexión real falle — los tests nunca tocan red, BD ni APIs de pago (todo con mocks y datos sintéticos).
- **Cobertura**: parsers de respuestas IA de ambos providers (`test_ai_parsers.py` — triage batch, deep analysis, JSON malformado), servicio geo (`test_geo_service.py` — radio, fallback por zonas, matching de vialidades, falsos positivos de "Monterrey" genérico), análisis profundo (`test_deep_analysis.py` — descartes, relevancia, alertas), hasher de contenido (`test_content_hasher.py` — colisiones, separador `\x1f`, contador de ciclos sin cambio), heartbeat (`test_heartbeat.py` — estados starting/ok/atrasado/sin_latido, tolerancia, gracia de arranque), watchdog (`test_watchdog.py` — 2 fallos consecutivos → exit, reset tras un ciclo sano), persistencia (`test_file_storage.py` — limpieza conservando las recientes; `test_postgres_fase2.py` — pool lazy, UniqueViolation benigna, putconn según tipo de error; `test_fecha_evento.py` — tz America/Chicago) y digest mensual (`test_crime_digest_scheduler.py` — gates de día/hora/flag, marcador, no-reenvío, `probe_beyond` con HEAD mockeado).

Reglas del proyecto al desarrollar: no romper la suite, no tocar la BD real, no enviar Telegram real, comentarios en español.

---

## 🚂 RUNBOOK — Reactivar Railway

El bot lleva apagado desde ~junio 2026 (desactivado a propósito). Pasos para reencenderlo:

1. **Reactivar billing** en el dashboard de Railway (la causa del apagado).
2. **`railway login`** — la sesión del CLI está expirada; volver a autenticarse antes de cualquier comando.
3. **Limpiar variables sin uso** en Railway: eliminar `TWITTER_AUTH_TOKEN`, `TWITTER_CT0` y `TWITTER_PROXY`. La vía twscrape fue eliminada del código; Twitter/X ahora entra por Nitter (RSS) sin credenciales.
4. **Verificar IA**: `AI_PROVIDER=anthropic` y `ANTHROPIC_API_KEY` vigente (el default del código es `openai`; en producción se opera con Anthropic).
5. **Deploy desde `main`** de GitHub (`https://github.com/Eugeh13/costco-news-monitor`). Railway usa `nixpacks.toml` (Python 3.12 + playwright chromium) y arranca con `python server.py`.
6. **Validar el arranque**:
   - Logs del primer ciclo: deben verse los pasos 1–6 del pipeline y el conteo por fuente.
   - `GET /health`: ahora devuelve **503 con detalle** (`worker`, `worker_detail`) si el worker murió o está atrasado — y el **watchdog reinicia el contenedor solo** (sale con código 1 tras 2 chequeos fallidos, ~4 min). Hay gracia de arranque de 10 min: "starting" con 200 es normal al inicio.
7. **Verificar el dashboard**: que las vistas (`vista_noticias_recientes`, `vista_impacto_por_costco`, `vista_estadisticas_fuentes`) devuelvan filas cuando entren incidentes — `fecha_evento` ya se escribe en los INSERT (las vistas usan `COALESCE` para filas históricas con NULL).
8. **Nota sobre el backlog**: no habrá avalancha de alertas al reencender. El filtro de 1 hora (`MAX_AGE_HOURS=1`) descarta todo lo publicado durante los meses apagado; solo entra lo de la última hora.

---

## Historial

Auditoría de junio 2026, aplicada en tres fases:

- **Fase 0** — Reparar el bot roto en producción: parser del triage de Anthropic (AttributeError) y fechas de feedparser que llegaban `None` y mataban el filtro de 1 hora.
- **Fase 1** — Eliminar falsos positivos geo (centroide genérico de "Monterrey" dentro del radio de Valle Oriente), dejar de re-pagar IA por noticias ya descartadas y no truncar el triage en lotes grandes.
- **Fase 2** — Robustez operativa: heartbeat + watchdog en `server.py`, pool de conexiones PostgreSQL, `UniqueViolation` tratada como benigna, `fecha_evento` con tz America/Chicago, hasher con separador `\x1f` y providers de IA con manejo amplio de excepciones.

Posteriores: limpieza y validación en vivo de cuentas Twitter vía Nitter, y módulo de digest mensual SESNSP (`crime_report.py`) con descarga remota funcional.
