"""033_visualizer_html.py

기존 UI/차트 시각화 (DB 데이터 기반)

Usage: python 033_visualizer_html.py

[설계 결정] file:// 에서 ES module 로드 시 CORS 차단되므로
로컬 HTTP 서버로 제공. Ctrl+C 로 서버 종료.
"""

import subprocess
import webbrowser
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import requests

from lib.common.config import SUPABASE_ANON_KEY, SUPABASE_URL
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


def _apply_active_box_display_from_first_pred(cycle_zones: list) -> list:
    if not cycle_zones:
        return cycle_zones
    first_pred = next((z for z in cycle_zones if z.get("is_prediction") == 1), None)
    if not first_pred:
        return cycle_zones

    first_phase = (first_pred.get("phase") or "").upper()
    if first_phase not in ("BEAR", "BULL"):
        return cycle_zones

    active_result = "BEAR_ACTIVE" if first_phase == "BEAR" else "BULL_ACTIVE"
    out = []
    for z in cycle_zones:
        zcopy = dict(z)
        if z.get("is_completed") == 0 and z.get("is_prediction") == 0:
            zcopy["phase"] = first_phase
            zcopy["result"] = active_result
        out.append(zcopy)
    return out


def build_json_from_supabase() -> dict:
    coins_rows = fetch_all_supabase(
        "coins", "id,symbol,name,rank", {"order": "rank.asc"}
    )
    cycle_rows = fetch_all_supabase(
        "alt_cycle_data",
        "coin_id,cycle_number,cycle_name,days_since_peak,close_rate,high_rate,low_rate,peak_date,peak_price,timestamp",
        {"order": "coin_id.asc,cycle_number.asc,days_since_peak.asc"},
    )
    box_rows = fetch_all_supabase(
        "coin_analysis_results",
        "coin_id,cycle_number,box_index,phase,result,start_x,end_x,hi,lo,hi_day,lo_day,duration,range_pct,is_prediction,is_completed,rise_days,decline_days",
        {"order": "coin_id.asc,cycle_number.asc,box_index.asc"},
    )
    path_rows = fetch_all_supabase(
        "coin_prediction_paths",
        "coin_id,cycle_number,scenario,day_x,value",
        {"order": "coin_id.asc,cycle_number.asc,scenario.asc,day_x.asc"},
    )
    peak_rows = fetch_all_supabase(
        "coin_prediction_peaks",
        "coin_id,cycle_number,peak_type,predicted_value,predicted_day",
        {"order": "coin_id.asc,cycle_number.asc"},
    )

    print(
        "[INFO] Supabase 데이터 적재 완료: "
        f"coins={len(coins_rows)}, alt_cycle_data={len(cycle_rows)}, "
        f"analysis={len(box_rows)}, paths={len(path_rows)}, peaks={len(peak_rows)}"
    )

    cycles_by_coin: dict = {}
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

    box_by_coin_cycle: dict = {}
    for row in box_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue
        box_by_coin_cycle.setdefault(coin_id, {}).setdefault(cycle_num, []).append(
            {
                "boxIndex": int(row.get("box_index") or 0),
                "startX": row.get("start_x"),
                "endX": row.get("end_x"),
                "hi": row.get("hi"),
                "lo": row.get("lo"),
                "hiDay": row.get("hi_day"),
                "loDay": row.get("lo_day"),
                "duration": row.get("duration"),
                "rangePct": f"{float(row.get('range_pct') or 0.0):.1f}",
                "phase": row.get("phase"),
                "result": row.get("result"),
                "is_prediction": row.get("is_prediction"),
                "is_completed": row.get("is_completed"),
                "rise_days": row.get("rise_days"),
                "decline_days": row.get("decline_days"),
            }
        )

    path_by_coin_cycle: dict = {}
    for row in path_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue
        path_by_coin_cycle.setdefault(coin_id, {}).setdefault(
            cycle_num, {"bull": [], "bear": []}
        )
        key = str(row.get("scenario") or "").lower()
        key = key if key in ("bull", "bear") else "bull"
        path_by_coin_cycle[coin_id][cycle_num][key].append(
            {"x": row.get("day_x"), "value": row.get("value")}
        )

    peak_by_coin_cycle: dict = {}
    for row in peak_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue
        peak_by_coin_cycle.setdefault(coin_id, {}).setdefault(cycle_num, []).append(
            {
                "type": row.get("peak_type"),
                "value": row.get("predicted_value"),
                "day_x": row.get("predicted_day"),
            }
        )

    total_bz = sum(len(v2) for v1 in box_by_coin_cycle.values() for v2 in v1.values())
    print(
        f"[DB] coin_analysis_results 로드: {total_bz}개 박스 "
        f"({'DB 데이터 사용' if total_bz > 0 else '없음 → JS 폴백'})"
    )

    out: dict = {}
    for c in coins_rows:
        coin_id = c.get("id")
        if not coin_id:
            continue

        cycles = dict(cycles_by_coin.get(coin_id, {}))
        coin_zones = box_by_coin_cycle.get(coin_id, {})

        if not cycles and not coin_zones:
            continue

        if not cycles and coin_zones:
            for cn in coin_zones:
                cycles[cn] = {
                    "cycle_number": cn,
                    "cycle_name": f"Cycle {cn}",
                    "peak_date": "",
                    "peak_price": None,
                    "data": [],
                }

        cycles_list = []
        for cn in sorted(cycles.keys()):
            cycle_data = cycles[cn]
            raw_zones = coin_zones.get(cn, [])
            cycle_zones = _apply_active_box_display_from_first_pred(raw_zones)
            cycle_paths = path_by_coin_cycle.get(coin_id, {}).get(
                cn, {"bull": [], "bear": []}
            )
            cycle_peaks = peak_by_coin_cycle.get(coin_id, {}).get(cn, [])
            cycles_list.append(
                {
                    "cycle_number": cn,
                    "cycle_name": cycle_data.get("cycle_name"),
                    "peak_date": cycle_data.get("peak_date"),
                    "peak_price": cycle_data.get("peak_price"),
                    "data": cycle_data.get("data", []),
                    "box_zones": cycle_zones,
                    "prediction_paths": cycle_paths,
                    "peak_predictions": cycle_peaks,
                }
            )

        out[coin_id] = {
            "symbol": str(c.get("symbol") or "").upper(),
            "name": c.get("name"),
            "rank": c.get("rank"),
            "cycles": cycles_list,
        }

    return out


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

    # 3) Supabase에서 데이터 로드 후 HTML 생성
    data = build_json_from_supabase()
    if not data:
        print("[ERROR] No coin data. Run alt_cycle_analysis.py first.")
        return

    print(f"Loading data for {len(data)} coins...")

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
