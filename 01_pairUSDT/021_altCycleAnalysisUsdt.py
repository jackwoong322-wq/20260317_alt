"""
BTC cycle template analyzer for USDT pairs.

- Data source: Supabase ohlcv table
- Result tables: alt_cycle_data, alt_cycle_summary
- BTC cycle_number/cycle_name/peak_date templates are applied to every alt.
- Alt cycles are skipped when no exact OHLCV row exists on the BTC cycle start date.
- Alt close/high/low rates are normalized by that alt close on the BTC cycle start date.
"""

import pandas as pd
from datetime import datetime, timezone
import requests

from lib.common.config import SUPABASE_ANON_KEY, SUPABASE_URL


def make_cycle_name(peak_ts: int, is_current: bool = False) -> str:
    """Peak timestamp(ms)로부터 사이클 이름 생성 (예: Cycle 2017, Current Cycle 2025)"""
    year = datetime.fromtimestamp(peak_ts / 1000, tz=timezone.utc).year
    if is_current:
        return f"Current Cycle ({year})"
    return f"Cycle {year}"


ONE_DAY_MS = 86_400_000
ONE_YEAR_MS = int(365.25 * ONE_DAY_MS)
PEAK_CONFIRM_MS = int(365 * 1 * ONE_DAY_MS)  # 1년 동안 갱신 없어야 Peak 확정
NEXT_SEARCH_MS = 2 * ONE_YEAR_MS  # Peak 후 다음 탐색 시작: 2년 뒤
PEAK_DRAWDOWN_RATE = 0.50  # 고점 대비 50% 이상 하락해야 확정

SUPABASE_PAGE_SIZE = 1000


# ══════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════


def date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def ms_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y/%m/%d")


def slash_to_iso(date_str: str | None) -> str | None:
    if not date_str:
        return None
    return date_str.replace("/", "-")


def slash_to_timestamptz(date_str: str | None) -> str | None:
    if not date_str:
        return None
    return f"{date_str.replace('/', '-')}T00:00:00+00:00"


def get_supabase_headers() -> dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError(
            "SUPABASE_URL/SUPABASE_ANON_KEY가 설정되지 않았습니다."
        )
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }


def fetch_all_supabase(
    table: str, select_cols: str, extra_params: dict | None = None
) -> list[dict]:
    headers = get_supabase_headers()
    rows = []
    offset = 0

    while True:
        params = {"select": select_cols}
        if extra_params:
            params.update(extra_params)

        h = {
            **headers,
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + SUPABASE_PAGE_SIZE - 1}",
        }

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params=params,
            headers=h,
            timeout=60,
        )
        res.raise_for_status()

        batch = res.json()
        rows.extend(batch)

        if len(batch) < SUPABASE_PAGE_SIZE:
            break

        offset += SUPABASE_PAGE_SIZE

    return rows


def get_coins_supabase() -> list[tuple[str, str]]:
    rows = fetch_all_supabase("coins", "id,symbol", {"order": "rank.asc"})
    return [(r["id"], r["symbol"]) for r in rows]


# ══════════════════════════════════════════════════════
# OHLCV 로드 (Supabase)
# ══════════════════════════════════════════════════════


def load_ohlcv_supabase(coin_id: str, from_date: str | None = None) -> pd.DataFrame:
    """
    from_date: YYYY-MM-DD 형식. 지정 시 해당 날짜 이후 데이터만 로드.
    """
    extra = {
        "coin_id": f"eq.{coin_id}",
        "order": "date.asc",
    }
    if from_date:
        extra["date"] = f"gte.{from_date}"

    rows = fetch_all_supabase("ohlcv", "date,high,low,close", extra)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["timestamp"] = df["date"].apply(date_to_ms)
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════
# Peak 탐지
# ══════════════════════════════════════════════════════


