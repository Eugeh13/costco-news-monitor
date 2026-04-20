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
