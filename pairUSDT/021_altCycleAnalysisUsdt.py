"""
알트코인 4년 주기 사이클 분석기 (USDT 페어)

- 데이터 소스: Supabase (ohlcv 테이블, USDT 페어)
- 결과 저장:
    alt_cycle_data    : 일별 OHLCV (기존)
    alt_cycle_summary : 코인별 사이클 Peak/Low 요약 (신규)

Peak 확정 로직:
  1. 전체 데이터 시작점부터 날짜 순으로 순회
  2. 각 날짜에 대해 Peak 조건 체크:
     ① 이후 1년 동안 고점 갱신 없음
     ② 이후 3년 안에 50% 이상 하락한 시점 존재
  3. 조건 만족하는 첫 날짜 = Peak 확정
  4. 다음 탐색은 Peak 이후 3년 뒤부터
  5. 반복

alt_cycle_summary 구조:
  peak_date / peak_price
  peak_pct_from_low  : 직전 저점 대비 +%  (from prev low)
  low_date  / low_price : 이 Peak ~ 다음 Peak 사이 최저점 (current cycle은 미설정)
  low_pct_from_peak  : 직전 고점 대비 -%  (from prev peak)
  prev_peak_date / prev_peak_price
  prev_low_date  / prev_low_price
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
            "DB_MODE=supabase 이지만 SUPABASE_URL/SUPABASE_ANON_KEY가 설정되지 않았습니다."
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


def load_ohlcv_supabase(coin_id: str) -> pd.DataFrame:
    rows = fetch_all_supabase(
        "ohlcv",
        "date,high,low,close",
        {
            "coin_id": f"eq.{coin_id}",
            "order": "date.asc",
        },
    )

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

    if within_1yr.empty:
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


# ══════════════════════════════════════════════════════
# Low 탐지 (Peak ~ 다음Peak 구간 최저점)
# ══════════════════════════════════════════════════════


def find_low_between(df: pd.DataFrame, from_ts: int, to_ts: int = None) -> tuple:
    """
    from_ts ~ to_ts 구간에서 최저점 날짜/가격 반환
    to_ts=None 이면 끝까지
    """
    mask = df["timestamp"] > from_ts
    if to_ts:
        mask &= df["timestamp"] < to_ts
    seg = df[mask]
    if seg.empty:
        return None, None
    idx = seg["low"].idxmin()
    low_ts = seg.loc[idx, "timestamp"]
    low_price = seg.loc[idx, "low"]
    return int(low_ts), float(low_price)


# ══════════════════════════════════════════════════════
# 사이클 데이터 계산
# ══════════════════════════════════════════════════════


def calculate_cycle(
    df: pd.DataFrame,
    peak_ts: int,
    peak_high: float,
    cycle_num: int,
    next_peak_ts: int = None,
    is_current: bool = False,
) -> list[dict]:
    mask = df["timestamp"] >= peak_ts
    if next_peak_ts:
        mask &= df["timestamp"] < next_peak_ts

    cycle_df = df[mask].copy().reset_index(drop=True)
    peak_date = ms_to_date(peak_ts)
    cycle_name = make_cycle_name(peak_ts, is_current=is_current)
    records = []

    for i, row in cycle_df.iterrows():
        records.append(
            {
                "cycle_number": cycle_num,
                "cycle_name": cycle_name,
                "days_since_peak": i,
                "timestamp": ms_to_date(int(row["timestamp"])),
                "close_price": row["close"],
                "low_price": row["low"],
                "high_price": row["high"],
                "close_rate": (row["close"] / peak_high) * 100,
                "low_rate": (row["low"] / peak_high) * 100,
                "high_rate": (row["high"] / peak_high) * 100,
                "peak_date": peak_date,
                "peak_price": peak_high,
            }
        )

    return records


# ══════════════════════════════════════════════════════
# Summary 계산
# ══════════════════════════════════════════════════════


def build_summary(df: pd.DataFrame, peaks: list[tuple]) -> list[dict]:
    """
    peaks: [(peak_ts, peak_high), ...]
    각 사이클별 Peak/Low 요약 생성
    """
    summaries = []

    for idx, (peak_ts, peak_high) in enumerate(peaks):
        cycle_num = idx + 1
        is_last = idx == len(peaks) - 1
        next_peak_ts = peaks[idx + 1][0] if idx + 1 < len(peaks) else None
        is_current = is_last and (next_peak_ts is None)
        cycle_name = make_cycle_name(peak_ts, is_current=is_current)

        # ── Low: 이 Peak ~ 다음 Peak 사이 최저점 (current cycle은 아직 끝나지 않았으므로 저점 미설정) ──
        if is_current:
            low_ts, low_price = None, None
        else:
            low_ts, low_price = find_low_between(df, peak_ts, next_peak_ts)

        # ── 직전 Peak ──
        if idx > 0:
            prev_peak_ts, prev_peak_price = peaks[idx - 1]
            prev_peak_date = ms_to_date(prev_peak_ts)
        else:
            prev_peak_ts = None
            prev_peak_price = None
            prev_peak_date = None

        # ── 직전 Low: 이전 Peak ~ 이 Peak 사이 최저점 ──
        prev_from_ts = prev_peak_ts if prev_peak_ts else df["timestamp"].min() - 1
        prev_low_ts, prev_low_price = find_low_between(df, prev_from_ts, peak_ts)

        # ── % 계산 ──
        if prev_low_price and prev_low_price > 0:
            peak_pct_from_low = ((peak_high - prev_low_price) / prev_low_price) * 100
        else:
            peak_pct_from_low = None

        if low_price and peak_high > 0:
            low_pct_from_peak = ((low_price - peak_high) / peak_high) * 100
        else:
            low_pct_from_peak = None

        summaries.append(
            {
                "cycle_number": cycle_num,
                "cycle_name": cycle_name,
                "peak_date": ms_to_date(peak_ts),
                "peak_price": peak_high,
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
                "prev_peak_date": prev_peak_date,
                "prev_peak_price": prev_peak_price,
                "prev_low_date": ms_to_date(prev_low_ts) if prev_low_ts else None,
                "prev_low_price": prev_low_price,
            }
        )

    return summaries


# ══════════════════════════════════════════════════════
# DB 저장 (Supabase)
# ══════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════
# 로그 출력 (Peak/Low 상세)
# ══════════════════════════════════════════════════════


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
    print("알트코인 사이클 분석 시작 (USDT 페어)")
    print("  DB MODE    : supabase")
    print(f"  Peak 조건 ①: 이후 1년 동안 고점 갱신 없음")
    print(f"  Peak 조건 ②: 고점 대비 {int(PEAK_DRAWDOWN_RATE*100)}% 이상 하락")
    print(f"  다음 탐색  : Peak 이후 3년 뒤부터")
    print("=" * 60)

    coins = get_coins_supabase()

    if not coins:
        print(
            "[ERROR] coins 테이블 비어있음. crypto_collector_usdt.py 먼저 실행하세요."
        )
        return

    print(f"총 {len(coins)}개 코인 분석 시작\n")

    success, skipped, no_peak = 0, 0, 0

    for i, (coin_id, symbol) in enumerate(coins, 1):
        print(f"[{i}/{len(coins)}] {symbol} ({coin_id})")

        df = load_ohlcv_supabase(coin_id)
        if df.empty or len(df) < 365:
            print(f"  → 데이터 부족 ({len(df)}일), 건너뜀\n")
            skipped += 1
            continue

        print(f"  데이터: {len(df)}일 ({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")

        # ── Peak 탐지 (디버그 로그 포함) ────────────────
        peaks = find_all_peaks(df, symbol)

        if not peaks:
            print(f"  → Peak 없음, 건너뜀\n")
            no_peak += 1
            continue

        # ── Current Cycle 탐지 ──────────────────────────
        last_peak_ts, last_peak_high = peaks[-1]
        last_cycle_num = len(peaks)
        current_search_ts = last_peak_ts + NEXT_SEARCH_MS

        today_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        after_3yr = df[
            (df["timestamp"] >= current_search_ts) & (df["timestamp"] <= today_ts)
        ]
        if not after_3yr.empty:
            current_cycle_num = last_cycle_num + 1

            current_peak_idx = after_3yr["high"].idxmax()
            current_peak_ts = int(df.loc[current_peak_idx, "timestamp"])
            current_peak_high = float(df.loc[current_peak_idx, "high"])

            print(
                f"    [Current Peak]  {ms_to_date(current_peak_ts)}"
                f"  @ {current_peak_high:>14,.4f}"
            )

            peaks.append((current_peak_ts, current_peak_high))

        # ── 사이클 데이터 계산 ──────────────────────────
        all_records = []
        for idx, (peak_ts, peak_high) in enumerate(peaks):
            cycle_num = idx + 1
            next_peak_ts = peaks[idx + 1][0] if idx + 1 < len(peaks) else None
            is_current = (next_peak_ts is None) and (idx == len(peaks) - 1)
            records = calculate_cycle(
                df, peak_ts, peak_high, cycle_num, next_peak_ts, is_current
            )
            all_records.extend(records)

        # ── Summary 계산 ────────────────────────────────
        summaries = build_summary(df, peaks)

        # ── 로그 출력 ────────────────────────────────────
        print_coin_result(summaries)
        print(f"  → {len(peaks)}개 사이클, {len(all_records)}행 저장 ✓\n")

        # ── DB 저장 ──────────────────────────────────────
        save_cycle_data_supabase(coin_id, all_records)
        save_summary_supabase(coin_id, summaries)
        success += 1

    print("=" * 60)
    print(f"완료: 성공 {success}개 / Peak없음 {no_peak}개 / 데이터부족 {skipped}개")
    print("=" * 60)

    print_summary_supabase()


if __name__ == "__main__":
    main()
