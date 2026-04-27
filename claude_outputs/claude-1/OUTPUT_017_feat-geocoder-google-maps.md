# OUTPUT_017 — feat(geocoder): replace Nominatim with Google Geocoding API

**Fecha:** 2026-04-26
**Worker:** claude-1
**Rama trabajada:** feat/geocoder-google-maps
**Commit(s):** pendiente

## Problema

Pipeline 72h produjo 28 incidentes con 0 dentro del radio de 3 km. Causa: Nominatim retornaba centroides imprecisos para nombres de arterias y colonias en Monterrey (ej: centroide de "Cumbres" al nivel de municipio en lugar de la colonia exacta).

## Cambios aplicados

### `src/analyzer/geolocator.py`

- Eliminado: `_NOMINATIM_BASE`, `_NOMINATIM_UA`, rate-limiter (`_last_geocode_t`, `_geocode_lock`, `asyncio.Lock`)
- Nuevo: `_GOOGLE_GEOCODE_URL`, `_MTY_BOUNDS` (bounding box AMM para bias geográfico)
- `geocode()` reemplazado completamente: Google Geocoding API via httpx
  - Parámetros: `region=mx`, `bounds=25.5,-100.5|25.9,-100.1`, `language=es`
  - Rechaza resultados `APPROXIMATE + partial_match=True` (centroides de área grande)
  - Retry 1 vez en `TransportError` (timeout, conexión caída)
  - Logging estructurado: `geocoder.success` / `geocoder.no_result` / `geocoder.error`
  - Retorna `None` si `GOOGLE_MAPS_API_KEY` no está configurada (no lanza excepción)
- Nueva función helper: `_location_type_confidence()` — mapea `ROOFTOP→1.0`, `RANGE_INTERPOLATED→0.85`, `GEOMETRIC_CENTER→0.7`, `APPROXIMATE→0.5`
- Interfaz pública **sin cambios**: `async def geocode(address, *, http_client, api_key) -> GeoLocation | None`

### `src/core/config.py`

- Agregado: `google_maps_api_key: Optional[str] = Field(default=None, ...)`
- Nota: el archivo es `config.py`, no `settings.py` — la tarea mencionaba `settings.py` pero el módulo real es `config.py`

### `.env.example`

- Agregada línea: `GOOGLE_MAPS_API_KEY=`

### `tests/analyzer/test_geolocator.py`

- Actualizados los 3 tests de `geocode()`: mocks cambiados de formato Nominatim a formato Google Geocoding API
- `test_geocode_success`: ahora usa Google response + pasa `api_key="test-key"`
- `test_geocode_empty_results`: ahora usa `{"status": "ZERO_RESULTS", "results": []}`
- `test_geocode_http_error`: agrega `api_key="test-key"`

### `tests/analyzer/test_geolocator_google.py` (nuevo)

5 tests nuevos:
1. `test_geocode_returns_precise_result_for_known_address` — ROOFTOP result retorna GeoLocation con confidence=1.0
2. `test_geocode_returns_none_for_zero_results` — ZERO_RESULTS retorna None
3. `test_geocode_returns_none_for_partial_match_approximate` — APPROXIMATE+partial_match rechazado
4. `test_geocode_handles_timeout` — TransportError dispara retry; 2 intentos totales, retorna None
5. `test_geocode_includes_region_and_bounds_for_mty_bias` — verifica params region=mx, bounds con 25.5,-100.5, language=es, "Monterrey" en address

## Decisiones técnicas notables

- **`api_key` como parámetro explícito**: permite tests sin variables de entorno; en producción se lee de `os.environ.get("GOOGLE_MAPS_API_KEY")`
- **Sin rate-limiter**: Google Geocoding API no requiere 1 req/s como Nominatim. El free tier es 10k/mes (~432 req/mes estimados)
- **Reject APPROXIMATE+partial_match**: combinación específica que indica que Google no encontró la calle/número y devolvió el centroide de la colonia/municipio — exactamente el problema que teníamos con Nominatim
- **Retry solo en TransportError**: errores HTTP (4xx/5xx) no se reintentan; solo errores de red transitorios

## Tests

226/226 passed (5 nuevos en `test_geolocator_google.py` + 3 actualizados en `test_geolocator.py`)

## Verificación de criterios de aceptación

- [x] Tests pasan: 226/226 (221 + 5 nuevos)
- [x] Interfaz pública `geocode()` no cambió (drop-in replacement)
- [x] Sin imports de Nominatim/geopy en geolocator.py
- [x] `.env.example` refleja `GOOGLE_MAPS_API_KEY`

## Commit hash verificado

pendiente
