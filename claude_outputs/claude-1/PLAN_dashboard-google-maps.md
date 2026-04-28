# Plan: Migrate Dashboard Leaflet → Google Maps JavaScript API

## Files to Modify

| File | Change |
|------|--------|
| `src/core/config.py` | Add `google_maps_browser_key: Optional[str]` field |
| `src/dashboard/routes.py` | Pass `maps_browser_key` to `index.html` template context |
| `src/dashboard/templates/base.html` | Remove Leaflet CSS + JS CDN imports |
| `src/dashboard/templates/index.html` | Replace Leaflet JS with Google Maps JavaScript API |
| `.env.example` | Add `GOOGLE_MAPS_BROWSER_KEY=` line |
| `tests/dashboard/test_index.py` | Update `test_index_has_leaflet_cdn_loaded` → check Google Maps |

## Leaflet → Google Maps Element Mapping

| Leaflet | Google Maps |
|---------|-------------|
| `L.map('map').setView([lat, lng], zoom)` | `new google.maps.Map(div, { center: {lat, lng}, zoom })` |
| `L.tileLayer('...osm...').addTo(map)` | **ELIMINATE** — Google Maps includes tiles automatically |
| `L.marker([lat, lng], { icon: L.divIcon({html:'🛒'}) })` | Custom SVG marker: `new google.maps.Marker({ position: {lat, lng}, icon: svgIcon })` |
| `.bindPopup('<b>text</b>')` | `infoWindow.setContent(html); infoWindow.open(map, marker)` on click listener |
| `L.circle([lat, lng], { radius, color, fillColor, fillOpacity })` | `new google.maps.Circle({ center, radius, strokeColor, fillColor, fillOpacity })` |
| `L.popup()` | `new google.maps.InfoWindow()` |

## Loading Google Maps JavaScript API

```html
<!-- In index.html {% block head %} — loaded only on map page, not all pages -->
<script
  async defer
  src="https://maps.googleapis.com/maps/api/js?key={{ maps_browser_key }}&callback=initMap&v=weekly">
</script>
```

- `callback=initMap` — Google Maps calls this function once API is fully loaded
- `v=weekly` — pin to stable weekly channel (avoids breaking changes from `beta`)
- `async defer` — non-blocking load; `initMap` is called when ready

## Injecting GOOGLE_MAPS_BROWSER_KEY via Jinja2

1. `src/core/config.py`: `google_maps_browser_key: Optional[str] = Field(default=None, alias="GOOGLE_MAPS_BROWSER_KEY")`
2. `src/dashboard/routes.py` map_index handler:
   ```python
   from src.core.config import get_settings
   settings = get_settings()
   return TEMPLATES.TemplateResponse(request, "index.html", {
       "maps_browser_key": settings.google_maps_browser_key
   })
   ```
3. Template renders API key into the `<script src>` URL; if `None`, shows an error div instead of the map

## Incident Markers (from /api/incidents)

- Fetch `/api/incidents?since=24h&within_radius_only=true` via `fetch()` after `initMap` runs
- Render each incident with a colored circle SVG marker (red/orange/green by severity)
- Click opens InfoWindow with: title, type, severity, nearest Costco, distance, article link

## Error Handling When Key Not Configured

```jinja2
{% if maps_browser_key %}
  <!-- Google Maps script tag -->
{% else %}
  <!-- Show error message in #map div -->
{% endif %}
```
