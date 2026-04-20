# OUTPUT_002 — Semana 1: T1.3 Prompt Caching + T1.7 DB Dedup antes del LLM

**Fecha:** 2026-04-20
**Rama:** `week1/caching-dedup`
**Base:** `origin/v2-rewrite`
**Objetivo:** Reducir costo de input tokens ~90% con prompt caching; eliminar clasificación de duplicados usando dedup DB cross-run
**Estado:** Completo

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---------|----------------|
| `src/analyzer/classifier.py` | +`SYSTEM_PROMPT_TRIAGE`, +`SYSTEM_PROMPT_CLASSIFY`; `system` → `list[dict]` con `cache_control`; `_api_call` signature actualizada |
| `src/analyzer/dedup.py` | +`_TRACKING_PARAMS`, +`_canonicalize_url()`, +`is_duplicate_db()` |
| `scripts/run_pipeline.py` | Import `is_duplicate_db`; dedup check usa ambas capas (in-memory + DB) |
| `tests/analyzer/test_classifier.py` | +`test_classifier_uses_cache_control_triage`, +`test_classifier_uses_cache_control_classify` |
| `tests/analyzer/test_dedup_db.py` | Archivo nuevo: 6 tests (3 URL/sync + 3 DB/async) |

---

## T1.3 — Prompt caching en classifier.py

### Tamaño de los system prompts

| Prompt | Caracteres | Tokens (aprox.) | Califica para cache (≥1024) |
|--------|-----------|-----------------|------------------------------|
| `SYSTEM_PROMPT_TRIAGE` | 6 497 | ~1 624 | ✓ SÍ |
| `SYSTEM_PROMPT_CLASSIFY` | 7 839 | ~1 959 | ✓ SÍ |

Ambos superan el mínimo de 1024 tokens requerido por la API de Anthropic para activar el cache de prefijo ephemeral.

### Contenido de los prompts

**SYSTEM_PROMPT_TRIAGE** (para Haiku — filtro rápido):
- Descripción de las 3 sucursales con rutas de acceso, zonas aledañas y factores de riesgo
- Lista de tipos de incidentes HIGH/MEDIUM priority con criterios claros
- Lista explícita de lo que NUNCA debe flaggearse (deportes, entretenimiento, opinión, estadísticas)
- Alcance geográfico: municipios del AMM + arterias clave
- Reglas de decisión binaria (is_relevant=true/false) con condiciones enumeradas
- 8 ejemplos de calibración (4 relevantes, 4 no relevantes) con razonamiento

**SYSTEM_PROMPT_CLASSIFY** (para Sonnet — análisis completo):
- Contexto operacional completo de las 3 sucursales: direcciones, rutas de acceso ordenadas por importancia, horarios, horas pico, vulnerabilidades específicas
- Definición de 6 tipos de incidente con ejemplos MTY-específicos
- Escala de severidad 1-10 con descripciones por rango y modificadores (+/- puntos)
- Criterios binarios para `affects_operations`
- Tabla de acciones recomendadas por tier de severidad (1-3, 4-5, 6-7, 8, 9-10)
- Instrucción: siempre nombrar sucursal y ruta específica en la recomendación

### Implementación de cache_control

```python
# ANTES (sin caching):
system="You are a triage filter..."  # string literal inline

# DESPUÉS (con caching):
system=[{
    "type": "text",
    "text": SYSTEM_PROMPT_TRIAGE,  # constante estática
    "cache_control": {"type": "ephemeral"},
}]
```

El `_api_call` interno acepta ahora `system: str | list[dict]` y lo pasa directo al SDK sin modificación.

---

## T1.7 — Dedup antes del LLM

### Estado del pipeline antes y después

El pipeline ya tenía dedup antes del triage (en `run_pipeline.py` líneas 119-130). Sin embargo, solo usaba el cache in-memory (`TTLCache` con TTL=24h), que no persiste entre ejecuciones. Se agregó una segunda capa: consulta a `decision_log` en DB.

