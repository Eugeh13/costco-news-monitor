# OUTPUT_002 — Week 1 Scrapers Filters (T1.5 + T1.6)

**Fecha:** 2026-04-19  
**Rama:** `week1/scrapers-filters`  
**Commit:** `38fa8b2`  
**Estado:** Completo — 39/39 tests pasando

---

## Resumen de cambios

Implementé T1.5 (filtro de frescura temporal) y T1.6 (parámetro `when:Xh` en Google News RSS) del plan Semana 1.

El control de edad de artículos ahora fluye desde `Settings.news_max_age_hours` → `BaseScraper.max_age_hours` → `_filter_fresh()` → `fetch_google_news(when=N)`. Un solo punto de configuración (`NEWS_MAX_AGE_HOURS` en `.env`) controla todo el sistema.

---

## Tabla de archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/core/config.py` | Agregó `news_max_age_hours: int = Field(default=3, ge=1, le=48)` |
| `src/scrapers/base.py` | `RawArticle.published_at` → `Optional[datetime]`; `_ENV_MAX_AGE_HOURS`; `_is_fresh()`, `_filter_fresh()`, `_timed_fetch()` actualizado |
| `src/scrapers/_google_news_rss.py` | Agrega parámetro `max_age_hours=3`; construye `full_query = f"{query} when:{max_age_hours}h"` |
| `src/scrapers/proteccion_civil.py` | Eliminó filtro inline hardcodeado a 24h; pasa `max_age_hours=self.max_age_hours` |
| `src/scrapers/bomberos_nl.py` | Ídem |
| `tests/scrapers/test_google_news_scrapers.py` | Actualizó `_gnews_url()` para incluir `when:3h`; `test_filters_old_articles` usa `_timed_fetch()` |
| `tests/scrapers/test_freshness.py` | **Nuevo** — 6 tests: `_is_fresh()` stale/no-date/fresh/boundary + `when:Xh` en URL |

---

## Decisiones de diseño

1. **`_ENV_MAX_AGE_HOURS` sin Settings completo:** Los tests de scrapers no necesitan `database_url` ni `anthropic_api_key`. Leer solo `NEWS_MAX_AGE_HOURS` directamente de `os.getenv()` en `base.py` desacopla los scrapers de la inicialización completa de Settings.

2. **`fetch()` no filtra, `_timed_fetch()` sí:** La responsabilidad de filtrar recae en `BaseScraper._filter_fresh()` llamado desde `_timed_fetch()`, no dentro de `fetch()`. Esto mantiene `fetch()` puro (solo obtener datos) y hace testeable el filtro independientemente del transporte HTTP.

3. **`when:Xh` en la query de Google News:** El filtro en la URL de Google News actúa como primera línea de defensa (reduciendo datos descargados). `_filter_fresh()` actúa como segunda línea para artículos sin fecha o con fecha inconsistente.

---

## Resultado de tests

```
39 passed in 46.57s
```
