# OUTPUT_018 — merge: feat/dashboard-google-maps

**Worker:** integrator  
**Fecha:** 2026-04-27  
**Rama target:** v2-rewrite  
**Commit merge:** 2bf0771  

---

## Resumen

Merge exitoso de `feat/dashboard-google-maps` → `v2-rewrite`.

Claude-1 migró el dashboard de Leaflet/OpenStreetMap a Google Maps JavaScript API para cumplir los Terms of Service de Google Maps Platform. Se eliminó Leaflet completamente y se integró Google Maps JS API con key desde env. Bonus: se agregó renderización de incidents que no existía antes.

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/dashboard/templates/base.html` | Eliminados CSS + JS de Leaflet |
| `src/dashboard/templates/index.html` | Migrado a Google Maps JS API, markers + círculos 3km + incidents |
| `src/dashboard/routes.py` | Pasa `GOOGLE_MAPS_BROWSER_KEY` al template |
| `src/core/config.py` | Agrega `GOOGLE_MAPS_BROWSER_KEY` a Settings |
| `.env.example` | Agrega `GOOGLE_MAPS_BROWSER_KEY=` |
| `tests/dashboard/test_index.py` | Tests actualizados para Google Maps |
| `claude_outputs/claude-1/OUTPUT_019_feat-dashboard-google-maps.md` | Nuevo |
| `claude_outputs/claude-1/PLAN_dashboard-google-maps.md` | Nuevo |

---

## Tests

```
226 passed in 49.74s
```

226/226 tests pasando. Sin regresiones.

---

## Auditoría GOVERNANCE.md

| Check | Estado |
|-------|--------|
| `git status` → working tree clean | PASS |
| `git log origin/v2-rewrite..HEAD` → vacío | PASS |
| `base.html` NO contiene "leaflet" | PASS |
| `index.html` contiene `google.maps.Map` | PASS |
| `.env.example` contiene `GOOGLE_MAPS_BROWSER_KEY` | PASS |
| `OUTPUT_019` de claude-1 presente | PASS |

---

## Hashes verificados

| Ref | Hash |
|-----|------|
| Merge commit | `2bf0771` |
| Commit feat (claude-1) | `db23ca1` |
| Commit pre-merge v2-rewrite | `4c8c368` |

---

## Rama remota

`origin/v2-rewrite` actualizado a `2bf0771`.
