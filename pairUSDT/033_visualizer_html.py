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

from lib.common.config import DB_PATH
from lib.visualizer.db import build_json, load_all_coins
from lib.visualizer.renderer import generate_html, rewrite_dist_imports

BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = str(BASE_DIR / "033_visualizer_html.html")
TS_CONFIG = BASE_DIR / "tsconfig.frontend.json"
HTTP_PORT = 8765


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
        print("[WARN] npx/tsc not found. Skipping TypeScript build; using existing dist.")
        return dist_dir.exists()

    if result.returncode != 0:
        print(f"[ERROR] TypeScript build failed (exit code {result.returncode}). dist 미갱신.")
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
    conn = sqlite3.connect(DB_PATH)
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
