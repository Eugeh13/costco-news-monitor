# src/metrics

Quality-reporting layer for costco-news-monitor v2.

## Modules

| Module | Purpose |
|--------|---------|
| `aggregators.py` | Async DB query functions — counts, latency, tokens, distributions |
| `quality.py` | Precision / recall / accuracy against HumanFeedback |
| `report.py` | `generate_markdown_report()` — assembles the full Markdown report |

## CLI

```bash
python scripts/generate_report.py                     # writes REPORTE_CALIDAD.md
python scripts/generate_report.py --output /tmp/r.md  # custom path
```

Exit codes: 0 success · 1 DB error · 2 unexpected error.

## Dependency on DecisionLog / HumanFeedback

`aggregators.py` and `quality.py` use raw SQL against `decision_logs` and `human_feedbacks`.
All queries are wrapped in `try/except` and return empty/zero defaults when the tables
don't exist yet (pre-merge of `fase-a/pipeline`).

Tests use local stubs in `tests/metrics/stubs.py` — do **not** import these stubs from `src/`.

---

## Ejemplo de output (datos ficticios realistas)

El siguiente es el Markdown exacto que genera `generate_markdown_report()` cuando el pipeline
lleva ~72 horas corriendo con datos reales de las tres sucursales.

```markdown
# Reporte de Calidad — 2026-04-19 09:15 UTC

## 1. Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Total incidentes procesados | 312 |
| Throughput (última 24 h) | 4.83 inc/h |
| Latencia promedio pipeline | 1 847 ms |
| Tokens totales consumidos | 2,341,580 |
| Precisión del clasificador | 91.2% |
| Recall del clasificador | 84.6% |

## 2. Distribución por Etapa del Pipeline

| Etapa | Count |
|-------|-------|
| alerted | 47 |
| analyzed | 18 |
| dismissed | 231 |
| pending_analysis | 16 |

## 3. Decisiones Finales

| Decisión | Count |
|----------|-------|
| dismissed | 231 |
| alert_sent | 47 |
| passed | 34 |

## 4. Calidad por Etapa

| Etapa | Accuracy |
|-------|----------|
| classification | 91.2% |
| geo | 97.4% |
| triage | 88.5% |

## 5. Distribución de Incidentes

### Por Fuente

| Fuente | Count |
|--------|-------|
| Twitter | 148 |
| GNews | 97 |
| RSS El Norte | 67 |

### Por Tipo

| Tipo | Count |
|------|-------|
| accidente_vial | 134 |
| seguridad | 79 |
| incendio | 41 |
| bloqueo | 33 |
| desastre_natural | 18 |
| otro | 7 |

### Por Severidad

| Severidad | Count |
|-----------|-------|
| critica | 12 |
| grave | 35 |
| moderada | 148 |
| menor | 117 |

## 6. Patrones de Error Más Frecuentes

| Predicho | Debería ser | Ocurrencias |
|----------|-------------|-------------|
| dismissed | alert_sent | 14 |
| alert_sent | dismissed | 8 |
| passed | alert_sent | 5 |

## 7. Consumo de Tokens

| Tipo | Tokens |
|------|--------|
| Prompt | 1,876,240 |
| Completion | 465,340 |
| **Total** | **2,341,580** |

*Generado automáticamente por costco-news-monitor v2*
```

### Notas de interpretación

- **Sección 3** y **Sección 4** muestran `*(tabla decision_logs aún no disponible)*` hasta que se mergee `fase-a/pipeline`.
- **Sección 6** muestra `*(sin datos de feedback aún)*` hasta que existan filas en `human_feedbacks`.
- La **latencia** incluye triage + clasificación + geo + dedup; ~1.8 s es normal con Haiku+Sonnet en cascada.
- El patrón de error más común (`dismissed → alert_sent`) indica falsos negativos en el triage — revisar umbral de severidad.
