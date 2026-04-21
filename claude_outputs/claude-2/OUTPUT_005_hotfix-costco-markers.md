# OUTPUT_005 — Hotfix: markers 🛒 no visibles en mapa

**Fecha:** 2026-04-20  
**Rama:** `v2-rewrite` (commit directo)  
**Commit:** `1fdfa48`  
**Estado:** Completo — 39/39 tests pasando

---

## Problema

Los 3 markers existían en el DOM (`.leaflet-marker-icon` × 3) pero no eran visibles porque `.costco-marker` no tenía los estilos suficientes para sobreescribir los defaults de Leaflet (que aplica `background` y `border` propios al divIcon).

---

## Archivo modificado

`src/dashboard/templates/index.html`

### CSS (bloque `{% block head %}`)

**Antes:**
```css
#map { height: 70vh; }
.costco-marker {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: transparent;
  border: none;
}
```

**Después:**
```css
#map {
  height: 70vh;
  min-height: 500px;
  width: 100%;
}
.costco-marker {
  font-size: 28px;
  line-height: 1;
  text-align: center;
  background: transparent !important;
  border: none !important;
  width: 40px !important;
  height: 40px !important;
  display: flex !important;
  align-items: center;
  justify-content: center;
}
```

### JS — divIcon

**Antes:**
```js
iconSize: [32, 32]
```

**Después:**
```js
iconSize: [40, 40],
iconAnchor: [20, 20]
```

---

## Tests

```
39 passed in 0.29s
```
