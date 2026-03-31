"""031_analyzer_to_sqlite.py

박스권 분석 및 AI 학습용 SQLite DB 구축

Usage: python 031_analyzer_to_sqlite.py
"""

import logging
import sqlite3
from datetime import datetime

import numpy as np
import requests

from lib.common.config import DB_MODE, DB_PATH, SUPABASE_ANON_KEY, SUPABASE_URL
from lib.common.utils import signed_log1p
from lib.analyzer.box_detector import detect_box_zones, detect_bear_bull
from lib.analyzer.finalizer import finalize_hi_lo_days, compute_change_pcts
from lib.analyzer.db import (
    setup_db,
    insert_zones,
    compute_day_metrics,
    load_all_coins,
    load_cycle_data,
    print_norm_stats,
)

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


def setup_stage_db_for_supabase(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS coins (
            id         TEXT PRIMARY KEY,
            symbol     TEXT NOT NULL,
            name       TEXT NOT NULL,
            rank       INTEGER,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS alt_cycle_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_id         TEXT    NOT NULL,
            cycle_number    INTEGER NOT NULL,
            cycle_name      TEXT,
            days_since_peak INTEGER NOT NULL,
            timestamp       TEXT    NOT NULL,
            close_price     REAL,
            low_price       REAL,
            high_price      REAL,
            close_rate      REAL,
            low_rate        REAL,
            high_rate       REAL,
            peak_date       TEXT,
            peak_price      REAL,
            UNIQUE(coin_id, cycle_number, days_since_peak)
        );

        CREATE INDEX IF NOT EXISTS idx_alt_cycle_coin
            ON alt_cycle_data(coin_id);
        CREATE INDEX IF NOT EXISTS idx_alt_cycle_coin_cycle
            ON alt_cycle_data(coin_id, cycle_number);
        """
    )
    conn.commit()


def hydrate_stage_db_from_supabase(conn: sqlite3.Connection):
    coins = fetch_all_supabase(
        "coins", "id,symbol,name,rank,updated_at", {"order": "rank.asc"}
    )
    cycles = fetch_all_supabase(
        "alt_cycle_data",
        "coin_id,cycle_number,cycle_name,days_since_peak,timestamp,close_rate,high_rate,low_rate,peak_date,peak_price",
        {"order": "coin_id.asc,cycle_number.asc,days_since_peak.asc"},
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO coins (id, symbol, name, rank, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                c.get("id"),
                c.get("symbol"),
                c.get("name"),
                c.get("rank"),
                c.get("updated_at"),
            )
            for c in coins
        ],
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO alt_cycle_data
            (coin_id, cycle_number, cycle_name, days_since_peak, timestamp,
             close_rate, high_rate, low_rate, peak_date, peak_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.get("coin_id"),
                r.get("cycle_number"),
                r.get("cycle_name"),
                r.get("days_since_peak"),
                str(r.get("timestamp", ""))[:10],
                r.get("close_rate"),
                r.get("high_rate"),
                r.get("low_rate"),
                r.get("peak_date"),
                r.get("peak_price"),
            )
            for r in cycles
        ],
    )

    conn.commit()
    log.info(
        "Supabase 데이터 적재 완료: coins=%d, alt_cycle_data=%d",
        len(coins),
        len(cycles),
    )


def sync_results_to_supabase(conn: sqlite3.Connection):
    headers = {**get_supabase_headers(include_json=True), "Prefer": "return=minimal"}

    # 기존 분석 결과(비예측) 삭제 후 재적재
    del_res = requests.delete(
        f"{SUPABASE_URL}/rest/v1/coin_analysis_results",
        params={"is_prediction": "eq.0"},
        headers=headers,
        timeout=60,
    )
    del_res.raise_for_status()

    rows = conn.execute(
        """
        SELECT coin_id, symbol, coin_rank,
               cycle_number, cycle_name,
               box_index, phase, result,
               start_x, end_x, hi, lo, hi_day, lo_day,
               duration, range_pct,
               hi_change_pct, lo_change_pct, gain_pct,
               norm_hi, norm_lo, norm_range_pct, norm_duration,
               norm_hi_change_pct, norm_lo_change_pct, norm_gain_pct,
               is_completed, is_prediction,
               rise_days, decline_days, rise_rate, decline_intensity
        FROM coin_analysis_results
        ORDER BY coin_id, cycle_number, box_index
        """
    ).fetchall()

    payload = [
        {
            "coin_id": r[0],
            "symbol": r[1],
            "coin_rank": r[2],
            "cycle_number": r[3],
            "cycle_name": r[4],
            "box_index": r[5],
            "phase": r[6],
            "result": r[7],
            "start_x": r[8],
            "end_x": r[9],
            "hi": r[10],
            "lo": r[11],
            "hi_day": r[12],
            "lo_day": r[13],
            "duration": r[14],
            "range_pct": r[15],
            "hi_change_pct": r[16],
            "lo_change_pct": r[17],
            "gain_pct": r[18],
            "norm_hi": r[19],
            "norm_lo": r[20],
            "norm_range_pct": r[21],
            "norm_duration": r[22],
            "norm_hi_change_pct": r[23],
            "norm_lo_change_pct": r[24],
            "norm_gain_pct": r[25],
            "is_completed": r[26],
            "is_prediction": r[27],
            "rise_days": r[28],
            "decline_days": r[29],
            "rise_rate": r[30],
            "decline_intensity": r[31],
        }
        for r in rows
    ]

    for i in range(0, len(payload), SUPABASE_PAGE_SIZE):
        chunk = payload[i : i + SUPABASE_PAGE_SIZE]
        ins_res = requests.post(
            f"{SUPABASE_URL}/rest/v1/coin_analysis_results",
            headers=headers,
            json=chunk,
            timeout=60,
        )
        ins_res.raise_for_status()

    log.info("Supabase coin_analysis_results 동기화 완료: %d행", len(payload))


def main():
    db_mode = (DB_MODE or "sqlite").strip().lower()
    log.info("031 실행 모드: %s", db_mode)

    if db_mode == "supabase":
        conn = sqlite3.connect(":memory:")
        setup_stage_db_for_supabase(conn)
        setup_db(conn)
        hydrate_stage_db_from_supabase(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        setup_db(conn)

    deleted = conn.execute(
        "DELETE FROM coin_analysis_results WHERE is_prediction = 0"
    ).rowcount
    conn.commit()
    log.info("기존 분석 데이터 %d건 삭제 후 재분석 시작", deleted)

    coins = load_all_coins(conn)
    if not coins:
        log.error("코인 데이터 없음. alt_cycle_data 테이블을 먼저 채워주세요.")
        conn.close()
        return

    log.info("분석 대상 코인: %d개", len(coins))

    all_norm_range: list = []
    all_norm_hi_chg: list = []
    all_norm_lo_chg: list = []
    all_norm_gain: list = []
    all_norm_duration: list = []

    total_zones = 0

    for coin_id, symbol, name, rank in coins:
        cycles = load_cycle_data(conn, coin_id)
        coin_total = 0

        for cn, cycle in cycles.items():
            data = cycle["data"]
            if len(data) < 2:
                continue

            last_cycle_num = max(cycles.keys())
            zones = detect_box_zones(data, is_last_cycle=(cn == last_cycle_num))
            if not zones:
                log.debug("  [%s] Cycle %d → 박스권 없음", symbol, cn)
                continue

            zones = finalize_hi_lo_days(zones, data)

            # 과거 사이클 마지막 BULL 박스 hi 보정 (compute_change_pcts 전에 실행해야 gain_pct 등에 반영)
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
                                abs(corrected_hi - last_bull["lo"])
                                / last_bull["lo"]
                                * 100
                                if last_bull["lo"] > 0
                                else 0.0
                            )

            zones = compute_change_pcts(zones, data)

            bear_cnt = sum(1 for z in zones if z["phase"] == "BEAR")
            bull_cnt = sum(1 for z in zones if z["phase"] == "BULL")
            if symbol.upper() == "BTC":
                log.info(
                    "  [%s] %s → BEAR %d개 / BULL %d개 (총 %d개)",
                    symbol,
                    cycle["cycle_name"],
                    bear_cnt,
                    bull_cnt,
                    len(zones),
                )
                print(f"  ┌─────────────────────────────────────────")
                print(f"  │ BEAR:")
                for zi, z in enumerate(zones):
                    if z["phase"] == "BEAR":
                        print(
                            f"  │   #{zi} day {z['start_x']:4d}~{z['end_x']:4d}  hi={z['hi']:7.2f}%  lo={z['lo']:7.2f}%  gain={z.get('gain_pct', 0.0) or 0.0:8.2f}%  result={z['result']}"
                        )
                print(f"  │ BULL:")
                for zi, z in enumerate(zones):
                    if z["phase"] == "BULL":
                        print(
                            f"  │   #{zi} day {z['start_x']:4d}~{z['end_x']:4d}  hi={z['hi']:7.2f}%  lo={z['lo']:7.2f}%  gain={z.get('gain_pct', 0.0) or 0.0:8.2f}%  result={z['result']}"
                        )
                bull_zones = [z for z in zones if z["phase"] == "BULL"]
                cycle_min_idx_disp = zones[0].get("cycle_min_idx", 0)
                cycle_lo = data[cycle_min_idx_disp]["low"]
                cycle_lo_day = data[cycle_min_idx_disp]["x"]
                if bull_zones:
                    max_bull = max(bull_zones, key=lambda z: z["hi"])
                    cycle_hi = max_bull["hi"]
                    cycle_hi_day = max_bull.get("hi_day", max_bull["end_x"])
                    max_gain_pct = max(
                        z.get("gain_pct", 0.0) or 0.0 for z in bull_zones
                    )
                else:
                    cycle_hi = 0.0
                    cycle_hi_day = 0
                    max_gain_pct = 0.0
                print(f"  ├─────────────────────────────────────────")
                print(f"  │ 사이클 저점 : lo={cycle_lo:7.2f}%  day={cycle_lo_day}")
                print(f"  │ 사이클 고점 : hi={cycle_hi:7.2f}%  day={cycle_hi_day}")
                print(f"  │ gain_pct 최대: {max_gain_pct:.2f}%")
                print(f"  └─────────────────────────────────────────")
                if cn < last_cycle_num:
                    for zi, z in enumerate(zones):
                        if z["result"] == "ACTIVE":
                            log.warning(
                                "  [BTC] %s에 ACTIVE 박스 존재 → box#%d (과거 사이클인데 ACTIVE?)",
                                cycle["cycle_name"],
                                zi,
                            )

            for zi, z in enumerate(zones):
                rp = z["range_pct"]
                hcp = z.get("hi_change_pct", 0.0) or 0.0
                lcp = z.get("lo_change_pct", 0.0) or 0.0
                gp = z.get("gain_pct", 0.0) or 0.0
                dur = z["duration"]

                log.debug(
                    "    Box #%d [%s] day %d~%d (%dd) "
                    "hi=%.2f%% lo=%.2f%% range=%.1f%% "
                    "hi_chg=%.1f%%(norm=%.3f) "
                    "gain=%.1f%%(norm=%.3f) "
                    "result=%s",
                    zi + 1,
                    z["phase"],
                    z["start_x"],
                    z["end_x"],
                    dur,
                    z["hi"],
                    z["lo"],
                    rp,
                    hcp,
                    signed_log1p(hcp) or 0,
                    gp,
                    signed_log1p(gp) or 0,
                    z["result"],
                )

                all_norm_range.append(
                    float(np.log1p(rp))
                )  # range_pct 항상 양수; sqrt 대비 log1p가 std 더 안정적(검증됨)
                all_norm_duration.append(float(np.log1p(dur)))
                if hcp is not None:
                    all_norm_hi_chg.append(float(np.sign(hcp) * np.log1p(abs(hcp))))
                if lcp is not None:
                    all_norm_lo_chg.append(float(np.sign(lcp) * np.log1p(abs(lcp))))
                if gp is not None:
                    all_norm_gain.append(float(np.sign(gp) * np.log1p(abs(gp))))

            inserted = insert_zones(
                conn, coin_id, symbol, rank, cn, cycle["cycle_name"], zones
            )
            coin_total += inserted

        if symbol.upper() == "BTC":
            log.info("  [BTC] 저장 완료: %d개 박스", coin_total)
        total_zones += coin_total

    # ── Current 사이클 ACTIVE 재태깅 ─────────────────────────────────────────────
    # cycle_name LIKE '%Current%' 인 사이클의 마지막 박스(box_index 최대값)만 ACTIVE (is_completed=0)
    # 나머지 박스는 기존 result 유지 + is_completed=1
    cur_cycles = conn.execute(
        """
        SELECT DISTINCT coin_id, cycle_number
        FROM coin_analysis_results
        WHERE is_prediction = 0
          AND cycle_name LIKE '%Current%'
        """
    ).fetchall()
    for cid, cyc in cur_cycles:
        # 해당 Current 사이클의 모든 박스를 completed로 설정
        conn.execute(
            """
            UPDATE coin_analysis_results
            SET is_completed = 1
            WHERE is_prediction = 0
              AND coin_id = ?
              AND cycle_number = ?
            """,
            (cid, cyc),
        )
        # 마지막 박스(box_index 최대값)를 ACTIVE로 재태깅
        row = conn.execute(
            """
            SELECT MAX(box_index)
            FROM coin_analysis_results
            WHERE is_prediction = 0
              AND coin_id = ?
              AND cycle_number = ?
            """,
            (cid, cyc),
        ).fetchone()
        if row and row[0] is not None:
            max_idx = row[0]
            conn.execute(
                """
                UPDATE coin_analysis_results
                SET is_completed = 0,
                    result       = 'ACTIVE'
                WHERE is_prediction = 0
                  AND coin_id = ?
                  AND cycle_number = ?
                  AND box_index = ?
                """,
                (cid, cyc, max_idx),
            )
    conn.commit()

    log.info("=" * 65)
    log.info("총 저장 박스: %d개", total_zones)
    log.info("로그 변환값 범위 요약:")
    print_norm_stats("norm_range_pct", all_norm_range)
    print_norm_stats("norm_duration", all_norm_duration)
    print_norm_stats("norm_hi_change_pct", all_norm_hi_chg)
    print_norm_stats("norm_lo_change_pct", all_norm_lo_chg)
    print_norm_stats("norm_gain_pct", all_norm_gain)
    compute_day_metrics(conn)

    if db_mode == "supabase":
        sync_results_to_supabase(conn)

    log.info("분석 완료 — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    conn.close()


if __name__ == "__main__":
    main()