**Orden del pipeline (sin cambios en el orden, ya era correcto):**
```
scrape → dedup (in-memory + DB) → triage → deep_analyze → geolocate → notify
```

### Dos capas de dedup

**Capa 1 — In-memory (existente, sin cambios):**
- `is_duplicate(title, url)` — TTLCache de 24h, max 10k entradas
- Cubre duplicados dentro de la misma ejecución del pipeline (artículos repetidos en mismo ciclo)
- Hash semántico: título normalizado + URL, insensible al orden de palabras

**Capa 2 — DB (nueva):**
- `is_duplicate_db(title, url, session)` — async, consulta `decision_log`
- Cubre duplicados entre ejecuciones (ciclos de 15 min en producción)
- Dos checks: (a) URL canónica exacta, (b) título normalizado en Python

### URL canonicalization

```python
_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                    "utm_content", "utm_id", "fbclid", "gclid", "msclkid", "ref", "_ga"}

def _canonicalize_url(url):
    # Remueve solo tracking params, preserva el resto del query string
    # Ejemplo: ?id=123&utm_source=google → ?id=123
```

### Normalización de título (existente, reutilizada)

La función `_normalize()` ya existente convierte el título a un "bag of stems" ordenado: lowercase → strip non-alpha → remover stopwords → strip sufijos → sort + dedup. Esto hace que "el incendio en la bodega carretera" y "bodega carretera incendio" produzcan el mismo hash.

### Check en run_pipeline.py

```python
# Línea actualizada en _process_article():
if is_duplicate(article.title, url) or await is_duplicate_db(article.title, url, session):
    # marcar como duplicate y saltar
```

El cortocircuito con `or` garantiza que si in-memory ya encontró el duplicado, no se hace la consulta DB (más costosa).

---

## Resultado de pytest tests/analyzer/

```
tests/analyzer/test_classifier.py      — 11 passed  (+2 vs antes)
tests/analyzer/test_dedup.py           — 11 passed  (sin cambios)
tests/analyzer/test_dedup_db.py        —  6 passed  (archivo nuevo)
tests/analyzer/test_geolocator.py      — 11 passed  (sin cambios)
tests/analyzer/test_types.py           —  7 passed  (sin cambios)
─────────────────────────────────────────────────────
Total                                  — 51 passed / 0 failed
```

---

## Estimación de ahorro por ciclo (T1.3)

Un ciclo típico procesa ~200 artículos:
- Triage (Haiku): 200 llamadas × ~1624 tokens de sistema
- Deep analyze (Sonnet): ~30 llamadas (los que pasan triage) × ~1959 tokens de sistema

Con prompt caching:
- La primera llamada paga el costo completo
- Las 199 siguientes (triage) leen del cache: descuento ~90% en esos tokens
- Las 29 siguientes (deep analyze) leen del cache: descuento ~90%

**Ahorro estimado:**
- Triage: 199 × 1624 tokens × $1/1M (Haiku) × 0.9 = ~$0.00029 ahorrado por ciclo
- Classify: 29 × 1959 tokens × $3/1M (Sonnet) × 0.9 = ~$0.00015 ahorrado por ciclo
- Total: ~$0.00044 ahorrado / ciclo, o ~$2.60 / mes (6 ciclos/hora × 24h × 30 días)

El impacto es mayor cuando se procesan picos de noticias (>500 artículos): el ahorro escala linealmente con N artículos.

**Ahorro de dedup (T1.7):**
Si típicamente 10-15% de artículos son duplicados entre ciclos, evitar clasificarlos ahorra adicionalmente:
- 20 artículos × (1624 Haiku + 1959 Sonnet si hubieran pasado triage) tokens = ~$0.0001 adicional por ciclo
- Más importante: reduce latencia del ciclo y evita contaminación de `decision_log` con entradas duplicadas

---

## Commit hash final

`dc85ed0` (week1/caching-dedup)
