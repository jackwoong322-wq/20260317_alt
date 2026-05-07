# BTC Cycle Template Based Alt Cycle Analysis Specification

## Goal

Change `01_pairUSDT/021_altCycleAnalysisUsdt.py` so altcoin cycle analysis uses BTC cycle windows instead of each altcoin's own detected peaks.

All altcoins should share BTC's `cycle_number`, `cycle_name`, and `peak_date`. Altcoin price rates should be normalized from the altcoin close price on the BTC cycle start date.

## Core Policy

- BTC keeps the existing peak detection logic.
- BTC analysis produces the shared cycle template.
- Altcoins do not run their own peak detection.
- Each altcoin is mapped into BTC cycle windows.
- If an altcoin has no OHLCV row on the BTC cycle start date, that altcoin cycle is skipped.
- Existing Supabase table names and column names stay unchanged.
- Initial implementation should prefer full recalculation over incremental update.

## BTC Cycle Template

BTC cycle templates are built from BTC OHLCV and existing BTC peak detection.

```python
{
    "cycle_number": 1,
    "cycle_name": "Cycle 2017",
    "peak_ts": 1513468800000,
    "peak_date": "2017/12/17",
    "next_peak_ts": 1636502400000,
    "is_current": False,
}
```

For the final/current cycle:

```python
{
    "cycle_number": 5,
    "cycle_name": "Current Cycle (2025)",
    "peak_ts": 1730000000000,
    "peak_date": "2025/../..",
    "next_peak_ts": None,
    "is_current": True,
}
```

All template dates are UTC dates. Matching an altcoin to a BTC cycle start date requires an exact `YYYY-MM-DD` date match between BTC `peak_date` and the altcoin OHLCV `date`. Do not substitute the nearest previous or next altcoin date.

## Alt Cycle Data Rules

For each altcoin and each BTC cycle template:

1. Find the altcoin OHLCV row whose `timestamp == btc_cycle.peak_ts`.
2. If that row does not exist, skip that cycle for that altcoin.
3. Use that row's `close` as `base_close`.
4. Select altcoin OHLCV rows where:
   - historical cycle: `btc_cycle.peak_ts <= timestamp < btc_cycle.next_peak_ts`
   - current cycle: `timestamp >= btc_cycle.peak_ts`
5. For every selected row:
   - `days_since_peak = (row.timestamp - btc_cycle.peak_ts) // ONE_DAY_MS`
   - `close_rate = row.close / base_close * 100`
   - `high_rate = row.high / base_close * 100`
   - `low_rate = row.low / base_close * 100`

## `alt_cycle_data` Meaning

Column names stay the same, but several meanings become BTC-cycle based.

| Column | Meaning |
|---|---|
| `coin_id` | Altcoin id |
| `cycle_number` | BTC cycle number |
| `cycle_name` | BTC cycle name |
| `days_since_peak` | Days since BTC cycle `peak_date` |
| `timestamp` | Altcoin OHLCV date |
| `close_price` | Altcoin actual close |
| `low_price` | Altcoin actual low |
| `high_price` | Altcoin actual high |
| `close_rate` | Altcoin close vs `base_close` |
| `low_rate` | Altcoin low vs `base_close` |
| `high_rate` | Altcoin high vs `base_close` |
| `peak_date` | BTC cycle peak date |
| `peak_price` | Altcoin `base_close` on BTC cycle peak date |

Important: `peak_price` no longer means the altcoin's own peak price. It means the altcoin close price on the BTC cycle start date.

For BTC itself, the same template path should be used. Because the normalization base is the BTC peak-day `close`, BTC day-0 `close_rate` should be `100`, but day-0 `high_rate` can be above `100` when the peak-day high is above the peak-day close.

## `alt_cycle_summary` Meaning

Summary rows should also use BTC cycle windows.

| Column | Meaning |
|---|---|
| `cycle_number` | BTC cycle number |
| `cycle_name` | BTC cycle name |
| `peak_date` | BTC cycle peak date |
| `peak_price` | Altcoin `base_close` on BTC cycle peak date |
| `peak_pct_from_low` | `(base_close - prev_low_price) / prev_low_price * 100` when previous low exists |
| `low_date` | Lowest altcoin low date inside the BTC cycle window |
| `low_price` | Lowest altcoin low inside the BTC cycle window |
| `low_pct_from_peak` | `(low_price - base_close) / base_close * 100` |
| `prev_peak_date` | Previous BTC cycle peak date |
| `prev_peak_price` | Previous cycle altcoin `base_close` |
| `prev_low_date` | Previous BTC cycle window's altcoin low date |
| `prev_low_price` | Previous BTC cycle window's altcoin low |

For current cycle compatibility, keep `low_date`, `low_price`, and `low_pct_from_peak` as `None` if preserving the old "current cycle has no final low yet" behavior is preferred.

## Required Code Changes

### `main()`

Current behavior:

- Iterates every coin.
- Runs incremental update first.
- If needed, loads that coin's OHLCV.
- Finds that coin's own peaks.
- Calculates cycles from that coin's own peaks.

New behavior:

1. Load all coins.
2. Find BTC coin id.
3. Load BTC OHLCV.
4. Run existing BTC peak detection.
5. Add BTC current cycle as currently done.
6. Build BTC cycle templates.
7. Iterate every coin.
8. Load coin OHLCV.
9. Apply BTC cycle templates.
10. Save `alt_cycle_data` and `alt_cycle_summary`.

