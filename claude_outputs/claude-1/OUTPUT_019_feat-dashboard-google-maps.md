# OUTPUT_019 — feat/dashboard-google-maps

**Worker:** claude-1  
**Branch:** feat/dashboard-google-maps  
**Work commit:** db23ca1  
**Date:** 2026-04-27

---

## Archivos modificados

| Path | Tipo de cambio |
|------|---------------|
| `src/core/config.py` | Agregado campo `google_maps_browser_key` |
| `src/dashboard/routes.py` | Importado `os`; ruta `/` pasa `maps_browser_key` al template |
| `src/dashboard/templates/base.html` | Eliminados imports de Leaflet CSS + JS |
| `src/dashboard/templates/index.html` | Reemplazado Leaflet con Google Maps JavaScript API completo |
| `tests/dashboard/test_index.py` | Test actualizado: Leaflet CDN → Google Maps o error fallback |
| `.env.example` | Agregada línea `GOOGLE_MAPS_BROWSER_KEY=` con comentario |
| `claude_outputs/claude-1/PLAN_dashboard-google-maps.md` | Plan de migración creado |

---

## Cambios principales por archivo

### `src/core/config.py`
- Agregado: `google_maps_browser_key: Optional[str] = Field(default=None, description="Google Maps JavaScript API key (browser-side, HTTP referrer restricted)")`
- El campo existente `google_maps_api_key` se anotó explícitamente como server-side

### `src/dashboard/routes.py`
- Eliminado import de `get_settings` (causaba ValidationError en test env donde solo existe `DATABASE_URL`)
- Agregado `import os`
- `map_index` pasa `maps_browser_key = os.environ.get("GOOGLE_MAPS_BROWSER_KEY")` al template
- Justificación: leer directamente del env evita instanciar Settings completo en contexto de dashboard, que no requiere validación de Anthropic/Telegram keys

### `src/dashboard/templates/base.html`
- Eliminadas líneas:
  ```html
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  ```
- Leaflet se cargaba en TODAS las páginas — ahora ninguna página lo carga

### `src/dashboard/templates/index.html`
- `COSTCO_LOCATIONS` se renderiza siempre (fuera del bloque `{% if maps_browser_key %}`) para que los tests y el SEO puedan leer los nombres
- `{% if maps_browser_key %}` controla si se carga la Google Maps JS API o se muestra error
- Función `initMap()` (callback de la API):
  - `google.maps.Map` centrado en Monterrey (25.6767, -100.3161) zoom 12
  - 3 Costco markers con ícono SVG (círculo azul #0066cc + emoji 🛒)
  - 3 `google.maps.Circle` de 3000m, `strokeColor: '#dc2626'`, `fillColor: '#fca5a5'`, `fillOpacity: 0.1`
  - `fetch('/api/incidents?since=24h&within_radius_only=true')` asíncrono, markers de incidentes con círculo coloreado por severidad (rojo ≥8, naranja ≥5, verde <5)
  - `google.maps.InfoWindow` para Costcos y para incidentes (con título, tipo, severidad, distancia, link)
- Error fallback: si no hay key, `#map` se convierte en `#map-error` con mensaje descriptivo

### `tests/dashboard/test_index.py`
- `test_index_has_leaflet_cdn_loaded` → `test_index_has_google_maps_cdn_or_error_fallback`
- En tests, `GOOGLE_MAPS_BROWSER_KEY` no está seteada → renderiza el fallback de error → el test verifica que aparezca `"GOOGLE_MAPS_BROWSER_KEY"` en el body

---

## Mapeo Leaflet → Google Maps

| Leaflet | Google Maps |
|---------|-------------|
| `L.map('map').setView([lat,lng], 12)` | `new google.maps.Map(div, {center:{lat,lng}, zoom:12})` |
| `L.tileLayer('...osm...')` | Eliminado — Google Maps incluye tiles |
| `L.marker([lat,lng], {icon: L.divIcon({html:'🛒'})})` | `new google.maps.Marker({position:{lat,lng}, icon: svgDataUrl})` |
| `.bindPopup(html)` | `infoWindow.setContent(html); marker.addListener('click', ...)` |
| `L.circle([lat,lng], {radius, color, fillColor})` | `new google.maps.Circle({center, radius, strokeColor, fillColor})` |
| `L.popup()` | `new google.maps.InfoWindow()` (una instancia compartida, best practice) |

---

## Decisiones técnicas notables

1. **`os.environ.get()` en vez de `get_settings()`** — La ruta del mapa solo necesita una variable (la browser key). Instanciar `Settings` requiere `DATABASE_URL`, `ANTHROPIC_API_KEY`, `TELEGRAM_*` — variables que no están disponibles en el entorno de tests del dashboard. Leer directamente del env es correcto y no viola el principio de no hardcodear keys.

2. **`AdvancedMarkerElement` descartado** — Requiere `mapId` obligatorio en la instancia del mapa y una carga de librería adicional (`&libraries=marker`). Para este caso de uso (3 markers Costco + N incidentes), el `Marker` clásico con ícono SVG data-URL cumple igual y es más robusto.

3. **Un `InfoWindow` compartido** — Se crea una sola instancia de `InfoWindow` y se reutiliza para todos los markers. Esto sigue el best practice de Google Maps (evita múltiples popups abiertos simultáneamente).

4. **`COSTCO_LOCATIONS` fuera del bloque `{% if %}`** — Los nombres de los 3 Costcos están en el HTML incluso sin API key. Esto mantiene los tests del contenido (`test_index_has_3_costcos_in_script`) sin necesidad de una key válida en el test environment.

5. **`v=weekly` en la URL de carga** — Más estable que `beta` pero más actualizado que pinear a una versión específica como `v=3.56`.

6. **Incidents renderizados** — El dashboard original no renderizaba incidents en el mapa (solo Costco markers y círculos). Se agregó la carga de `/api/incidents` como feature completa, alineada con el endpoint existente `api.py`.

---

## Hallazgos inesperados durante análisis

1. **Dashboard no renderizaba incidents** — El endpoint `/api/incidents` existía y estaba completo, pero la página `index.html` no lo consumía. El mapa original solo mostraba los 3 Costcos y sus círculos. Se aprovechó la migración para agregar esta funcionalidad faltante.

2. **Leaflet cargado en TODAS las páginas** — `base.html` cargaba Leaflet CSS+JS aunque solo `index.html` usa mapa. Esto significaba 200KB+ de JS innecesario en `/decisions`, `/runs`, `/log/{id}`. La migración a Google Maps corrige esto: la API de Maps solo se carga en la página del mapa.

3. **No hay CSS específico de Leaflet en `style.css`** — `style.css` es puramente estilos de la interfaz (tabla de decisiones, dark theme, etc). No había reglas `.leaflet-*` — nada que eliminar del CSS.

---

## Tests

**226/226 passing**

```
226 passed in 49.47s
```

---

## Commit hash

- **Trabajo:** `db23ca1` — feat(dashboard): migrate from Leaflet to Google Maps JavaScript API