def is_confirmed_peak(df: pd.DataFrame, pos: int) -> bool:
    peak_ts = df.iloc[pos]["timestamp"]
    peak_high = df.iloc[pos]["high"]

    after_df = df[df["timestamp"] > peak_ts]
    if after_df.empty:
        return False

    confirm_end_ts = peak_ts + PEAK_CONFIRM_MS
    within_1yr = after_df[after_df["timestamp"] <= confirm_end_ts]

    if within_1yr.empty:  # type: ignore[union-attr]
        return False

    # ① 1년 내 고점 갱신하면 가짜 Peak
    if within_1yr["high"].max() >= peak_high:
        return False

    # ② 3년 안에 50% 이상 하락
    within_3yr = after_df[after_df["timestamp"] <= peak_ts + 3 * ONE_YEAR_MS]
    drawdown_threshold = peak_high * (1 - PEAK_DRAWDOWN_RATE)
    if within_3yr["low"].min() > drawdown_threshold:
        return False

    return True


def find_all_peaks(df: pd.DataFrame, symbol: str = "") -> list[tuple]:
    """
    확정된 Peak 목록을 반환.
    symbol 인자는 디버그 로그 출력용.
    """
    if df.empty or len(df) < 365:
        return []

    peaks = []
    start_ts = df["timestamp"].min()
    end_ts = df["timestamp"].max()

    while start_ts < end_ts:
        search_df = df[df["timestamp"] >= start_ts]
        if search_df.empty:
            break

        peak_found = False
        for pos in search_df.index:
            if is_confirmed_peak(df, pos):
                peak_ts = int(df.iloc[pos]["timestamp"])
                peak_high = float(df.iloc[pos]["high"])
                peaks.append((peak_ts, peak_high))

                cycle_num = len(peaks)
                print(
                    f"    [Peak {cycle_num} 확정] {ms_to_date(peak_ts)}"
                    f"  @ {peak_high:>14,.4f}"
                    f"  (다음 탐색: {ms_to_date(peak_ts + NEXT_SEARCH_MS)}~)"
                )

                start_ts = peak_ts + NEXT_SEARCH_MS
                peak_found = True
                break

        if not peak_found:
            break

    return peaks


# ------------------------------------------------------
# BTC-template cycle calculation
# ------------------------------------------------------


def find_btc_coin_id(coins: list[tuple[str, str]]) -> str | None:
    for coin_id, symbol in coins:
        if str(symbol).upper() == "BTC":
            return coin_id
    return None


def build_btc_cycle_templates(btc_df: pd.DataFrame) -> list[dict]:
    peaks = find_all_peaks(btc_df, "BTC")
    if not peaks:
        return []

    last_peak_ts, _last_peak_high = peaks[-1]
    current_search_ts = last_peak_ts + NEXT_SEARCH_MS
    today_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    current_df = btc_df[
        (btc_df["timestamp"] >= current_search_ts)
        & (btc_df["timestamp"] <= today_ts)
    ]

    if not current_df.empty:
        current_peak_idx = current_df["high"].idxmax()  # type: ignore[union-attr]
        current_peak_ts = int(btc_df.loc[current_peak_idx, "timestamp"])
        current_peak_high = float(btc_df.loc[current_peak_idx, "high"])
        print(
            f"    [BTC Current Peak] {ms_to_date(current_peak_ts)}"
            f"  @ {current_peak_high:>14,.4f}"
        )
        peaks.append((current_peak_ts, current_peak_high))

    templates = []
    for idx, (peak_ts, peak_high) in enumerate(peaks):
        cycle_num = idx + 1
        next_peak_ts = peaks[idx + 1][0] if idx + 1 < len(peaks) else None
        is_current = next_peak_ts is None
        templates.append(
            {
                "cycle_number": cycle_num,
                "cycle_name": make_cycle_name(peak_ts, is_current=is_current),
                "peak_ts": int(peak_ts),
                "peak_date": ms_to_date(int(peak_ts)),
                "peak_high": float(peak_high),
                "next_peak_ts": int(next_peak_ts) if next_peak_ts else None,
                "is_current": is_current,
            }
        )
    return templates


def get_row_at_timestamp(df: pd.DataFrame, ts: int):
    rows = df[df["timestamp"] == ts]
    if rows.empty:
        return None
    return rows.iloc[0]


