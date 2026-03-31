"""031_box_analyzer_to_sqlite.py

박스권 분석 및 AI 학습용 분석 결과 생성 (Supabase 전용)

Usage: python 031_box_analyzer_to_sqlite.py
"""

import logging
from collections import defaultdict
from datetime import datetime

import numpy as np
import requests

from lib.common.config import SUPABASE_ANON_KEY, SUPABASE_URL
from lib.common.utils import safe_log1p, signed_log1p
from lib.analyzer.box_detector import detect_box_zones
from lib.analyzer.finalizer import finalize_hi_lo_days, compute_change_pcts
from lib.analyzer.db import print_norm_stats

log = logging.getLogger(__name__)

SUPABASE_PAGE_SIZE = 1000


def get_supabase_headers(include_json: bool = False) -> dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError(
            "DB_MODE=supabase 이지만 SUPABASE_URL/SUPABASE_ANON_KEY가 설정되지 않았습니다."
        )
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


def fetch_all_supabase(
    table: str, select_cols: str, extra_params: dict | None = None
) -> list[dict]:
    rows = []
    offset = 0
    headers = get_supabase_headers()

    while True:
        params = {"select": select_cols}
        if extra_params:
            params.update(extra_params)

        page_headers = {
            **headers,
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + SUPABASE_PAGE_SIZE - 1}",
        }
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params=params,
            headers=page_headers,
            timeout=60,
        )
        res.raise_for_status()

        batch = res.json()
        rows.extend(batch)
        if len(batch) < SUPABASE_PAGE_SIZE:
            break
        offset += SUPABASE_PAGE_SIZE

    return rows


def load_all_coins_and_cycles() -> tuple[list[tuple], dict]:
    coins = fetch_all_supabase("coins", "id,symbol,name,rank", {"order": "rank.asc"})
    cycle_rows = fetch_all_supabase(
        "alt_cycle_data",
        "coin_id,cycle_number,cycle_name,days_since_peak,close_rate,high_rate,low_rate,peak_date,peak_price,timestamp",
        {"order": "coin_id.asc,cycle_number.asc,days_since_peak.asc"},
    )

    cycles_by_coin: dict[str, dict] = {}
    for row in cycle_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue

        if coin_id not in cycles_by_coin:
            cycles_by_coin[coin_id] = {}
        if cycle_num not in cycles_by_coin[coin_id]:
            cycles_by_coin[coin_id][cycle_num] = {
                "cycle_number": cycle_num,
                "cycle_name": row.get("cycle_name"),
                "peak_date": row.get("peak_date"),
                "peak_price": row.get("peak_price"),
                "data": [],
            }

        cycles_by_coin[coin_id][cycle_num]["data"].append(
            {
                "x": int(row.get("days_since_peak") or 0),
                "close": round(float(row.get("close_rate") or 0.0), 4),
                "high": round(float(row.get("high_rate") or 0.0), 4),
                "low": round(float(row.get("low_rate") or 0.0), 4),
                "date": str(row.get("timestamp") or "")[:10],
            }
        )

    filtered_coins = []
    for c in coins:
        cid = c.get("id")
        if cid and cid in cycles_by_coin:
            filtered_coins.append((cid, c.get("symbol"), c.get("name"), c.get("rank")))

    log.info(
        "Supabase 데이터 적재 완료: coins=%d, alt_cycle_data=%d",
        len(filtered_coins),
        len(cycle_rows),
    )
    return filtered_coins, cycles_by_coin


