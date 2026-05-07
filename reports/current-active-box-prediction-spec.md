# Current Active Box Prediction Specification

## Goal

Change the 031/032 prediction flow so prediction starts from the current active box itself.

The current box is not confirmed yet. Therefore the first prediction target must be the final state of the current active box, not the next box after it.

## Background

After `021_altCycleAnalysisUsdt.py` was changed to BTC cycle templates, `031_box_analyzer_to_supabase.py` marks the last box in the BTC `Current Cycle` as active:

- `is_prediction = 0`
- `is_completed = 0`
- `result = "ACTIVE"`

This active row represents observed/provisional data only. It should remain untouched. The predicted completion of that same box should be written as a separate prediction row.

## Current Problem

The current predictor flow still behaves as if the active box is already handled.

### Problem 1: Active Box Is Skipped

In `01_pairUSDT/lib/predictor/predict.py`, `predict_outputs()` currently prefers the last completed box when both completed and active boxes exist.

Current behavior:

```python
if not active.empty and not completed.empty:
    last = completed.iloc[-1]
elif not active.empty:
    last = active.iloc[-1]
else:
    last = grp.iloc[-1]
```

This makes prediction start after the previous completed box instead of from the current active box.

Required behavior:

```python
if not active.empty:
    last = active.iloc[-1]
else:
    last = grp.iloc[-1]
```

### Problem 2: Prediction Always Starts at the Next Box

In `_predict_one_coin_phase1()`, prediction anchor values are currently next-box based:

```python
start_x = int(last["end_x"]) + 1
next_box_idx = int(grp[grp["is_prediction"] == 0]["box_index"].max()) + 1
```

If `last` is the active box, this still jumps to the next box. That is not the desired behavior.

### Problem 3: Real Active Row May Be Mutated

`_predict_one_coin_phase2()` contains logic that updates the real active row:

- changes `result`
- may update `lo`
- may update `lo_day`

The observed row should not be overwritten by prediction logic. Predictions should be inserted as `is_prediction = 1` rows.

### Problem 4: Training Pair Can Use Active Box as Label

In `01_pairUSDT/lib/predictor/data.py`, `build_training_pairs()` skips incomplete rows only when the incomplete row is the input/current row:

```python
if curr["is_completed"] != 1:
    continue
```

But `nxt` can still be active. That leaks an unconfirmed box into the training label.

Required rule:

```python
if curr["is_completed"] != 1 or nxt["is_completed"] != 1:
    continue
```

## Required Data Semantics

### Observed Active Box

The real active row remains observed data.

| Column | Value |
|---|---|
| `is_prediction` | `0` |
| `is_completed` | `0` |
| `box_index` | current active box index |
| `result` | `ACTIVE` |
| `start_x` | observed active box start |
| `end_x` | latest observed active box end |
| `hi`, `lo`, `hi_day`, `lo_day` | observed/provisional values |

Do not overwrite this row during prediction.

### Predicted Active Box Completion

The predicted completion of the active box is stored separately.

| Column | Value |
|---|---|
| `is_prediction` | `1` |
| `is_completed` | `0` |
| `box_index` | same as active box index |
| `result` | `PRED_BEAR_ACTIVE` or `PRED_BULL_ACTIVE` |
| `start_x` | active box `start_x` |
| `end_x` | predicted final end day |
| `hi`, `lo` | predicted final box high/low |
| `hi_day`, `lo_day` | predicted final high/low days |
| `duration` | `end_x - start_x + 1` |

### Future Predicted Boxes

Future boxes continue after the active box.

| Row Type | `box_index` |
|---|---|
| predicted active-final row | `N` |
| first future predicted row | `N + 1` |
| second future predicted row | `N + 2` |

Existing future result labels can remain:

- `PRED_BEAR_CHAIN`
- `PRED_BULL_CHAIN`

## Required Implementation Changes

## 1. Add Active-Aware Prediction Anchor

File:

`01_pairUSDT/lib/predictor/predict.py`

Add a helper:

```python
def _resolve_prediction_anchor(grp: pd.DataFrame, last: pd.Series) -> dict:
    has_active_box = int(last.get("is_completed", 1)) == 0
    real_rows = grp[grp["is_prediction"] == 0]

    if has_active_box:
        return {
            "has_active_box": True,
            "prediction_box_idx": int(last["box_index"]),
            "prediction_start_x": int(last["start_x"]),
        }

    return {
        "has_active_box": False,
        "prediction_box_idx": int(real_rows["box_index"].max()) + 1,
        "prediction_start_x": int(last["end_x"]) + 1,
    }
```

Use this helper in `_predict_one_coin_phase1()`.

## 2. Select Active Box as `last`

File:

`01_pairUSDT/lib/predictor/predict.py`

In `predict_outputs()`, change selection to:

```python
active = grp[grp["is_completed"] == 0]
if not active.empty:
    last = active.iloc[-1]
else:
    last = grp.iloc[-1]
```

## 3. Preserve Observed Active Row

File:

`01_pairUSDT/lib/predictor/predict.py`

Remove or gate the active-row update block in `_predict_one_coin_phase2()`.

Do not execute SQL updates against:

```sql
WHERE coin_id = ? AND cycle_number = ? AND is_completed = 0 AND is_prediction = 0
```

Prediction output must be represented by inserted `is_prediction = 1` rows only.

## 4. Predict Active Box With Same Box Index

File:

`01_pairUSDT/lib/predictor/predict.py`

When `has_active_box = True`:

- `next_box_idx` means "prediction target box index", not "next after observed"
- first prediction row uses the active box index
- first prediction row start is active `start_x`

