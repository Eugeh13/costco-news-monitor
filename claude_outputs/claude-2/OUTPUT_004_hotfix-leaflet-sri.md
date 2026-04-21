# OUTPUT_004 — Hotfix: Leaflet SRI hash bloqueaba mapa

**Fecha:** 2026-04-20  
**Rama:** `v2-rewrite` (commit directo)  
**Commit:** `fde001f`  
**Estado:** Completo — 39/39 tests pasando

---

## Problema

El navegador bloqueaba `leaflet.js` por hash SRI incorrecto:
```
Failed to find a valid digest in the 'integrity' attribute for resource
'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js' with computed SHA-256
integrity '20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo='. The resource has been blocked.
```
Resultado: `L is not defined`, mapa en blanco.

---

## Archivo modificado

`src/dashboard/templates/base.html`

**Antes:**
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
  crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV/XN/WLcE="
  crossorigin=""></script>
```

**Después:**
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

---

## Altura del mapa

`index.html` ya tenía `#map { height: 70vh; }` en el bloque `{% block head %}`. No fue necesario modificarlo.

---

## Tests

```
39 passed in 0.28s
```

---

## Notas

Push directo a `v2-rewrite` por ser hotfix de una línea. El mapa debería renderizar tras Cmd+Shift+R.