def _cycle_window_df(df: pd.DataFrame, template: dict) -> pd.DataFrame:
    peak_ts = int(template["peak_ts"])
    next_peak_ts = template.get("next_peak_ts")
    mask = df["timestamp"] >= peak_ts
    if next_peak_ts:
        mask &= df["timestamp"] < int(next_peak_ts)
    return df[mask].copy().reset_index(drop=True)


def calculate_cycle_by_btc_template(
    df: pd.DataFrame,
    template: dict,
) -> list[dict]:
    start_row = get_row_at_timestamp(df, int(template["peak_ts"]))
    if start_row is None:
        return []

    base_close = float(start_row["close"])
    if base_close <= 0:
        return []

    cycle_df = _cycle_window_df(df, template)
    if cycle_df.empty:
        return []

    peak_ts = int(template["peak_ts"])
    records = []
    for _, row in cycle_df.iterrows():
        row_ts = int(row["timestamp"])
        records.append(
            {
                "cycle_number": int(template["cycle_number"]),
                "cycle_name": str(template["cycle_name"]),
                "days_since_peak": int((row_ts - peak_ts) // ONE_DAY_MS),
                "timestamp": ms_to_date(row_ts),
                "close_price": row["close"],
                "low_price": row["low"],
                "high_price": row["high"],
                "close_rate": (row["close"] / base_close) * 100,
                "low_rate": (row["low"] / base_close) * 100,
                "high_rate": (row["high"] / base_close) * 100,
                "peak_date": template["peak_date"],
                "peak_price": base_close,
            }
        )
    return records


def build_summary_by_btc_templates(
    df: pd.DataFrame,
    templates: list[dict],
) -> list[dict]:
    summaries = []
    prev_summary = None

    for template in templates:
        start_row = get_row_at_timestamp(df, int(template["peak_ts"]))
        if start_row is None:
            continue

        base_close = float(start_row["close"])
        if base_close <= 0:
            continue

        cycle_df = _cycle_window_df(df, template)
        if cycle_df.empty:
            continue

        if template.get("is_current"):
            low_ts, low_price, low_pct_from_peak = None, None, None
        else:
            low_idx = cycle_df["low"].idxmin()  # type: ignore[union-attr]
            low_ts = int(cycle_df.loc[low_idx, "timestamp"])
            low_price = float(cycle_df.loc[low_idx, "low"])
            low_pct_from_peak = (
                ((low_price - base_close) / base_close) * 100
                if base_close > 0
                else None
            )

        if prev_summary and prev_summary.get("low_price"):
            prev_low_price = float(prev_summary["low_price"])
            peak_pct_from_low = (
                ((base_close - prev_low_price) / prev_low_price) * 100
                if prev_low_price > 0
                else None
            )
        else:
            peak_pct_from_low = None

        summary = {
            "cycle_number": int(template["cycle_number"]),
            "cycle_name": str(template["cycle_name"]),
            "peak_date": template["peak_date"],
            "peak_price": base_close,
            "peak_pct_from_low": (
                round(peak_pct_from_low, 2)
                if peak_pct_from_low is not None
                else None
            ),
            "low_date": ms_to_date(low_ts) if low_ts else None,
            "low_price": low_price,
            "low_pct_from_peak": (
                round(low_pct_from_peak, 2)
                if low_pct_from_peak is not None
                else None
            ),
            "prev_peak_date": (
                prev_summary["peak_date"] if prev_summary else None
            ),
            "prev_peak_price": (
                prev_summary["peak_price"] if prev_summary else None
            ),
            "prev_low_date": (
                prev_summary["low_date"] if prev_summary else None
            ),
            "prev_low_price": (
                prev_summary["low_price"] if prev_summary else None
            ),
        }
        summaries.append(summary)
        prev_summary = summary

    return summaries


def delete_by_coin_supabase(table: str, coin_id: str):
    headers = {**get_supabase_headers(), "Prefer": "return=minimal"}
    res = requests.delete(
        f"{SUPABASE_URL}/rest/v1/{table}",
        params={"coin_id": f"eq.{coin_id}"},
        headers=headers,
        timeout=60,
    )
    res.raise_for_status()


def post_rows_supabase(table: str, rows: list[dict]):
    headers = {
        **get_supabase_headers(),
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    for i in range(0, len(rows), SUPABASE_PAGE_SIZE):
        chunk = rows[i : i + SUPABASE_PAGE_SIZE]
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            json=chunk,
            timeout=60,
        )
        res.raise_for_status()


def save_cycle_data_supabase(coin_id: str, records: list[dict]) -> int:
    delete_by_coin_supabase("alt_cycle_data", coin_id)
    if not records:
        return 0

    payload = []
    for r in records:
        payload.append(
            {
                "coin_id": coin_id,
                "cycle_number": r["cycle_number"],
                "cycle_name": r["cycle_name"],
                "days_since_peak": r["days_since_peak"],
                "timestamp": slash_to_timestamptz(r["timestamp"]),
                "close_price": r["close_price"],
                "low_price": r["low_price"],
                "high_price": r["high_price"],
                "close_rate": r["close_rate"],
                "low_rate": r["low_rate"],
                "high_rate": r["high_rate"],
                "peak_date": slash_to_iso(r["peak_date"]),
                "peak_price": r["peak_price"],
            }
        )

    post_rows_supabase("alt_cycle_data", payload)
    return len(payload)


def save_summary_supabase(coin_id: str, summaries: list[dict]) -> int:
    delete_by_coin_supabase("alt_cycle_summary", coin_id)
    if not summaries:
        return 0

    payload = []
    for s in summaries:
        payload.append(
            {
                "coin_id": coin_id,
                "cycle_number": s["cycle_number"],
                "cycle_name": s["cycle_name"],
                "peak_date": slash_to_iso(s["peak_date"]),
                "peak_price": s["peak_price"],
                "peak_pct_from_low": s["peak_pct_from_low"],
                "low_date": slash_to_iso(s["low_date"]),
                "low_price": s["low_price"],
                "low_pct_from_peak": s["low_pct_from_peak"],
                "prev_peak_date": slash_to_iso(s["prev_peak_date"]),
                "prev_peak_price": s["prev_peak_price"],
                "prev_low_date": slash_to_iso(s["prev_low_date"]),
                "prev_low_price": s["prev_low_price"],
            }
        )

    post_rows_supabase("alt_cycle_summary", payload)
    return len(payload)


def date_diff_days(date_from: str, date_to: str) -> int:
    """YYYY/MM/DD 형식 두 날짜 간 일수 차이"""
    fmt = "%Y/%m/%d"
    d1 = datetime.strptime(date_from, fmt)
    d2 = datetime.strptime(date_to, fmt)
    return abs((d2 - d1).days)


def print_coin_result(summaries: list[dict]):
    for s in summaries:
        # Peak 라인
        if s["peak_pct_from_low"] is not None and s["prev_low_date"]:
            days = date_diff_days(s["prev_low_date"], s["peak_date"])
            peak_str = (
                f"  Peak : {s['peak_date']} @ {s['peak_price']:>14,.4f} USDT"
                f"  (+{s['peak_pct_from_low']:.1f}% from prev low in {days}d)"
            )
        else:
            peak_str = f"  Peak : {s['peak_date']} @ {s['peak_price']:>14,.4f} USDT"
        print(peak_str)

        # Low 라인
        if s["low_date"]:
            if s["low_pct_from_peak"] is not None:
                days = date_diff_days(s["peak_date"], s["low_date"])
                low_str = (
                    f"   Low : {s['low_date']} @ {s['low_price']:>14,.4f} USDT"
                    f"  ({s['low_pct_from_peak']:.1f}% from prev peak in {days}d)"
                )
            else:
                low_str = f"   Low : {s['low_date']} @ {s['low_price']:>14,.4f} USDT"
            print(low_str)


# ══════════════════════════════════════════════════════
# 요약 출력 (Supabase)
# ══════════════════════════════════════════════════════


def print_summary_supabase():
    rows = fetch_all_supabase("alt_cycle_data", "coin_id,cycle_number,timestamp")
    if not rows:
        print("\n요약 데이터 없음")
        return

    df = pd.DataFrame(rows)
    summary = (
        df.groupby("coin_id")
        .agg(
            cycles=("cycle_number", "nunique"),
            earliest=("timestamp", "min"),
            latest=("timestamp", "max"),
            total_rows=("timestamp", "count"),
        )
        .reset_index()
        .sort_values("coin_id")
    )

    print(f"\n{'코인':<20} {'사이클':>6} {'시작':>12} {'끝':>12} {'총행수':>8}")
    print("-" * 65)
    for _, r in summary.iterrows():
        earliest = str(r["earliest"])[:10].replace("-", "/")
        latest = str(r["latest"])[:10].replace("-", "/")
        print(
            f"{r['coin_id']:<20} {int(r['cycles']):>6} {earliest:>12} {latest:>12} {int(r['total_rows']):>8}"
        )


# ══════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("BTC-template cycle analysis start (USDT pairs)")
    print("  DB MODE    : supabase")
    print("  Cycle basis: BTC peak-date template")
    print("  Alt base   : close on exact BTC cycle start date")
    print("  Incremental: disabled, full recalculation")
    print("=" * 60)

    coins = get_coins_supabase()
    if not coins:
        print("[ERROR] coins table is empty. Run collector first.")
        return

    btc_coin_id = find_btc_coin_id(coins)
    if not btc_coin_id:
        print("[ERROR] BTC coin not found in coins table.")
        return

    print(f"[BTC] Loading OHLCV for template source: {btc_coin_id}")
    btc_df = load_ohlcv_supabase(btc_coin_id)
    if btc_df.empty or len(btc_df) < 365:
        print(f"[ERROR] BTC data is insufficient ({len(btc_df)} rows).")
        return

    print(
        f"[BTC] Data {len(btc_df)} rows "
        f"({btc_df['date'].iloc[0]} ~ {btc_df['date'].iloc[-1]})"
    )
    btc_templates = build_btc_cycle_templates(btc_df)
    if not btc_templates:
        print("[ERROR] BTC cycle templates could not be built.")
        return

    print("[BTC] Cycle templates:")
    for template in btc_templates:
        end_label = (
            ms_to_date(template["next_peak_ts"])
            if template.get("next_peak_ts")
            else "latest"
        )
        print(
            f"  Cy{template['cycle_number']:>2} "
            f"{template['cycle_name']:<22} "
            f"{template['peak_date']} ~ {end_label}"
        )

    print(f"\nTotal {len(coins)} coins to process\n")
    success, skipped, no_cycle = 0, 0, 0

    for i, (coin_id, symbol) in enumerate(coins, 1):
        print(f"[{i}/{len(coins)}] {symbol} ({coin_id})")

        df = load_ohlcv_supabase(coin_id)
        if df.empty:
            print("  - no OHLCV rows, skipped\n")
            skipped += 1
            continue

        print(f"  Data {len(df)} rows ({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")
        all_records = []
        skipped_cycles = 0

        for template in btc_templates:
            records = calculate_cycle_by_btc_template(df, template)
            if not records:
                skipped_cycles += 1
                continue
            all_records.extend(records)

        summaries = build_summary_by_btc_templates(df, btc_templates)
        if not all_records or not summaries:
            print(
                "  - no BTC-template cycles generated "
                f"(skipped cycles={skipped_cycles}), skipped\n"
            )
            no_cycle += 1
            continue

        print_coin_result(summaries)
        print(
            f"  -> {len(summaries)} cycles, {len(all_records)} rows saved "
            f"(skipped cycles={skipped_cycles})\n"
        )

        save_cycle_data_supabase(coin_id, all_records)
        save_summary_supabase(coin_id, summaries)
        success += 1

    print("=" * 60)
    print(
        f"Done: success {success} / no cycle {no_cycle} / "
        f"no data {skipped}"
    )
    print("=" * 60)

    print_summary_supabase()


if __name__ == "__main__":
    main()
