# OUTPUT_020 — Fix Costco Coordinates (ROOFTOP Precision)

**Date:** 2026-05-03
**Worker:** claude-1
**Branch:** fix/costco-real-coordinates
**Commit (trabajo):** aa66fc5
**Tests:** 226/226 passing

---

## Archivos modificados (9)

| File | Tipo de cambio |
|---|---|
| `src/dashboard/templates/index.html` | Coordenadas JS array COSTCO_LOCATIONS |
| `src/analyzer/geolocator.py` | Coordenadas dict COSTCO_LOCATIONS + sistema prompt |
| `tests/analyzer/test_geolocator.py` | Comentario + rango de distancia CN→VO |
| `tests/analyzer/test_geolocator_google.py` | Default mock lat/lng + assertions |
| `tests/analyzer/test_geolocator_tool_use.py` | Mock input + assertions Carretera Nacional |
| `tests/core/test_decision_logger.py` | geo_lat/geo_lon test data + assertion |
| `tests/dashboard/conftest.py` | geo_lat/geo_lon test fixture |
| `tests/dashboard/test_api_incidents.py` | geo_lat/geo_lon test fixture |
| `tests/models/test_decision_log.py` | geo_lat/geo_lon test data |

---

## Coordenadas: viejo → nuevo

| Costco | lat viejo | lng viejo | lat nuevo | lng nuevo | Fuente |
|---|---|---|---|---|---|
| Carretera Nacional | 25.6026 | -100.2640 | 25.577970 | -100.251028 | Google Geocoding API ROOFTOP |
| Cumbres | 25.7353 | -100.4022 | 25.729656 | -100.392913 | Google Geocoding API ROOFTOP |
| Valle Oriente | 25.6457 | -100.3072 | 25.639695 | -100.317631 | Google Geocoding API ROOFTOP |

Nuevas direcciones (ROOFTOP):
- **Carretera Nacional:** Km 268 + 500, Carr Nacional 501, Bosques de Valle Alto, 64989 Monterrey, N.L.
- **Cumbres:** Calle Alejandro de Rodas 6767, Pedregal Cumbres, 64340 Monterrey, N.L.
- **Valle Oriente:** Av Lázaro Cárdenas 800, Zona Valle Oriente, 66269 San Pedro Garza García, N.L.

---

## Distancia aproximada entre coordenada vieja y nueva (haversine)

| Costco | Δ distancia (m aprox) |
|---|---|
| Carretera Nacional | ~3,200 m |
| Cumbres | ~630 m |
| Valle Oriente | ~730 m |

La mayor diferencia es en Carretera Nacional (~3.2 km), lo que confirma que las coordenadas anteriores estaban notablemente desplazadas.

---

## Nota sobre distancia CN→VO

La distancia Haversine entre Carretera Nacional y Valle Oriente cambió de ~6.5 km (coordenadas viejas) a ~9.5 km (coordenadas ROOFTOP). Se actualizó el rango en `test_geolocator.py` de `5_000 < d < 9_000` a `5_000 < d < 12_000`.

---

## Tests

```
226 passed in 49.69s
```

---

## Verificación origin

```
aa66fc5 fix(dashboard): correct Costco coordinates with Google Geocoding ROOFTOP precision
```
