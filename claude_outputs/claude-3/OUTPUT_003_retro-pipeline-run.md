# OUTPUT_003 — Corrida Retrospectiva 72h (Data Generation Semana 2)

**Fecha:** 2026-04-20
**Rama:** `v2-rewrite` (sin cambios de código)
**Objetivo:** Generar data variada en `costco_motor.db` para que el dashboard de Semana 2 tenga incidentes reales que mostrar
**Estado:** Completo — hallazgos críticos identificados

---

## Contexto

Se intentó primero una estrategia de 4 corridas cada 30 minutos (ventana 3h por defecto). Corrida 1 produjo solo 1 artículo al triage (todos los demás eran duplicados de corridas previas o weather alerts). Se cambió la estrategia a una corrida retrospectiva única con ventana ampliada a 72h.

---

## Configuración de la corrida

```bash
cd ~/code/costco-v2
export $(grep -v '^#' .env | xargs)
export NEWS_MAX_AGE_HOURS=72
python3 scripts/run_pipeline.py
```

- `NEWS_MAX_AGE_HOURS=72` es leído por `src/scrapers/base.py` al momento de importación
- `--dry-run` y `--limit` en el comando original son ignorados (el pipeline no tiene argparse para esos flags; `dry_run=True` ya es hardcoded para Telegram)

---

## Resultado de la corrida retrospectiva

| Métrica | Valor |
|---------|-------|
| Elapsed | 1020s (17 min) |
| Scrapers OK / error | 5 / 0 |
| Artículos procesados | 93 |
| irrelevant (triage) | 71 |
| out_of_radius (geo) | 12 |
| duplicate | 9 |
| **alerted** | **0** |

### Scrapers activos vs rotos
| Scraper | Resultado |
|---------|-----------|
| Protección Civil NL (Google News) | ✓ 100 artículos (filtrados a ~80 frescos en 72h) |
| Bomberos NL (Google News) | ✓ ~20 artículos (muchos internacionales: España, León GTO) |
| Milenio | ✗ 403 Forbidden |
| Info7 | ✗ 404 Not Found |
| El Horizonte | ✗ 404/500 |

---

## Estado consolidado de la DB (todas las corridas acumuladas)

```sql
-- Resultado de: SELECT COUNT(*), passed_triage, classified, within_radius, geo_confident, avg_severity FROM decision_log
total_records = 312
passed_triage = 28
classified    = 28
within_radius = 0      ← CRÍTICO
geo_confident = 13     (geolocation_confidence >= 0.5)
avg_severity  = 4.64
```

### Por tipo de incidente (28 clasificados)
| incident_type | n |
|---------------|---|
| fire | 16 |
| accident | 11 |
| other | 1 |

### Por Costco más cercano
| Costco | Geolocalizado | within_radius |
|--------|:-------------:|:-------------:|
| Cumbres | 12 | 0 |
| Carretera Nacional | 7 | 0 |
| Valle Oriente | 7 | 0 |

---

## Hallazgo crítico: within_radius = 0 en toda la DB

**Todos los incidentes clasificados quedaron out_of_radius.** El geolocator resuelve nombres genéricos de arterias a puntos de referencia fijos incorrectos:

| Referencia en noticia | Distancia resuelta | Esperado |
|----------------------|--------------------|----------|
| "Carretera Nacional" | 6.3km del Costco CN | ~0.3km si es km 268 |
| "Escobedo" | 8.0km del Costco Cumbres | varía; podría ser <3km |
| "Av. Constitución" | 3.7km del Costco Cumbres | debería ser <1km |

El geolocator usa Nominatim y resuelve el nombre de la calle/municipio a un centroide genérico en vez de al tramo específico del incidente. El accidente más relevante de la corrida (severity=8, Carretera Nacional, multi-vehículo) quedó a 6.3km por este motivo.

**Impacto para el dashboard:** mapa vacío. Los 28 incidentes clasificados están en la DB pero ninguno tiene `within_radius = 1`, por lo tanto un query que filtre `within_radius = 1` no devuelve nada.

---

## Costo real (no medible con datos actuales)

El campo `total_tokens_input` no se está escribiendo en `decision_log` para las filas clasificadas. El `decision_logger` actualmente no captura métricas de tokens por artículo.

**Estimación manual:** ~28 triage (Haiku) + ~28 deep_analyze (Sonnet) ≈ $0.05–0.10 por la corrida completa.

---

## Calidad del triage — observaciones

El classifier se comportó bien:

- **Correctamente rechazado:** pronósticos de lluvia ("weather forecast, not active flooding"), rescates en La Huasteca, incidentes en España/León GTO/Tamaulipas, accidentes menores sin bloqueo de arteria
- **Correctamente aceptado:** accidente multi-vehículo Carretera Nacional (severity=8), volcaduras en arteria primaria (severity=7), incendio bodega Escobedo con evacuados (severity=5), accidente Av. Constitución con herido (severity=6)
- **Falso positivo identificado:** tráiler fire en Apodaca clasificado con severity=2 (triage correcto pero classifier lo bajó apropiadamente)

El prompt caching funcionó: `in_tokens=2698–2737` en triage (constante = desde cache después de la primera llamada).

---

## Recomendaciones para el dashboard de mañana (Semana 2)

**Opción A — Fix urgente (T1.2):** Implementar geolocator con `tool_use` de Anthropic que extraiga colonia/calle específica y coordenadas precisas. Sin esto el mapa permanece vacío.

**Opción B — Radio ampliado temporal:** Cambiar `_ALERT_RADIUS_M = 3_000.0` a `10_000.0` en `run_pipeline.py` para una corrida de demo. Capturaría los 26 incidentes que cayeron entre 3–10km. No commitear.

**Opción C — Seed manual:** Insertar 5–10 registros de prueba directamente en `decision_log` con coordenadas reales de incidentes MTY conocidos y `within_radius = 1`. Útil para demo, pero no refleja pipeline real.

**Opción D — Query del dashboard sin filtro de radio:** El dashboard de claude-2 podría mostrar todos los incidentes clasificados (28) en el mapa usando `geo_lat`/`geo_lon`, filtrando solo los que tengan coordenadas, sin requerir `within_radius = 1`. Esto da un mapa poblado con datos reales mientras se arregla el geolocator.

---

## Archivos modificados

Ninguno — corrida de data generation, sin commits.