### `calculate_cycle()`

Current behavior:

- Uses each coin's `peak_ts` and `peak_high`.
- `days_since_peak` is row index inside the sliced cycle.

New recommended replacement:

```python
def calculate_cycle_by_btc_template(
    df: pd.DataFrame,
    template: dict,
) -> list[dict]:
    ...
```

This function should:

- Require an exact altcoin row on `template["peak_ts"]`.
- Use that row's close as `base_close`.
- Compute `days_since_peak` from actual timestamp difference.
- Store BTC `peak_date` and altcoin `base_close`.

### `build_summary()`

Current behavior:

- Uses each coin's own peak list.
- Finds lows between that coin's own peaks.

New recommended replacement:

```python
def build_summary_by_btc_templates(
    df: pd.DataFrame,
    templates: list[dict],
) -> list[dict]:
    ...
```

This function should:

- Skip templates that do not have an exact altcoin start-date row.
- Compute lows inside BTC cycle windows.
- Use previous BTC-template summary for previous low/peak fields.

### `process_incremental()`

Current behavior:

- Uses `low_date IS NULL` current cycle for each coin.
- Re-detects current peak from that coin's own OHLCV.

New policy:

- Do not use the existing incremental update in the first BTC-template implementation.
- It is based on altcoin-specific peak detection and can mix old and new semantics.
- First implementation should run full recalculation for consistency.
- BTC-template incremental update can be implemented later as a separate change.

## Suggested New Helpers

```python
def find_btc_coin_id(coins: list[tuple[str, str]]) -> str | None:
    ...
```

```python
def build_btc_cycle_templates(btc_df: pd.DataFrame) -> list[dict]:
    ...
```

```python
def get_row_at_timestamp(df: pd.DataFrame, ts: int) -> pd.Series | None:
    ...
```

```python
def calculate_cycle_by_btc_template(
    df: pd.DataFrame,
    template: dict,
) -> list[dict]:
    ...
```

```python
def build_summary_by_btc_templates(
    df: pd.DataFrame,
    templates: list[dict],
) -> list[dict]:
    ...
```

## Skip Rules

- If BTC coin id cannot be found, stop the whole script.
- If BTC OHLCV is empty or shorter than the minimum required history, stop the whole script.
- If BTC peaks cannot be detected, stop the whole script.
- If an altcoin has no OHLCV, skip that coin.
- If an altcoin has no row exactly on a BTC cycle start date, skip that cycle only.
- If an altcoin produces no cycles, skip saving for that coin.

## Downstream Impact

### `031_box_analyzer_to_supabase.py`

Expected to keep working because table and column names stay the same.

Important semantic change:

- `peak_price` now means altcoin base close on BTC cycle peak date.
- Box analysis should be interpreted as BTC-cycle-relative altcoin movement.
- The existing BULL correction uses `next_peak / this_peak * 100`.
  After this change, that correction means "next BTC-cycle base close divided by this BTC-cycle base close", not "next altcoin peak divided by this altcoin peak".

### `032_train_and_predict_box.py`

Expected to keep working structurally because it reads the same tables and columns.

Training distribution will change because:

- All altcoins share BTC cycle numbers.
- `days_since_peak` becomes BTC-cycle aligned.
- Rates become altcoin performance from BTC cycle start.

### `033_visualizer_html.py`

Expected to keep working structurally.

Visualizer comparison should improve because:

- Cycles line up across BTC and alts.
- `x = days_since_peak` means the same BTC-relative day for every coin.

## Verification Checklist

- BTC produces templates with expected cycle count.
- BTC itself can be saved using the same template logic.
- Every altcoin `cycle_number` is a subset of BTC template cycle numbers.
- Every altcoin `cycle_name` matches BTC template names.
- For each saved altcoin cycle:
  - First row has `days_since_peak == 0`.
  - First row has `close_rate == 100`.
  - First row `timestamp` equals BTC `peak_date`.
- A cycle is skipped when the altcoin has no exact OHLCV row on BTC `peak_date`.
- Supabase unique key `coin_id, cycle_number, days_since_peak` does not conflict.
- `031_box_analyzer_to_supabase.py` can read the regenerated data.
- `032_train_and_predict_box.py` can train/predict from the regenerated data.
- `033_visualizer_html.py` shows cycles aligned by BTC day index.

## Required Rebuild Order

After changing the cycle basis, downstream derived tables must be regenerated in order:

```text
021_altCycleAnalysisUsdt.py
031_box_analyzer_to_supabase.py
032_train_and_predict_box.py
033_visualizer_html.py
```

If `021_altCycleAnalysisUsdt.py` fails midway, `alt_cycle_data` and `alt_cycle_summary` may contain a mixture of old per-alt peak semantics and new BTC-template semantics across different coins. In that case, rerun `021_altCycleAnalysisUsdt.py` successfully before running `031`, `032`, or `033`.

## Open Decisions

1. Current cycle summary low handling:
   - Option A: keep old behavior and store `low_date=None`.
   - Option B: store current-to-date low for current cycle.
   - Recommended: Option A for compatibility.

2. BTC itself:
   - Option A: process BTC through the same BTC-template path.
   - Option B: preserve existing BTC self-peak behavior.
   - Recommended: Option A, so BTC and alts share identical semantics.

3. Incremental update:
   - Option A: disable first and full-recalculate every run.
   - Option B: implement BTC-template incremental update now.
   - Recommended: Option A for the first implementation.
