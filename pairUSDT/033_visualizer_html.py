"""033_visualizer_html.py

기존 UI/차트 시각화 (DB 데이터 기반)

Usage: python 033_visualizer_html.py

[설계 결정] file:// 에서 ES module 로드 시 CORS 차단되므로
로컬 HTTP 서버로 제공. Ctrl+C 로 서버 종료.
"""

import sqlite3
import subprocess
import webbrowser
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import requests

from lib.common.config import DB_MODE, DB_PATH, SUPABASE_ANON_KEY, SUPABASE_URL
from lib.visualizer.db import build_json, load_all_coins
from lib.visualizer.renderer import generate_html, rewrite_dist_imports

BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = str(BASE_DIR / "033_visualizer_html.html")
TS_CONFIG = BASE_DIR / "tsconfig.frontend.json"
HTTP_PORT = 8765
SUPABASE_PAGE_SIZE = 1000


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


def setup_stage_db(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS coins (
            id TEXT PRIMARY KEY,
            symbol TEXT,
            name TEXT,
            rank INTEGER
        );

        CREATE TABLE IF NOT EXISTS alt_cycle_data (
            coin_id TEXT,
            cycle_number INTEGER,
            cycle_name TEXT,
            days_since_peak INTEGER,
            close_rate REAL,
            high_rate REAL,
            low_rate REAL,
            peak_date TEXT,
            peak_price REAL,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS coin_analysis_results (
            coin_id TEXT,
            cycle_number INTEGER,
            box_index INTEGER,
            phase TEXT,
            result TEXT,
            start_x INTEGER,
            end_x INTEGER,
            hi REAL,
            lo REAL,
            hi_day INTEGER,
            lo_day INTEGER,
            duration INTEGER,
            range_pct REAL,
            is_prediction INTEGER,
            is_completed INTEGER,
            rise_days INTEGER,
            decline_days INTEGER
        );

        CREATE TABLE IF NOT EXISTS coin_prediction_paths (
            coin_id TEXT,
            cycle_number INTEGER,
            scenario TEXT,
            day_x INTEGER,
            value REAL
        );

        CREATE TABLE IF NOT EXISTS coin_prediction_peaks (
            coin_id TEXT,
            cycle_number INTEGER,
            peak_type TEXT,
            predicted_value REAL,
            predicted_day INTEGER
        );
        """
    )
    conn.commit()


def _insert_rows(
    conn: sqlite3.Connection, table: str, columns: list[str], rows: list[dict]
):
    if not rows:
        return
    placeholders = ",".join(["?" for _ in columns])
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
    values = [tuple(r.get(c) for c in columns) for r in rows]
    conn.executemany(sql, values)
    conn.commit()


def build_connection_for_mode() -> sqlite3.Connection:
    db_mode = (DB_MODE or "sqlite").strip().lower()
    if db_mode != "supabase":
        return sqlite3.connect(DB_PATH)

    conn = sqlite3.connect(":memory:")
    setup_stage_db(conn)

    coins = fetch_all_supabase("coins", "id,symbol,name,rank")
    _insert_rows(conn, "coins", ["id", "symbol", "name", "rank"], coins)

    cycle_rows = fetch_all_supabase(
        "alt_cycle_data",
        "coin_id,cycle_number,cycle_name,days_since_peak,close_rate,high_rate,low_rate,peak_date,peak_price,timestamp",
    )
    _insert_rows(
        conn,
        "alt_cycle_data",
        [
            "coin_id",
            "cycle_number",
            "cycle_name",
            "days_since_peak",
            "close_rate",
            "high_rate",
            "low_rate",
            "peak_date",
            "peak_price",
            "timestamp",
        ],
        cycle_rows,
    )

    box_rows = fetch_all_supabase(
        "coin_analysis_results",
        "coin_id,cycle_number,box_index,phase,result,start_x,end_x,hi,lo,hi_day,lo_day,duration,range_pct,is_prediction,is_completed,rise_days,decline_days",
    )
    _insert_rows(
        conn,
        "coin_analysis_results",
        [
            "coin_id",
            "cycle_number",
            "box_index",
            "phase",
            "result",
            "start_x",
            "end_x",
            "hi",
            "lo",
            "hi_day",
            "lo_day",
            "duration",
            "range_pct",
            "is_prediction",
            "is_completed",
            "rise_days",
            "decline_days",
        ],
        box_rows,
    )

    path_rows = fetch_all_supabase(
        "coin_prediction_paths",
        "coin_id,cycle_number,scenario,day_x,value",
    )
    _insert_rows(
        conn,
        "coin_prediction_paths",
        ["coin_id", "cycle_number", "scenario", "day_x", "value"],
        path_rows,
    )

    peak_rows = fetch_all_supabase(
        "coin_prediction_peaks",
        "coin_id,cycle_number,peak_type,predicted_value,predicted_day",
    )
    _insert_rows(
        conn,
        "coin_prediction_peaks",
        ["coin_id", "cycle_number", "peak_type", "predicted_value", "predicted_day"],
        peak_rows,
    )

    print(
        "[INFO] Supabase 데이터 적재 완료: "
        f"coins={len(coins)}, alt_cycle_data={len(cycle_rows)}, "
        f"analysis={len(box_rows)}, paths={len(path_rows)}, peaks={len(peak_rows)}"
    )
    return conn


def build_frontend_assets() -> bool:
    """TypeScript → dist 빌드. templates/dist/*.js 를 갱신한다. 성공 시 True."""
    if not TS_CONFIG.exists():
        print(f"[WARN] tsconfig.frontend.json not found at {TS_CONFIG}. Skip TS build.")
        return False

    dist_dir = BASE_DIR / "templates" / "dist"
    cmd = ["npx", "tsc", "-p", str(TS_CONFIG)]
    print(f"[INFO] dist 갱신: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            check=False,
        )
    except FileNotFoundError:
        print(
            "[WARN] npx/tsc not found. Skipping TypeScript build; using existing dist."
        )
        return dist_dir.exists()

    if result.returncode != 0:
        print(
            f"[ERROR] TypeScript build failed (exit code {result.returncode}). dist 미갱신."
        )
        return False
    print("[INFO] dist 갱신 완료 (tsc)")
    return True


def main():
    # 1) 매 실행 시 dist 갱신: TypeScript → templates/dist/*.js
    build_ok = build_frontend_assets()

    # 2) 서브모듈 캐시 무효화: dist/*.js 의 import 경로에 ?v= 붙임
    dist_dir = BASE_DIR / "templates" / "dist"
    script_version = int(time.time())
    if dist_dir.exists():
        rewrite_dist_imports(dist_dir, script_version)
        if build_ok:
            print("[INFO] dist 캐시버스트 적용 (?v=...)")
    else:
        print("[WARN] templates/dist 없음. 033 실행 전에 tsc로 빌드 필요.")

    # 3) DB에서 데이터 로드 후 HTML 생성
    conn = build_connection_for_mode()
    coins = load_all_coins(conn)

    if not coins:
        print("[ERROR] No coin data. Run alt_cycle_analysis.py first.")
        conn.close()
        return

    print(f"Loading data for {len(coins)} coins...")
    data = build_json(conn, coins)
    conn.close()

    html = generate_html(data, script_version)
    out = Path(OUT_FILE)
    out.write_text(html, encoding="utf-8")

    url = f"http://127.0.0.1:{HTTP_PORT}/033_visualizer_html.html"
    print(f"Chart saved: {out.resolve()}")
    print(f"Serving at {url} (Ctrl+C to stop)")
    webbrowser.open(url)

    import os

    os.chdir(BASE_DIR)
    server = HTTPServer(("", HTTP_PORT), SimpleHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
