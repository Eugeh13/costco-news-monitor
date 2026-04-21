# Geolocator Fix Research — Semana 3

**Fecha:** 2026-04-20  
**Contexto:** Pipeline 72h produjo 28 incidentes clasificados, 0 `within_radius=1`. Nominatim resuelve nombres genéricos de arterias a centroides incorrectos: "Carretera Nacional" → 6.3km del Costco CN, "Av. Constitución" → 3.7km del Costco Cumbres. Sin fix el mapa del dashboard permanece vacío.

---

## Opciones evaluadas

### Opción A — Google Maps Geocoding API

| Parámetro | Valor |
|-----------|-------|
| Free tier | 10,000 requests/mes (SKU Essentials, desde Mar 2025; antes eran $200 en créditos ≈ 28,500 requests) |
| Costo extra | $5.00 USD / 1,000 requests |
| Volumen estimado | ~200 artículos/ciclo × 6 ciclos/h × 24h = 28,800/día → solo los que pasan triage (~5%) = ~1,440 geocoding/día = ~43,200/mes |
| Costo mensual estimado | 43,200 − 10,000 = 33,200 extra × $5/1,000 = **$166/mes** |
| Precisión MTY | Alta — calle + número de exterior; conoce subdivisions y fracticionamientos de Monterrey |
| Licencia | Los resultados solo pueden mostrarse en mapas de Google (restricción ToS) |
| Complejidad implementación | Baja — `googlemaps` Python client, una línea de cambio en `geolocator.py` |

**Problema:** $166/mes excede el presupuesto de infra ($20–40/mes) y la restricción de ToS impide usar coordenadas en un mapa propio.

---

### Opción B — Mapbox Geocoding API

| Parámetro | Valor |
|-----------|-------|
| Free tier | 100,000 requests/mes (geocoding temporal, sin almacenamiento) |
| Costo extra | $5.00 / 1,000 requests (permanent) · $0.75 / 1,000 (temporary, 100k–500k) |
| Volumen estimado | ~43,200 requests/mes (mismo cálculo que arriba) |
| Costo mensual estimado | Dentro del free tier de 100k → **$0/mes** en uso típico |
| Precisión MTY | Buena — mejor que Nominatim en México; puede aceptar texto libre con `proximity` bias hacia AMM |
| Licencia | Coordenadas pueden usarse en mapas propios; almacenamiento requiere plan Permanent ($5/1k) |
| Complejidad implementación | Baja — REST API + `mapbox-sdk` Python, o `requests` directo |

**Ventaja clave:** 100k requests/mes gratuitos cubre con margen el volumen proyectado (43k/mes). Sin costo en el escenario actual.

---

### Opción C — HERE Maps Geocoding API

| Parámetro | Valor |
|-----------|-------|
| Free tier | 250,000 requests/mes (Freemium, requiere tarjeta de crédito) |
| Costo extra | $1.00 / 1,000 requests |
| Precio Pro | $449/mes (incluye 1M requests + soporte) |
| Volumen estimado | ~43,200 requests/mes |
| Costo mensual estimado | Dentro del free tier de 250k → **$0/mes** |
| Precisión MTY | Alta — base de datos HERE incluye calles y POIs de México; mejor cobertura que OSM en zonas industriales |
| Licencia | Sin restricción de visualización en mapas propios |
| Complejidad implementación | Baja — REST API, Python con `requests` |
| Nota | HERE aumentó tarifas 6% para contratos nuevos desde 1 abril 2026 |

**Ventaja:** free tier más amplio (250k). Sin embargo, requiere cuenta con tarjeta y la documentación para México está menos detallada.

---

### Opción D — INEGI fuzzy matching (local, $0)

| Parámetro | Valor |
|-----------|-------|
| Costo | $0 — catálogo estático descargable |
| Fuente | INEGI DCAH (Delimitación de Colonias y Asentamientos Humanos) + Catálogo Único Geoestadístico |
| Precisión MTY | Media — cubre colonias y municipios del AMM; NO cubre coordenadas de puntos de incidente |
| Enfoque | LLM (`tool_use`) extrae colonia mencionada en el texto → buscar colonia en catálogo INEGI → obtener centroide de colonia |
| Ventaja vs Nominatim | Centroide de colonia (≈500m de radio) vs centroide de municipio/arteria (varios km) |
| Limitación | "Carretera Nacional km 268" → no existe colonia "km 268"; hay que hacer match a "Carretera Nacional" la colonia, que sí tiene centroide |
| Complejidad implementación | Media-alta — descargar SHP INEGI, convertir a GeoJSON/SQLite, implementar fuzzy search (RapidFuzz) |

**Problema real:** El pipeline ya usa LLM para extraer lugares pero sigue pasando el nombre literal a Nominatim. INEGI resuelve colonias, no tramos de arteria. Mejora parcial.

---

### Opción E — Hybrid: LLM tool_use → Mapbox