def build_zone_rows(
    coin_id: str,
    symbol: str,
    coin_rank: int | None,
    cycle_number: int,
    cycle_name: str,
    zones: list[dict],
) -> list[dict]:
    rows = []
    for zi, z in enumerate(zones):
        rp = float(z["range_pct"])
        hi = float(z["hi"])
        lo = float(z["lo"])
        dur = int(z["duration"])
        hcp = z.get("hi_change_pct")
        lcp = z.get("lo_change_pct")
        gp = z.get("gain_pct")

        row = {
            "coin_id": coin_id,
            "symbol": symbol,
            "coin_rank": coin_rank,
            "cycle_number": cycle_number,
            "cycle_name": cycle_name,
            "box_index": zi,
            "phase": z["phase"],
            "result": z["result"],
            "start_x": int(z["start_x"]),
            "end_x": int(z["end_x"]),
            "hi": hi,
            "lo": lo,
            "hi_day": z.get("hi_day"),
            "lo_day": z.get("lo_day"),
            "duration": dur,
            "range_pct": rp,
            "hi_change_pct": hcp,
            "lo_change_pct": lcp,
            "gain_pct": gp,
            "norm_hi": safe_log1p(hi),
            "norm_lo": safe_log1p(lo),
            "norm_range_pct": safe_log1p(rp),
            "norm_duration": safe_log1p(dur),
            "norm_hi_change_pct": signed_log1p(hcp) if hcp is not None else None,
            "norm_lo_change_pct": signed_log1p(lcp) if lcp is not None else None,
            "norm_gain_pct": signed_log1p(gp) if gp is not None else None,
            "is_completed": 1 if z["result"] != "ACTIVE" else 0,
            "is_prediction": 0,
            "rise_days": None,
            "decline_days": None,
            "rise_rate": None,
            "decline_intensity": None,
        }
        rows.append(row)
    return rows


def apply_current_cycle_active_retag(rows: list[dict]):
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("is_prediction") == 0 and "Current" in str(r.get("cycle_name") or ""):
            groups[(r["coin_id"], r["cycle_number"])].append(r)

    for _, grp in groups.items():
        for r in grp:
            r["is_completed"] = 1
        max_box = max(r["box_index"] for r in grp)
        for r in grp:
            if r["box_index"] == max_box:
                r["is_completed"] = 0
                r["result"] = "ACTIVE"
                break


def apply_day_metrics(rows: list[dict]):
    grouped: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    for r in rows:
        grouped[(r["coin_id"], r["cycle_number"], r["is_prediction"])].append(r)

    for _, grp in grouped.items():
        grp.sort(key=lambda x: x["box_index"])

        for i, r in enumerate(grp):
            hi_day = r.get("hi_day")
            lo_day = r.get("lo_day")
            if hi_day is not None and lo_day is not None:
                r["rise_days"] = int(hi_day) - int(lo_day)

            if lo_day is not None:
                if i == 0:
                    r["decline_days"] = int(lo_day)
                else:
                    prev_hi = grp[i - 1].get("hi_day")
                    if prev_hi is not None:
                        r["decline_days"] = int(lo_day) - int(prev_hi)

            if r.get("duration") and r.get("rise_days") is not None and r["duration"] > 0:
                r["rise_rate"] = float(r["rise_days"]) / float(r["duration"])

            if r.get("rise_days") and r["rise_days"] > 0 and r.get("decline_days") is not None:
                r["decline_intensity"] = float(r["decline_days"]) / float(r["rise_days"])


def _normalize_value(v):
    if isinstance(v, np.generic):
        return v.item()
    return v


def sync_results_to_supabase(rows: list[dict]):
    headers = {**get_supabase_headers(include_json=True), "Prefer": "return=minimal"}

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/coin_analysis_results",
        params={"is_prediction": "eq.0"},
        headers=headers,
        timeout=60,
    ).raise_for_status()

    if not rows:
        log.info("Supabase coin_analysis_results 동기화 완료: 0행")
        return

    for i in range(0, len(rows), SUPABASE_PAGE_SIZE):
        chunk = rows[i : i + SUPABASE_PAGE_SIZE]
        payload = [{k: _normalize_value(v) for k, v in row.items()} for row in chunk]
        requests.post(
            f"{SUPABASE_URL}/rest/v1/coin_analysis_results",
            headers=headers,
            json=payload,
            timeout=60,
        ).raise_for_status()

    log.info("Supabase coin_analysis_results 동기화 완료: %d행", len(rows))


