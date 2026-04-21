# OUTPUT_003 — Week 2: Token Logging + /api/incidents Endpoint

**Branch:** `week2/api-and-tokens`
**Date:** 2026-04-19
**Tasks:** T2.3 (endpoint) + token accumulation instrumentation

---

## Summary

Implemented Part A (token cost logging) and Part B (`GET /api/incidents` REST endpoint) for the Week 2 sprint.

---

## Part A — Token Logging

### New model fields (`src/models/decision_log.py`)

Added 3 nullable columns to `DecisionLog`:

| Column | Type | Purpose |
|--------|------|---------|
| `total_tokens_cache_read` | `Integer` | Prompt-cache read tokens across all LLM calls for the article |
| `total_tokens_cache_creation` | `Integer` | Prompt-cache creation tokens |
| `cost_estimated_usd` | `Float` | Blended cost estimate (input+cache_read+cache_creation+output) |

### `src/core/token_counter.py` — `TokenAccumulator`

Dataclass with 4 counters (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`).

- `add_response(response)` — reads `response.usage`, uses `getattr(..., 0)` for cache fields (absent on non-caching models)
- `cost_usd` property — formula: `input*1e-6 + cache_read*0.1e-6 + cache_creation*1.25e-6 + output*5e-6`

### Instrumentation

- `classifier.triage()` — accepts optional `accumulator: TokenAccumulator` kwarg; calls `accumulator.add_response(response)` after API call
- `classifier.deep_analyze()` — same pattern
- `geolocator.geolocate_incident()` — same pattern
- `scripts/run_pipeline.py` — creates `TokenAccumulator()` per article, passes to all 3 LLM calls, persists all 5 token fields + `cost_estimated_usd` in the final `FinalDecision.alerted` log call

### Alembic migration

`alembic/versions/0005_add_token_cache_and_cost_fields.py`

- `down_revision = "74b26b81cb14"` (end of previous chain)
- `batch_alter_table` for SQLite + PostgreSQL compatibility
- 3 `ADD COLUMN` operations, all nullable

---

## Part B — `GET /api/incidents`

### `src/dashboard/api.py`

Router prefix `/api`, registered in `src/dashboard/main.py`.

**Query parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `since` | `1h\|6h\|24h\|72h` | `24h` | Filters by `created_at >= now - N hours` |
| `severity_min` | int 0–10 | `0` | Lower bound on `severity_score` |
| `branch` | `carretera_nacional\|cumbres\|valle_oriente\|all` | `all` | Maps to `nearest_costco` exact match |
| `within_radius_only` | bool | `true` | Filters `within_radius = True` |
| `limit` | int 1–500 | `100` | Row cap, ordered by `created_at DESC` |

**Business rule:** only rows where `incident_type IS NOT NULL` (i.e., articles that reached deep_analysis stage).

**Response shape:**

```json
{
  "count": 2,
  "generated_at": "...",
  "filters_applied": {"since": "24h", ...},
  "incidents": [
    {
      "id": "42",
      "article_url": "...",
      "incident_type": "accident",
      "severity_score": 7,
      "nearest_costco": "Costco Carretera Nacional",
      "distance_km": 1.2,
      "within_radius": true,
      "cost_estimated_usd": 0.004,
      ...
    }
  ],
  "stats": {
    "avg_severity": 7.0,
    "by_branch": {"carretera_nacional": 1, "cumbres": 0, "valle_oriente": 1},
    "total_cost_usd": 0.008
  }
}
```

Stats are computed with SQL `AVG()`, `SUM()`, and per-branch `COUNT()` queries (not Python loops).

`distance_km` is derived server-side as `nearest_costco_dist_m / 1000`.

---

## Tests

`tests/dashboard/test_api_incidents.py` — **11 tests**, all passing.

| Test | What it verifies |
|------|-----------------|
| `test_returns_empty_when_no_incidents` | 200 + well-formed empty response |
| `test_returns_incident_with_all_fields` | All required fields present, `distance_km` correct |
| `test_excludes_null_incident_type` | Pre-triage rows not returned |
| `test_filters_by_severity_min` | Only rows >= severity_min |
| `test_filters_by_branch` | Branch → store name mapping correct |
| `test_within_radius_only_excludes_far_incidents` | Default filter works |
| `test_within_radius_only_false_includes_all` | Opt-out works |
| `test_limit_param_respected` | Row cap respected |
| `test_stats_avg_severity_computed` | avg_severity not null |
| `test_stats_by_branch_counts` | by_branch has correct keys and non-negative ints |
| `test_invalid_since_param_returns_422` | Validation rejects invalid enum |

Full suite (excluding pre-existing metrics failures): **176 tests passed**.

---

## Files Changed

| File | Change |
|------|--------|
| `src/models/decision_log.py` | +3 columns |
| `src/core/token_counter.py` | NEW — `TokenAccumulator` dataclass |
| `alembic/versions/0005_add_token_cache_and_cost_fields.py` | NEW — migration |
| `src/analyzer/classifier.py` | `triage()` + `deep_analyze()` accept `accumulator` kwarg |
| `src/analyzer/geolocator.py` | `geolocate_incident()` accepts `accumulator` kwarg |
| `scripts/run_pipeline.py` | Creates `TokenAccumulator` per article, passes + persists |
| `src/dashboard/api.py` | NEW — `GET /api/incidents` endpoint |
| `src/dashboard/main.py` | Register `api_router` |
| `tests/dashboard/test_api_incidents.py` | NEW — 11 tests |