| Componentes |
|-------------|
| 1. `extract_locations()` actualizado: devuelve `{colonia, via_principal, municipio, coordenadas_aproximadas_si_se_mencionan}` usando `tool_use` en Haiku |
| 2. Geocoder: Mapbox con `proximity=-100.3,25.67` (centro AMM) + `country=MX` + `types=address,neighborhood` |
| 3. Fallback: si Mapbox retorna score < 0.7 → intentar con Nominatim solo como último recurso |

Este enfoque combina extracción semántica mejorada (Claude) con geocodificación precisa (Mapbox), dentro del free tier.

---

## Tabla comparativa

| Criterio | Google Maps | Mapbox | HERE | INEGI local | Hybrid (E) |
|----------|:-----------:|:------:|:----:|:-----------:|:-----------:|
| Costo/mes (volumen actual) | ~$166 | $0 | $0 | $0 | $0 |
| Precisión MTY | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★☆☆☆ | ★★★★☆ |
| ToS: coordenadas propias | ✗ | ✓ | ✓ | ✓ | ✓ |
| Free tier suficiente | ✗ | ✓ (100k) | ✓ (250k) | N/A | ✓ |
| Complejidad impl. | Baja | Baja | Baja | Alta | Media |
| Riesgo técnico | Bajo | Bajo | Medio | Alto | Medio |

---

## Recomendación

**Opción E — Hybrid (LLM tool_use + Mapbox)**, implementada en dos pasos:

1. **Semana 3, Paso 1 (T2.1):** Cambiar geocoder de Nominatim a Mapbox en `geolocator.py`. Cambio de 30 min, elimina el problema de centroides genéricos. Costo: $0. Sin cambio al prompt.

2. **Semana 3, Paso 2 (T2.2):** Actualizar `extract_locations()` para usar `tool_use` y extraer `colonia` + `vialidad_específica` en vez de solo el nombre de la arteria. Esto alimenta Mapbox con queries más precisos.

**Justificación:** Mapbox cubre el free tier con margen (100k vs 43k proyectados), no tiene restricciones de ToS sobre visualización propia, y su API acepta `proximity` bias hacia AMM lo que mejora el ranking de resultados para Monterrey. El paso 2 mejora el input al geocoder independientemente del proveedor elegido.

**Costo mensual:** $0 en el escenario actual. Si el volumen de artículos creciera ×10 (430k geocodings/mes), el costo seguiría siendo $0 con HERE (250k free) y ~$1.65/mes con Mapbox ($0.75/1k en el tramo 100k-500k).

---

## Plan de implementación (Semana 3)

### T2.1 — Swap Nominatim → Mapbox (estimado: 2–3h)

```python
# src/analyzer/geolocator.py

import httpx

MAPBOX_TOKEN = settings.MAPBOX_TOKEN  # nueva var en .env
_AMM_CENTER = "-100.3162,25.6866"      # lon,lat Monterrey centro

async def geocode(place_name: str) -> GeoResult | None:
    url = "https://api.mapbox.com/search/geocode/v6/forward"
    params = {
        "q": place_name,
        "access_token": MAPBOX_TOKEN,
        "country": "MX",
        "proximity": _AMM_CENTER,
        "limit": 1,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
    features = resp.json().get("features", [])
    if not features:
        return None
    feat = features[0]
    lon, lat = feat["geometry"]["coordinates"]
    return GeoResult(lat=lat, lon=lon, address=feat["properties"].get("full_address", ""))
```

Archivos a modificar: `src/analyzer/geolocator.py`, `src/core/settings.py` (+ `MAPBOX_TOKEN`), `.env.example`.

### T2.2 — LLM tool_use para extracción de ubicación (estimado: 4–6h)

Cambiar `extract_locations()` para devolver ubicaciones estructuradas:
- Actualmente: `list[str]` (nombres libres de lugares)
- Nuevo: `list[LocationExtract]` con `colonia`, `vialidad`, `municipio`, `referencia_adicional`

Esto alimenta a Mapbox con queries como `"Col. Carretera Nacional, San Pedro Garza García"` en vez de solo `"Carretera Nacional"`.

---

## Fuentes

- [Google Maps Geocoding — Usage and Billing](https://developers.google.com/maps/documentation/geocoding/usage-and-billing)
- [Mapbox Pricing](https://www.mapbox.com/pricing)
- [Mapbox Geocoding Docs](https://docs.mapbox.com/accounts/guides/pricing/)
- [HERE Maps Pricing — Freemium](https://www.here.com/get-started/pricing)
- [INEGI DCAH — Delimitación de Colonias](https://www.inegi.org.mx/programas/dcah/)
- [Geocoding API Pricing Compared 2026](https://csv2geo.com/blog/geocoding-api-pricing-compared-real-cost-2026)
- [Nominatim OpenStreetMap Wiki](https://wiki.openstreetmap.org/wiki/Nominatim)
