# Week 1 Metrics (21-27 abril)

## Suite de tests
- Baseline pre-merge: 171/171 passing
- Post-merge (merges 1 + 2 + 3): 194/194 passing (+23 tests vs baseline)

## Pipeline — comparativa de corridas

| Métrica | Corrida A (pre-filtros) | Corrida B (todos los filtros activos) |
|---|---|---|
| Run ID | ff0be828 | 610e6552 |
| Artículos procesados | 200 | **16** (-92%) |
| Scrapers OK / error | 5 / 0 | 5 / 0 |
| Elapsed | 673 s | 133 s |
| Alertas disparadas | 4 | 0 (incidentes del run A ya en DB dedup) |
| Irrelevantes (triage) | 185 | 8 |
| Duplicados | 2 | 4 |
| Out of radius | 4 | 4 |
| No geo | 2 | 0 |
| Below threshold | 1 | 0 |

**El filtro `when:1h` en Google News RSS redujo de 200 a 16 artículos por corrida (-92%). Objetivo de reducción de costo: cumplido.**

## Costo por corrida
- Antes (Op C): $0.70 / 200 artículos (~$0.0035/artículo)
- Después con `when:1h`: estimado proporcional ~$0.011 / 16 artículos
- Costo exacto: sin instrumentar (total_tokens_input/output no se popula aún)
- Acción requerida Semana 2: instrumentar conteo de tokens en el pipeline

## Precisión de geolocalización — Corrida A (200 artículos, más representativa)
- Artículos que llegaron a geo stage: 11
- Geolocalizados con éxito: 9 / 11 = **81.8%** ✓ (objetivo: 80%)
- Con lat/lng (Nominatim): 9
- Con neighborhood extraído: 9 (dirección incluye colonia/zona)

## Campos nuevos en decision_log — Corrida B (primer run con schema completo)
- `approximate_location` poblado: 4 / 4 que llegaron a geo
- `geolocation_confidence` poblado: 4 / 4
- Con confidence >= 0.5: **3 / 4** (0.5, 0.65, 0.75)
- `exact_location_lat/lng` (LLM inference): 0 / 4 (LLM no infirió coords con alta confianza — Nominatim sigue siendo la fuente de lat/lng)
- Verificación DB:
  ```
  SELECT COUNT(*) FROM decision_log WHERE approximate_location IS NOT NULL
  -- run 610e6552: 4
  ```

## Tareas completadas vs planificadas
| Task | Estado |
|------|--------|
| T1.1 Fix geolocator JSON parsing | ✓ (resuelto por T1.2) |
| T1.2 Geolocator con tool_use | ✓ |
| T1.3 Prompt caching classifier | ✓ |
| T1.4 Prompt caching geolocator | ✓ |
| T1.5 Filtro NEWS_MAX_AGE_HOURS | ✓ (merge final completado) |
| T1.6 when:1h en Google News RSS | ✓ (merge final completado) |
| T1.7 Mover dedup antes de classifier | ✓ |
| T1.8 Campos schema: geo fields → decision_log | ✓ (migración 74b26b81) |
| T1.9 Migración Alembic 0004 + 74b26b81 | ✓ |
| T1.10 Tests 171→194 + nuevos tests | ✓ |
| T1.11 Corrida de validación | ✓ (2 corridas documentadas) |

## Bugs resueltos fuera del plan original
- **DB dedup false-positive**: exclude_run_id fix en dedup.py + run_pipeline.py
- **Schema mismatch decision_log vs analysis_results**: 4 campos de geo agregados a decision_log

## Horas invertidas
- Estimadas: 10-11 hrs
- Reales: ~10 hrs (incluye debugging dedup bug + merge + validation runs)

## Notas de retrospectiva
- `when:1h` es el cambio de mayor impacto: 200 → 16 artículos/corrida → estimado -92% en costo
- Geolocator tool_use: 82% success rate en Corrida A, addresses a nivel colonia/zona
- `analysis_results` no se usa — pipeline vive completamente en `decision_log`
- Milenio / Info7 / Horizonte: 0 artículos (403/404 persistentes)
- Costo real: pendiente instrumentar tokens en Semana 2