The path should include the predicted active box range:

```text
start_x = active.start_x
end_x   = predicted final end
```

The path may start from an observed point inside the active box for visual continuity, but the prediction row itself must keep the active box `start_x`.

## 5. Active Result Labels

Files:

- `01_pairUSDT/lib/predictor/predict.py`
- `01_pairUSDT/lib/predictor/predict_box_bear.py`
- `01_pairUSDT/lib/predictor/predict_box_bull.py`

For the first predicted row when `has_active_box = True`:

- Bear scenario: `result = "PRED_BEAR_ACTIVE"`
- Bull scenario: `result = "PRED_BULL_ACTIVE"`

Future rows remain:

- `PRED_BEAR_CHAIN`
- `PRED_BULL_CHAIN`

## 6. Fix Bear Single-Row Off-By-One

File:

`01_pairUSDT/lib/predictor/predict_box_bear.py`

`_make_bear_row_single()` currently stores:

```python
next_box_idx + 1
```

This should be changed to:

```python
next_box_idx
```

Debug output should also print the provided index directly.

## 7. Prevent Active Label Leakage in Training

File:

`01_pairUSDT/lib/predictor/data.py`

In `build_training_pairs()`, skip pairs where either side is incomplete:

```python
if curr["is_completed"] != 1 or nxt["is_completed"] != 1:
    continue
```

This keeps active/unconfirmed boxes out of model labels.

## 8. Preserve Completed Historical Boxes

File:

`01_pairUSDT/031_box_analyzer_to_supabase.py`

No major direction change is required here.

The current logic is correct in principle:

- completed boxes in the current cycle stay completed
- only the last current-cycle box becomes active

That active row is the prediction target in `032`.

## Prediction Path Rules

When active box exists:

1. The first prediction path belongs to the active box index.
2. The first prediction row has `start_x = active.start_x`.
3. The path should not start from the previous completed box's `end_x + 1`.
4. The path may include an observed anchor point such as:
   - active `lo_day`, `lo`
   - active `hi_day`, `hi`
   - active `end_x`, latest observed value if available
5. Future path rows continue from the predicted active box endpoint.

## Example

Observed rows:

| box_index | result | is_prediction | is_completed | start_x | end_x |
|---:|---|---:|---:|---:|---:|
| 0 | `DOWN` | 0 | 1 | 4 | 38 |
| 1 | `ACTIVE` | 0 | 0 | 39 | 120 |

Predicted rows should be:

| box_index | result | is_prediction | is_completed | start_x | end_x |
|---:|---|---:|---:|---:|---:|
| 1 | `PRED_BEAR_ACTIVE` | 1 | 0 | 39 | predicted |
| 2 | `PRED_BEAR_CHAIN` | 1 | 0 | predicted + 1 | predicted |
| 3 | `PRED_BULL_CHAIN` | 1 | 0 | predicted + 1 | predicted |

The predicted active row intentionally shares `box_index = 1` with the observed active row. They are distinguished by `is_prediction`.

## Test Plan

Add or update tests under:

- `unit_tests/01_pairUSDT/lib/predictor/test_predict.py`
- `unit_tests/01_pairUSDT/lib/predictor/test_predict_cycle_box_count.py`
- optionally `unit_tests/01_pairUSDT/lib/predictor/test_predict_active_box.py`

Required tests:

1. `predict_outputs()` uses active box as `last` when active exists.
2. `_predict_one_coin_phase1()` returns:
   - `has_active_box = True`
   - `next_box_idx = active.box_index`
   - `start_x = active.start_x`
3. No-active behavior remains unchanged:
   - `next_box_idx = max_box_index + 1`
   - `start_x = last.end_x + 1`
4. Active observed row is not updated in phase2.
5. Active bear prediction row:
   - uses same `box_index` as active
   - uses `result = "PRED_BEAR_ACTIVE"`
   - uses `start_x = active.start_x`
6. Active bull prediction row:
   - uses same `box_index` as active
   - uses `result = "PRED_BULL_ACTIVE"`
   - uses `start_x = active.start_x`
7. Future predicted rows continue at `active.box_index + 1`.
8. Training pairs exclude active rows as both input and label.
9. `build_bear_scenario(..., next_box_idx=N)` stores `box_index = N`, not `N + 1`.
10. Prediction path for active box does not start from previous completed `end_x + 1`.

## Implementation Priority

1. Change `predict_outputs()` to choose active box first.
2. Add `_resolve_prediction_anchor()`.
3. Use active anchor in `_predict_one_coin_phase1()`.
4. Stop mutating observed active rows in `_predict_one_coin_phase2()`.
5. Fix bear off-by-one.
6. Add training-pair guard for `nxt.is_completed`.
7. Add regression tests.
8. Run:

```powershell
python -m py_compile 01_pairUSDT/032_train_and_predict_box.py 01_pairUSDT/lib/predictor/data.py 01_pairUSDT/lib/predictor/predict.py 01_pairUSDT/lib/predictor/predict_box_bear.py 01_pairUSDT/lib/predictor/predict_box_bull.py
python -m pytest unit_tests/01_pairUSDT/test_032_train_and_predict_box.py unit_tests/01_pairUSDT/lib/predictor/test_predict.py unit_tests/01_pairUSDT/lib/predictor/test_predict_cycle_box_count.py
```

## Non-Goals

- Do not change `021_altCycleAnalysisUsdt.py` for this feature.
- Do not change Supabase table names or column names.
- Do not overwrite observed active rows with predicted values.
- Do not start prediction from the next box when an active box exists.

