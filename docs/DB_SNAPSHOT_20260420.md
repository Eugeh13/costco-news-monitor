# DB Snapshot — 20 abril 2026

**Generado:** 2026-04-20 ~20:10 CST  
**DB:** `costco_motor.db` (SQLite dev)  
**Tabla:** `decision_log`

---

## Resumen general

| Métrica | Valor |
|---------|-------|
| Total records | 331 |
| Records con tokens | 19 |
| Artículos clasificados (incident_type != NULL) | 28 |
| Within radius (= 1) | **0** ← issue conocido (within_radius=NULL en runs previos) |
| Costo total medido | **$0.0187 USD** |

---

## Por tipo de incidente

| Tipo | Count |
|------|-------|
| fire | 16 |
| accident | 11 |
| other | 1 |
| **Total** | **28** |

Fuegos dominan (57%) — tiene sentido para MTY industrial.

---

## Por decisión final

| final_decision | Count | % |
|----------------|-------|---|
| irrelevant | 269 | 81.3% |
| duplicate | 39 | 11.8% |
| out_of_radius | 17 | 5.1% |
| alerted | 4 | 1.2% |
| no_geo | 2 | 0.6% |

**Tasa de alerta real: 4 / 331 = 1.2%** — pipeline muy conservador, correcto para evitar alert fatigue.

---

## Historial de runs

| run_id | rows | con_tokens | costo_usd | iniciado (UTC) |
|--------|------|-----------|-----------|----------------|
| 0c052a0c | 9 | 0 | $0.0000 | 2026-04-21 02:04 |
| 4459d992 | 10 | 6 | **$0.0187** | 2026-04-21 01:53 |
| c2911dc5 | 90 | 0 | $0.0000 | 2026-04-21 00:57 |
| 3dc11acd | 12 | 0 | $0.0000 | 2026-04-21 00:42 |
| 610e6552 | 12 | 0 | $0.0000 | 2026-04-21 00:27 |
| ff0be828 | 198 | 0 | $0.0000 | 2026-04-20 23:49 |

**Notas:**
- `ff0be828`: primera corrida completa (200 artículos, pre-filtros `when:1h`), token logging no instrumentado aún
- `c2911dc5`: 90 rows — run de prueba grande de claude-1 durante desarrollo del token fix
- `4459d992`: **único run con token logging activo** — $0.0187 en 6 artículos con LLM calls
- `0c052a0c` / `3dc11acd` / `610e6552`: runs post-`when:1h`, todo duplicados o sin LLM calls

---

## Issues identificados en el snapshot

### 1. within_radius = 0 en todos los registros
- 17 artículos con `final_decision = out_of_radius` tienen `within_radius = 0`
- 4 artículos `alerted` tienen `within_radius = NULL` (escritos antes de que el campo existiera)
- **Consecuencia:** `/api/incidents?within_radius_only=true` devuelve 0 resultados
- **Causa raíz:** geolocator Nominatim resuelve a centroides genéricos fuera del radio de 3km
- **Fix:** Semana 3 (ver `docs/GEOLOCATOR_FIX_RESEARCH.md`)

### 2. Costo real subestimado
- Solo `4459d992` tiene tokens capturados ($0.0187 / 6 artículos con LLM)
- Los 5 runs anteriores tienen `cost_estimated_usd = NULL` o `0`
- Costo real del día ≈ $0.10-0.20 estimado (sin instrumentación en esos runs)
- Token logging ya activo desde merge `week2/decision-logger-tokens-fix` — próximos runs sí capturarán

### 3. Ratio irrelevante alto (81%)
- Es esperado y correcto: la mayoría de noticias no son incidentes cercanos a Costco
- Triage con Haiku está funcionando como primer filtro efectivo

---

## Proyecciones

Con `when:1h` activo: ~10-20 artículos / corrida cada 15 min  
Artículos por día: ~1,000-2,000  
Costo proyectado/día: ~$0.03-0.10 USD (basado en $0.0187 / 6 artículos con LLM)  
Costo proyectado/mes: ~$1-3 USD ← bien dentro del presupuesto de $5-15 USD

---

*Snapshot generado manualmente. Próxima actualización: al final de Semana 2.*
