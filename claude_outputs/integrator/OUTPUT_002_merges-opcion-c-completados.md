# OUTPUT_002 — Merges Op C completados: 171/171 tests pasando

**Fecha:** 2026-04-19  
**Tarea:** Mergear 3 hotfixes de Op C + resolver conflictos post-merge  
**Estado:** Completo — suite verde, pusheado a origin

---

## Resumen de los 3 merges

### Merge 1 — `hotfix/model-fields` → `v2-rewrite`

**Commit de merge:** `3607497`  
**Sin conflictos.**

Archivos incorporados:
```
alembic/versions/0003_add_missing_decision_log_fields.py   (nuevo)
src/models/decision_log.py                                  (modificado — +8 campos)
tests/models/test_decision_log.py                           (modificado — +12 tests)
claude_outputs/claude-1/OUTPUT_001_hotfix-model-fields.md   (nuevo)
```

Tests post-merge: **34/34** (`tests/core/` + `tests/models/`)

---

### Merge 2 — `hotfix/metrics-align` → `v2-rewrite`

**Commit de merge:** `db445aa`  
**Sin conflictos.**

Archivos incorporados:
```
src/metrics/__init__.py       (modificado — +3 exports)
src/metrics/aggregators.py    (modificado — +3 aggregators: within_radius, duplicate_rate, alerts_sent)
tests/metrics/stubs.py        (modificado — alineado con modelo real + 8 campos)
tests/metrics/test_aggregators.py  (modificado — +6 tests para nuevos aggregators)
claude_outputs/claude-3/OUTPUT_001_hotfix-metrics-align.md  (nuevo)
```

Tests post-merge aislado: **29/29** (`tests/metrics/`)

---

### Merge 3 — `hotfix/dashboard-align` → `v2-rewrite`

**Commit de merge:** `3cbfedf`  
**Sin conflictos.**

Archivos incorporados:
```
src/dashboard/_model_stubs.py          (ELIMINADO — git rm)
src/dashboard/main.py                  (simplificado — try/except removido)
src/dashboard/routes.py                (simplificado — try/except removido, _decision_class actualizado)
src/dashboard/templates/detail.html    (actualizado — campos del modelo real)
src/dashboard/templates/index.html     (actualizado — campos del modelo real)
tests/dashboard/conftest.py            (actualizado — imports reales, seed data alineado)
tests/dashboard/test_routes.py         (actualizado — imports reales, test_save simplificado)
claude_outputs/claude-2/OUTPUT_001_hotfix-dashboard-align.md  (nuevo)
```

Tests post-merge aislado: **24/24** (`tests/dashboard/`)

---

## Problema encontrado post-merge 3 + fix aplicado

Al correr el suite completo apareció el `InvalidRequestError` predicho en `REPORTE_FASE_A.md`:

```
sqlalchemy.exc.InvalidRequestError: Table 'decision_log' is already defined
for this MetaData instance.
```

**Causa:** `tests/metrics/stubs.py` usaba `from src.core.database import Base` (el Base compartido). Al correr el suite completo, el dashboard/conftest ya había registrado el modelo real en ese Base; cuando metrics intentó registrar su stub en el mismo Base, SQLAlchemy colisionó.

**Fix aplicado (commit `9624f2b`):**

```python
# tests/metrics/stubs.py — antes
from src.core.database import Base

# después
class Base(DeclarativeBase):
    """Private base for metrics test stubs — isolated from src.core.database.Base."""
```

Y en los 3 test files de metrics, cambiar:
```python
# antes
from src.core.database import Base
from tests.metrics.stubs import DecisionLog, ...

# después
from tests.metrics.stubs import Base, DecisionLog, ...
```

---

## Test suite final

| Capa | Tests | Estado |
|------|------:|-------|
| `tests/core/` | 13 | ✅ |
| `tests/models/` | 21 | ✅ |
| `tests/scrapers/` | 33 | ✅ |
| `tests/analyzer/` | 43 | ✅ |
| `tests/notifier/` | 8 | ✅ |
| `tests/metrics/` | 29 | ✅ |
| `tests/dashboard/` | 24 | ✅ |
| **Total** | **171** | **✅ 0 failed** |

**Comparativa antes vs después de Op C:**

