# OUTPUT_003 — Week 2 Dashboard Base (T2.1 + T2.2 + T2.4)

**Fecha:** 2026-04-20  
**Rama:** `week2/dashboard-base`  
**Commit:** `65a424c`  
**Estado:** Completo — 39/39 tests pasando

---

## Resumen de cambios

Setup del frontend base del dashboard: mapa Leaflet funcional centrado en Monterrey con los 3 Costcos como pins fijos con círculos de 3km. Sin incidentes todavía (T2.5 es siguiente).

La ruta `GET /` ahora sirve el mapa. La tabla de decision_logs del Fase A se movió a `GET /decisions` para no romper el trabajo de observabilidad previo.

---

## Tabla de archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/dashboard/templates/base.html` | CDN Tailwind, Leaflet 1.9.4, Alpine.js; nav con links a `/` y `/decisions`; `{% block head %}` |
| `src/dashboard/templates/index.html` | **Reemplazado** — ahora es el mapa con Leaflet, 3 Costcos, círculos 3km |
| `src/dashboard/templates/decisions.html` | **Nuevo** — contenido anterior de `index.html` (tabla decision_log) |
| `src/dashboard/routes.py` | `GET /` → mapa (`index.html`); `GET /decisions` → tabla (`decisions.html`) |
| `tests/dashboard/test_index.py` | **Nuevo** — 4 tests: 200, `id="map"`, 3 sucursales en script, leaflet CDN |
| `tests/dashboard/test_routes.py` | `TestIndex` actualizado de `GET /` a `GET /decisions` |

---

## Curl de verificación

```
$ curl -s http://localhost:8001/ | grep -iE "(costco|leaflet|tailwind|map)" | head -8

  <title>Mapa — Costco MTY Alert</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  #map { height: 70vh; }
  .costco-marker {
    <span class="font-bold text-gray-800 mr-2">🛒 Costco MTY Alert</span>
    <a href="/" class="text-gray-600 hover:text-gray-900">Mapa</a>
```

---

## Resultado de pytest

```
tests/dashboard/ — 39 passed in 0.30s
  - test_index.py: 4 nuevos (mapa)
  - test_routes.py: 35 existentes actualizados (/decisions)
```

---

## Decisiones de diseño

1. **`GET /` → mapa, `GET /decisions` → tabla:** El mapa es ahora la pantalla principal del producto. La tabla Fase A quedó en `/decisions` sin romper ningún endpoint ni test existente.

2. **`decisions.html` creado en lugar de eliminar `index.html` de golpe:** Permite que Fase A siga funcionando con sus propios tests durante Semana 2 mientras se construye el dashboard de producto.

3. **Leaflet cargado en `base.html`:** Disponible en todas las páginas. El overhead es bajo (Leaflet es ~40KB gzipped) y simplifica futuras páginas que necesiten mapas.

4. **`/static/style.css` mantenido en `base.html`:** Los templates de Fase A (`detail.html`, `runs.html`) siguen funcionando con sus estilos oscuros propios.
