# OUTPUT_001 — Hotfix dashboard-align (Op C)

**Fecha:** 2026-04-19  
**Rama:** `hotfix/dashboard-align`  
**Commit:** `67b82e0`  
**Estado:** Completo — 24/24 tests pasando

---

## Resumen de cambios

Alineé el dashboard con el modelo real `DecisionLog` / `HumanFeedback` de `src/models/`. Eliminé `_model_stubs.py` por completo. Los 7 renombres de campo fueron aplicados. Los enums de `FinalDecision` y `StageReached` actualizados. El modelo `HumanFeedback` real solo tiene `should_have_been` (no tiene `was_correct` ni `notes`), por lo que el formulario de feedback fue simplificado acordemente.

---

## Tabla de archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/dashboard/main.py` | Eliminó `try/except ImportError` → import directo `from src.models.decision_log import DecisionLog` |
| `src/dashboard/routes.py` | Eliminó `try/except`; corrigió `_decision_class()` (`"alert_sent"` → `"alerted"`); `entry.feedback` → `entry.human_feedbacks`; `save_feedback()` simplificado a solo `should_have_been`; runs query `"alert_sent"` → `"alerted"` |
| `src/dashboard/templates/detail.html` | 7 renombres de campo; eliminó secciones de campos no existentes aún (tokens, within_radius, is_duplicate, telegram_sent, error_stage); actualizó feedback form para usar solo `should_have_been`; actualizó JS keyboard shortcuts |
| `src/dashboard/templates/index.html` | `classified_severity` → `severity_score`; `geo_distance_meters` → `nearest_costco_dist_m`; `log.feedback` → `log.human_feedbacks` |
| `tests/dashboard/conftest.py` | Import `_Base` → `from src.core.database import Base`; imports reales de `src.models.*`; `_Base.metadata` → `Base.metadata`; seed data con campos y enums reales (7 renombres, eliminados 8 campos de DecisionLog que claude-1 añade en `hotfix/model-fields`) |
| `tests/dashboard/test_routes.py` | Imports de `src.models.*`; HumanFeedback sin `was_correct`/`notes`; valores de enum reales (`"alerted"`, `"irrelevant"`, etc.); feedback tests adaptados a `should_have_been` |
| `src/dashboard/_model_stubs.py` | **ELIMINADO** (`git rm`) |

---

## Detalle de renombres aplicados

| Campo stub | Campo real | Dónde |
|-----------|------------|-------|
| `article_published_at` | `published_at` | detail.html |
| `triage_reasoning` | `triage_reason` | routes.py, detail.html, conftest.py |
| `classified_type` | `incident_type` | detail.html, conftest.py |
| `classified_severity` | `severity_score` | index.html, detail.html, conftest.py |
| `classified_reasoning` | `ai_reasoning` | detail.html, conftest.py |
| `geo_closest_costco` | `nearest_costco` | detail.html, conftest.py |
| `geo_distance_meters` | `nearest_costco_dist_m` | index.html, detail.html, conftest.py |

### Enums actualizados

**FinalDecision:** `alert_sent` → `alerted`, `dismissed_not_relevant` → `irrelevant`, `dismissed_too_far` → `out_of_radius`

**StageReached:** seed data usa `"notification"` (valor real válido) en lugar de `"alerted"` (stub inválido)

---

## Tests pasando

```
tests/dashboard/test_routes.py — 24/24 PASSED (0.22s)
```

Sin fallos. Sin tests pendientes de campos de claude-1.

---

## Campos que se quitaron del dashboard (temporalmente)

Los siguientes campos del stub **no existen aún** en el modelo real `DecisionLog`. Fueron eliminados de templates y seed data. Volverán cuando claude-1 mergee `hotfix/model-fields`:

- `article_content_snippet`
- `within_radius`
- `is_duplicate`
- `total_tokens_input` / `total_tokens_output`
- `total_latency_ms`
- `telegram_sent`
- `error_stage`

El `HumanFeedback` real tampoco tiene `was_correct` ni `notes` (solo `should_have_been`). El formulario de feedback fue simplificado a solo el select de corrección. Si se requieren esos campos, deben añadirse al modelo real.

---

## Confirmación de eliminación de stubs

```
git rm src/dashboard/_model_stubs.py
→ delete mode 100644 src/dashboard/_model_stubs.py
```

El archivo ya no existe en la rama ni en el historial de la rama (sí en commits anteriores de `fase-a/dashboard`).

---

## Commit final

```
67b82e0  fix(dashboard): align with real DecisionLog model, remove stubs (Op C hotfix)
hotfix/dashboard-align → origin/hotfix/dashboard-align ✓ (pusheado)
```
