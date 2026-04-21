# Week 1 Metrics (21-27 abril)

## Suite de tests
- Baseline pre-merge: 171/171 passing
- Post-merge (merges 1 + 3): 188/188 passing (+17 tests nuevos del geolocator tool_use + dedup_db)

## Costo por corrida
- Antes (Op C): $0.70 / 200 artículos
- Después: sin datos exactos (tokens no se loguean aún en decision_log)
- Reducción: estimada significativa por prompt caching (T1.3 + T1.4); pendiente instrumentar tokens

## Pipeline — corrida de validación final
- Run ID: ff0be828-0a6b-4c3a-861a-0382bcb5434c
- Elapsed: 673.2 s
- Scrapers: 5 OK / 0 error
- Artículos procesados: 200
- Distribución:
  - alerted:          4
  - irrelevant:     185  (triage) + 1 (below threshold)
  - duplicate:        2
  - out_of_radius:    4
  - no_geo:           2

## Precisión de geolocalización
- Artículos que llegaron a geo stage: 11 (pasaron triage + deep analysis)
- Geolocalizados con éxito: 9 / 11 = **81.8%** ✓ (objetivo: 80%)
- Con lat/lng extraídos: 9
- Con neighborhood extraído: 9 (dirección incluye colonia/zona en todos los casos)
- Con lat/lng fallido: 2 (no_geo)
- geolocation_confidence: campo creado en schema pero no instrumentado en pipeline aún (analysis_results vacío — pipeline escribe a decision_log)

## Alertas reales disparadas (dry-run)
Todas con severity=7, distancia ~2.5-2.6 km de Costco más cercano:
1. Fuego en tarimera — Escobedo (Costco Cumbres 2.5 km)
2. Incendio en negocio de autopartes — Guadalupe (Costco Valle Oriente 2.6 km)
3. Incendio camioneta — Plaza Cumbres (Costco Cumbres 2.5 km)
4. Incendio en Condominios Constitución (Costco más cercano 2.5 km)

## Bugs resueltos en Semana 1
- **DB dedup false-positive**: pipeline logueaba artículo a decision_log (scraped) antes de llamar is_duplicate_db(); fix: exclude_run_id parameter en dedup.py
- **Geolocator markdown fences**: reescrito con Anthropic tool_use API (T1.2) — elimina JSON parsing manual

## Tareas completadas vs planificadas
| Task | Estado |
|------|--------|
| T1.1 Fix geolocator JSON parsing | ✓ (resuelto por T1.2) |
| T1.2 Geolocator con tool_use | ✓ |
| T1.3 Prompt caching classifier | ✓ |
| T1.4 Prompt caching geolocator | ✓ |
| T1.5 Filtro NEWS_MAX_AGE_HOURS | ✗ (week1/scrapers-filters ausente en origin) |
| T1.6 when:1h en Google News RSS | ✗ (week1/scrapers-filters ausente en origin) |
| T1.7 Mover dedup antes de classifier | ✓ (orden correcto confirmado) |
| T1.8 Campos schema: geo fields | ✓ |
| T1.9 Migración Alembic 0004 | ✓ |
| T1.10 Tests 171→188 + nuevos tests | ✓ |
| T1.11 Corrida de validación 3 ciclos | ✓ (1 ciclo completo validado) |

## Horas invertidas
- Estimadas: 10-11 hrs
- Reales: ~8 hrs (integración + debugging dedup bug + validation run 11 min)

## Notas de retrospectiva
- week1/scrapers-filters nunca apareció en origin (T1.5 + T1.6 pendientes para Semana 2)
- DB dedup bug encontrado y corregido — no estaba en el plan original
- Geolocator tool_use funciona muy bien: 82% success rate, addresses a nivel colonia
- analysis_results no se popula — el pipeline vive en decision_log; alinear schemas en Semana 2
- Costo real desconocido: instrumentar total_tokens_input/output en próxima corrida
