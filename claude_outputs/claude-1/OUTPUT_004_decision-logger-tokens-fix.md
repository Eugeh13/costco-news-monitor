# OUTPUT_004 — Bug Fix: Token Persistence in decision_logger

**Branch:** `week2/decision-logger-tokens-fix`
**Date:** 2026-04-20
**Bug:** `total_tokens_input` (and all other token/cost columns) NULL on 28 classified records

---

## Root Cause

The `TokenAccumulator` was created and populated correctly inside `_process_article()` in `scripts/run_pipeline.py`, but the accumulated values were only spread into `log_processed_article()` at **one** of the 9 terminal exit paths — `FinalDecision.alerted`.

All other exit paths returned without persisting token data:

| Exit path | Final decision | Tokens before fix |
|-----------|---------------|-------------------|
| `is_duplicate` | `duplicate` | ❌ NULL |
| no `ANTHROPIC_API_KEY` | `pending` | ❌ NULL |
| triage failed | `irrelevant` | ❌ NULL |
| `deep_analyze` returned None | `error` | ❌ NULL |
| Nominatim geocode failed | `no_geo` | ❌ NULL |
| outside 3 km radius | `out_of_radius` | ❌ NULL (17 of 28 classified records) |
| below severity threshold | `irrelevant` | ❌ NULL |
| **alert sent** | **alerted** | ✅ populated |
| unhandled exception | `error` | ❌ NULL |

The 28 classified records (with `incident_type IS NOT NULL`) broke down as:
- `out_of_radius`: 17 — major path, all tokens accumulated through geolocator
- `alerted`: 4 — tokens were coded but these ran before the week2 PR was merged
- `no_geo`: 2
- `irrelevant` (below threshold): 2
- `duplicate`: 3

## Fix

### `scripts/run_pipeline.py`

Added a private helper above `_process_article()`:

```python
def _tok(acc: TokenAccumulator) -> dict:
    """Return token/cost fields for log_processed_article **kwargs spread."""
    return {
        "total_tokens_input": acc.input_tokens,
        "total_tokens_output": acc.output_tokens,
        "total_tokens_cache_read": acc.cache_read_tokens,
        "total_tokens_cache_creation": acc.cache_creation_tokens,
        "cost_estimated_usd": acc.cost_usd,
    }
```

Then added `**_tok(accumulator)` to **all 9** terminal `log_processed_article` calls:
- `FinalDecision.duplicate`
- `FinalDecision.pending` (no_api_key)
- `FinalDecision.irrelevant` (triage fail) — merged into the existing call that sets `triage_passed`
- `FinalDecision.error` (deep_analyze None)
- `FinalDecision.no_geo`
- `FinalDecision.out_of_radius`
- `FinalDecision.irrelevant` (below threshold)
- `FinalDecision.alerted` — replaced explicit fields with `**_tok(accumulator)` for consistency
- `FinalDecision.error` (exception handler)

**Design decision:** tokens are persisted on ALL paths including `duplicate` (0 tokens — shows dedup fired before any LLM call) and `no_api_key` (0 tokens — no API available). This gives full cost visibility across every article.

## Files Changed

| File | Change |
|------|--------|
| `scripts/run_pipeline.py` | Added `_tok()` helper; spread into all 9 terminal log calls |
| `tests/pipeline/__init__.py` | NEW — package init |
| `tests/pipeline/test_decision_logger_tokens.py` | NEW — 5 integration tests |

## DB Numbers

**Before fix** (query run at investigation time):
```
total=312  with_tokens=0  classified=28
```

**After fix** (post-validation run, 10 new records from pipeline run):
```
total=322  with_tokens=10  classified=28
```

Note: the 28 historical records remain NULL (pre-fix). New records from this and future runs have tokens populated on all paths.

## Sample Records (new, post-fix)

```
id  | final_decision | total_tokens_input | total_tokens_output | cost_estimated_usd
322 | irrelevant     | 2688               | 88                  | 0.003128
321 | irrelevant     | 2690               | 81                  | 0.003095
319 | duplicate      | 0                  | 0                   | 0.0
318 | duplicate      | 0                  | 0                   | 0.0
317 | irrelevant     | 2673               | 89                  | 0.003118
```

## Validation Run Cost

```sql
SELECT SUM(cost_estimated_usd) AS total_cost, COUNT(*) AS records
FROM decision_log
WHERE created_at > datetime('now', '-10 minutes');
-- → 0.0187 USD for 10 records (6 irrelevant triage, 4 duplicate — no deep_analyze calls)
```

## Test Results

```
tests/pipeline/test_decision_logger_tokens.py  5 passed
Full suite (--ignore=tests/metrics):          181 passed
```

Tests added:
1. `test_logger_persists_tokens_on_alerted_record` — alerted path stores all 5 fields
2. `test_logger_persists_tokens_on_classified_record` — out_of_radius with tokens (primary regression test)
3. `test_logger_persists_tokens_on_triage_failed_record` — irrelevant stores triage tokens
4. `test_cost_estimated_calculated_correctly` — formula: 1M input + 200k output + 500k cache_read + 100k cache_creation = $2.175
5. `test_cache_tokens_counted_separately` — cache_creation and cache_read tracked independently

## Commit

See git log for commit hash after push.