def main():
    log.info("031 실행 모드: supabase")

    coins, cycles_by_coin = load_all_coins_and_cycles()
    if not coins:
        log.error("코인 데이터 없음. alt_cycle_data 테이블을 먼저 채워주세요.")
        return

    log.info("분석 대상 코인: %d개", len(coins))

    all_norm_range: list[float] = []
    all_norm_hi_chg: list[float] = []
    all_norm_lo_chg: list[float] = []
    all_norm_gain: list[float] = []
    all_norm_duration: list[float] = []

    all_rows: list[dict] = []

    for coin_id, symbol, _name, rank in coins:
        cycles = cycles_by_coin.get(coin_id, {})
        coin_total = 0

        for cn, cycle in cycles.items():
            data = cycle["data"]
            if len(data) < 2:
                continue

            last_cycle_num = max(cycles.keys())
            zones = detect_box_zones(data, is_last_cycle=(cn == last_cycle_num))
            if not zones:
                continue

            zones = finalize_hi_lo_days(zones, data)

            if cn < last_cycle_num:
                next_cycle = cycles.get(cn + 1)
                if next_cycle:
                    this_peak = cycle.get("peak_price")
                    next_peak = next_cycle.get("peak_price")
                    if this_peak and next_peak and this_peak > 0:
                        bull_zones_corr = [z for z in zones if z["phase"] == "BULL"]
                        if bull_zones_corr:
                            last_bull = bull_zones_corr[-1]
                            corrected_hi = next_peak / this_peak * 100
                            last_bull["hi"] = corrected_hi
                            last_bull["hi_day"] = last_bull["end_x"]
                            last_bull["range_pct"] = (
                                abs(corrected_hi - last_bull["lo"]) / last_bull["lo"] * 100
                                if last_bull["lo"] > 0
                                else 0.0
                            )

            zones = compute_change_pcts(zones, data)

            for z in zones:
                rp = float(z["range_pct"])
                hcp = z.get("hi_change_pct", 0.0) or 0.0
                lcp = z.get("lo_change_pct", 0.0) or 0.0
                gp = z.get("gain_pct", 0.0) or 0.0
                dur = int(z["duration"])

                all_norm_range.append(float(np.log1p(rp)))
                all_norm_duration.append(float(np.log1p(dur)))
                all_norm_hi_chg.append(float(np.sign(hcp) * np.log1p(abs(hcp))))
                all_norm_lo_chg.append(float(np.sign(lcp) * np.log1p(abs(lcp))))
                all_norm_gain.append(float(np.sign(gp) * np.log1p(abs(gp))))

            rows = build_zone_rows(
                coin_id=coin_id,
                symbol=str(symbol),
                coin_rank=rank,
                cycle_number=cn,
                cycle_name=str(cycle["cycle_name"]),
                zones=zones,
            )
            all_rows.extend(rows)
            coin_total += len(rows)

        if str(symbol).upper() == "BTC":
            log.info("  [BTC] 저장 완료: %d개 박스", coin_total)

    apply_current_cycle_active_retag(all_rows)
    apply_day_metrics(all_rows)

    log.info("=" * 65)
    log.info("총 저장 박스: %d개", len(all_rows))
    log.info("로그 변환값 범위 요약:")
    print_norm_stats("norm_range_pct", all_norm_range)
    print_norm_stats("norm_duration", all_norm_duration)
    print_norm_stats("norm_hi_change_pct", all_norm_hi_chg)
    print_norm_stats("norm_lo_change_pct", all_norm_lo_chg)
    print_norm_stats("norm_gain_pct", all_norm_gain)

    sync_results_to_supabase(all_rows)

    log.info("분석 완료 — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