| Momento | Passed | Failed |
|---------|-------:|-------:|
| Pre-Op C (post Fase A merges) | 133 | 20 |
| Post-Op C | **171** | **0** |
| Delta | +38 | −20 |

---

## Árbol `src/` completo

```
src/
├── core/
│   ├── config.py
│   ├── database.py
│   ├── decision_logger.py
│   └── logger.py
├── models/
│   ├── alert.py
│   ├── analysis_result.py
│   ├── base.py
│   ├── decision_log.py        ← +8 campos Op C
│   ├── human_feedback.py
│   ├── incident.py
│   └── source.py
├── schemas/
│   ├── alert.py
│   ├── analysis_result.py
│   ├── incident.py
│   └── source.py
├── scrapers/
│   ├── _google_news_rss.py
│   ├── base.py
│   ├── bomberos_nl.py
│   ├── horizonte.py
│   ├── info7.py
│   ├── milenio.py
│   └── proteccion_civil.py
├── analyzer/
│   ├── classifier.py
│   ├── dedup.py
│   ├── geolocator.py
│   └── types.py
├── notifier/
│   └── telegram.py            ← dry_run=False añadido
├── dashboard/
│   ├── database.py
│   ├── main.py
│   ├── routes.py
│   ├── static/style.css
│   └── templates/
│       ├── base.html
│       ├── detail.html
│       ├── index.html
│       └── runs.html
└── metrics/
    ├── aggregators.py         ← +3 aggregators Op C
    ├── quality.py
    └── report.py
```

---

## Los 3 problemas conocidos de los workers — ¿se manifestaron?

### 1. `InvalidRequestError` en suite completo (claude-3 lo reportó como riesgo)
**Sí se manifestó.** Resuelto en commit `9624f2b` — `stubs.py` ahora usa `DeclarativeBase` privado.

### 2. Campos perdidos en templates del dashboard (claude-2 reportó como deuda)
**No se manifestó como error en tests.** Los templates fueron actualizados por claude-2 para usar los nombres del modelo real. Sin embargo, los templates pueden mostrar `None` en campos que el pipeline aún no popula (ej. `total_latency_ms`, `telegram_sent`). Esto es cosmético y se resolverá cuando `run_pipeline.py` empiece a llenar esos campos.

**Queda como deuda conocida:** verificar visualmente en el dashboard que todos los campos se muestren correctamente tras una corrida real del pipeline.

### 3. `HumanFeedback` simplificado sin `was_correct` (claude-2 reportó)
**No bloqueante.** El modelo real de `human_feedback.py` no tiene el campo `was_correct` que estaba en el spec de FASE_A.md. El dashboard guarda `should_have_been` y `notes` pero no el booleano explícito. El campo `was_correct` puede inferirse de si `should_have_been` es None o no.

**Queda como deuda:** si se quiere el campo explícito para métricas de precision/recall, claude-1 debe añadirlo en una futura migración.

---

## ¿Está listo `python scripts/run_pipeline.py`?

**Casi.** Necesita un `.env` con las variables requeridas por `Settings`:

```bash
# .env mínimo para correr en modo dry_run
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=bot...        # puede ser dummy si dry_run=True
TELEGRAM_CHAT_ID=-100...         # puede ser dummy si dry_run=True
DATABASE_URL=sqlite+aiosqlite:///./costco_motor.db
```

El script acepta `--dry-run` para no mandar alertas reales por Telegram.

También hay que correr las migraciones antes de la primera ejecución:
```bash
alembic upgrade head
```

**El código está listo. Solo falta configuración.**

---

## Total de commits en `v2-rewrite`

**93 commits** en la rama (incluyendo merges y hotfixes).

---

## Próximos pasos sugeridos

1. **Crear `.env`** con las 4 variables requeridas
2. **`alembic upgrade head`** — crea `costco_motor.db` con las 3 migraciones
3. **`python scripts/run_pipeline.py --dry-run`** — primera corrida completa
4. **`uvicorn src.dashboard.main:app --reload`** — revisar el dashboard con datos reales
5. **`python scripts/generate_report.py`** — generar `REPORTE_CALIDAD.md`
6. **Verificar visualmente** los campos `None` en el dashboard y decidir si pipeline necesita poblarlos
7. **Fase B:** refinamiento del classifier (ajuste de prompts, threshold de severidad, fuentes adicionales)
