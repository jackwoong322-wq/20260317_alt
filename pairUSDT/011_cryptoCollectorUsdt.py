"""
암호화폐 데이터 수집기 (Binance + CryptoCompare 병행) - USDT 페어

코인 목록 전략:
  1. CoinGecko 시총 상위 300개 조회
  2. Binance USDT 상장 여부 필터
  3. 교집합에서 시총 순서 유지하여 상위 100개 선택

데이터 수집:
  1단계 - Binance  → 상장일부터 현재까지 OHLCV
  2단계 - CryptoCompare → Binance 상장 이전 데이터 보완

DB: Supabase (coins, ohlcv)
"""

import os
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from lib.common.config import SUPABASE_ANON_KEY, SUPABASE_URL

# ── .env 로드 ──────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _SCRIPT_DIR.parent
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_SCRIPT_DIR / ".env", override=False)
CC_API_KEY = os.getenv("CC_API_KEY")
if not CC_API_KEY:
    raise ValueError(".env 파일에 CC_API_KEY가 없습니다.")

# ── 설정 ──────────────────────────────────────────────
BINANCE_QUOTE = "USDT"
CC_QUOTE = "USD"
CG_TOP_N = 20  # CoinGecko 시총 상위 N개
FINAL_TOP_N = 10  # 최종 수집 대상
CG_DELAY = 2.5
BINANCE_DELAY = 0.2
CC_DELAY = 0.5
MAX_RETRIES = 3

# 스테이블코인 제외 (CoinGecko ID 기준)
STABLE_IDS = {
    "tether",
    "usd-coin",
    "dai",
    "binance-usd",
    "trueusd",
    "usdd",
    "frax",
    "usds",
    "paypal-usd",
    "ethena-usde",
    "ondo-us-dollar-yield",
    "first-digital-usd",
    "tether-gold",
    "pax-gold",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("collector_usdt.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)
# Suppress verbose HTTP client logs from supabase/httpx internals.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError(
            "DB_MODE=supabase 이지만 SUPABASE_URL/SUPABASE_ANON_KEY가 설정되지 않았습니다."
        )
    try:
        from supabase import create_client
    except ImportError as e:
        raise ImportError("supabase 패키지가 필요합니다. pip install supabase") from e
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ══════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════


def ts_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def date_to_ts(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def api_get(
    url: str, params: dict = None, retries: int = MAX_RETRIES
) -> dict | list | None:
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, params=params, timeout=30)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 429:
                wait = 60 * attempt
                log.warning(f"Rate limit! {wait}초 대기 후 재시도...")
                time.sleep(wait)
            else:
                log.error(f"HTTP {res.status_code} | {url} | {res.text[:200]}")
                return None
        except requests.RequestException as e:
            log.error(f"요청 오류 (시도 {attempt}/{retries}): {e}")
            time.sleep(5 * attempt)
    return None


# ══════════════════════════════════════════════════════
# Step 1: CoinGecko 시총 상위 300개
# ══════════════════════════════════════════════════════


def cg_fetch_top_coins(limit: int = CG_TOP_N) -> list[dict]:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    coins = []
    per_page = 100
    pages = (limit + per_page - 1) // per_page

    for page in range(1, pages + 1):
        data = api_get(
            url,
            {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": False,
            },
        )
        if data:
            coins.extend(data)
        time.sleep(CG_DELAY)

    # 스테이블코인 제외
    coins = [c for c in coins if c["id"] not in STABLE_IDS]
    log.info(f"CoinGecko: 시총 상위 {limit}개 조회 → 스테이블 제외 후 {len(coins)}개")
    return coins[:limit]


# ══════════════════════════════════════════════════════
# Step 2: Binance USDT 상장 심볼 목록
# ══════════════════════════════════════════════════════


def binance_fetch_usdt_symbols() -> set[str]:
    """
    Binance에 USDT 페어로 상장된 심볼 집합 반환
    레버리지 토큰(UP/DOWN/BULL/BEAR) 제외
    예: {"BTC", "ETH", "SOL", ...}
    """
    url = "https://api.binance.com/api/v3/exchangeInfo"
    data = api_get(url)
    if not data:
        raise RuntimeError("Binance exchangeInfo 조회 실패")

    EXCLUDE_SUFFIX = {"DOWN", "UP", "BULL", "BEAR"}

    symbols = set()
    for s in data["symbols"]:
        if s["quoteAsset"] != "USDT":
            continue
        if s["status"] != "TRADING":
            continue
        base = s["baseAsset"]
        # 레버리지 토큰 제외
        if any(base.endswith(suf) for suf in EXCLUDE_SUFFIX):
            continue
        symbols.add(base)

    log.info(f"Binance: USDT 상장 심볼 {len(symbols)}개")
    return symbols


# ══════════════════════════════════════════════════════
# Step 3: 교집합 → 최종 수집 목록
# ══════════════════════════════════════════════════════


def build_coin_list(
    cg_coins: list[dict], bn_symbols: set[str], top_n: int = FINAL_TOP_N
) -> list[dict]:
    """
    CoinGecko 시총 순서를 유지하면서 Binance 상장 코인만 필터
    """
    result = []
    for coin in cg_coins:
        symbol = coin["symbol"].upper()
        if symbol not in bn_symbols:
            continue
        result.append(
            {
                "id": coin["id"],
                "symbol": symbol,
                "name": coin["name"],
                "rank": coin.get("market_cap_rank") or len(result) + 1,
            }
        )
        if len(result) >= top_n:
            break

    log.info(
        f"최종 수집 대상: {len(result)}개 "
        f"(CoinGecko 시총 순위 유지, Binance USDT 상장 확인)"
    )
    return result


# ══════════════════════════════════════════════════════
# Binance OHLCV (1단계)
# ══════════════════════════════════════════════════════


def binance_fetch_all_klines(symbol: str) -> list[list]:
    url = "https://api.binance.com/api/v3/klines"
    all_klines, start_time = [], 0

    while True:
        data = api_get(
            url,
            {
                "symbol": f"{symbol}{BINANCE_QUOTE}",
                "interval": "1d",
                "startTime": start_time,
                "limit": 1000,
            },
        )
        time.sleep(BINANCE_DELAY)

        if not data:
            break

        all_klines.extend(data)

        if len(data) < 1000:
            break

        start_time = data[-1][6] + 1

    return all_klines


def parse_binance_klines(klines: list[list]) -> list[dict]:
    result = []
    for k in klines:
        result.append(
            {
                "date": ts_to_date(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume_base": float(k[5]),
                "volume_quote": float(k[7]),
                "trade_count": int(k[8]),
                "source": "binance",
            }
        )
    return result


# ══════════════════════════════════════════════════════
# CryptoCompare (2단계)
# ══════════════════════════════════════════════════════


def cc_fetch_before(symbol: str, before_date: str) -> list[dict]:
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    to_ts = date_to_ts(before_date) - 86400
    all_data = []

    while True:
        data = api_get(
            url,
            {
                "fsym": symbol.upper(),
                "tsym": CC_QUOTE,
                "limit": 2000,
                "toTs": to_ts,
                "api_key": CC_API_KEY,
            },
        )
        time.sleep(CC_DELAY)

        if not data or data.get("Response") != "Success":
            log.warning(
                f"  CC 응답 실패: {data.get('Message') if data else 'No response'}"
            )
            break

        rows = data["Data"]["Data"]
        rows = [r for r in rows if r["close"] != 0]

        if not rows:
            break

        all_data = rows + all_data
        earliest_ts = rows[0]["time"]
        to_ts = earliest_ts - 86400

        if len(rows) < 2000:
            break

    result = []
    for r in all_data:
        result.append(
            {
                "date": datetime.fromtimestamp(r["time"], tz=timezone.utc).strftime(
                    "%Y-%m-%d"
                ),
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume_base": r["volumefrom"],
                "volume_quote": r["volumeto"],
                "trade_count": 0,
                "source": "cryptocompare",
            }
        )
    return result


# ══════════════════════════════════════════════════════
# DB 저장 (Supabase)
# ══════════════════════════════════════════════════════


def save_coin_supabase(supabase, coin: dict):
    payload = {
        "id": coin["id"],
        "symbol": coin["symbol"],
        "name": coin["name"],
        "rank": coin["rank"],
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    supabase.table("coins").upsert(payload, on_conflict="id").execute()


def save_rows_supabase(supabase, coin_id: str, rows: list[dict]) -> int:
    if not rows:
        return 0, 0

    payload = [
        {
            "coin_id": coin_id,
            "date": r["date"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume_base": r["volume_base"],
            "volume_quote": r["volume_quote"],
            "trade_count": r["trade_count"],
            "source": r["source"],
        }
        for r in rows
    ]

    chunk_size = 500
    batch_count = 0
    for i in range(0, len(payload), chunk_size):
        batch_count += 1
        supabase.table("ohlcv").upsert(
            payload[i : i + chunk_size],
            on_conflict="coin_id,date",
        ).execute()
    return len(payload), batch_count


def get_ohlcv_count_supabase(supabase, coin_id: str) -> int:
    res = (
        supabase.table("ohlcv")
        .select("id", count="exact")
        .eq("coin_id", coin_id)
        .limit(1)
        .execute()
    )
    return int(res.count or 0)


# ══════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════


def main():
    log.info("=" * 55)
    log.info("암호화폐 데이터 수집 시작 (USDT 페어)")
    log.info("  MODE   : supabase")
    log.info("  Target : supabase")
    log.info(f"  Step1: CoinGecko 시총 상위 {CG_TOP_N}개")
    log.info(f"  Step2: Binance USDT 상장 필터")
    log.info(f"  Step3: 교집합 상위 {FINAL_TOP_N}개 수집")
    log.info("=" * 55)

    supabase = get_supabase_client()

    # ── 코인 목록 구성 ───────────────────────────────
    log.info("\n[코인 목록 구성]")
    cg_coins = cg_fetch_top_coins(CG_TOP_N)
    bn_symbols = binance_fetch_usdt_symbols()
    coins = build_coin_list(cg_coins, bn_symbols, FINAL_TOP_N)

    if not coins:
        log.error("수집 대상 코인이 없습니다.")
        return

    log.info(f"\n수집 대상 목록:")
    for c in coins:
        log.info(f"  #{c['rank']:<4} {c['symbol']:<10} {c['name']}")

    log.info(f"\n총 {len(coins)}개 코인 데이터 수집 시작\n")

    # ── 데이터 수집 ──────────────────────────────────
    for i, coin in enumerate(coins, 1):
        coin_id = coin["id"]
        symbol = coin["symbol"]

        log.info(f"[{i}/{len(coins)}] {symbol} ({coin_id})")
        save_coin_supabase(supabase, coin)

        # 1단계: Binance
        log.info(f"  [1단계] Binance {symbol}USDT 수집 중...")
        klines = binance_fetch_all_klines(symbol)

        if klines:
            rows = parse_binance_klines(klines)
            before_cnt = get_ohlcv_count_supabase(supabase, coin_id)
            saved, batch_count = save_rows_supabase(supabase, coin_id, rows)
            after_cnt = get_ohlcv_count_supabase(supabase, coin_id)
            reflected = max(0, after_cnt - before_cnt)
            earliest = rows[0]["date"]
            log.info(f"  Binance: 요청 {saved}건 / 배치 {batch_count}")
            log.info(f"  Binance: 실제 반영 {reflected}건 (count delta)")
            log.info(f"  Binance 최초 일자: {earliest}")
        else:
            log.warning(f"  Binance {symbol}USDT 없음 → 2단계에서 전체 수집")
            earliest = None

        # 2단계: CryptoCompare
        if earliest:
            log.info(f"  [2단계] CC {symbol}/USD → {earliest} 이전 수집 중...")
            cc_rows = cc_fetch_before(symbol, before_date=earliest)
        else:
            log.info(f"  [2단계] CC {symbol}/USD → 전체 수집 중...")
            today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            cc_rows = cc_fetch_before(symbol, before_date=today)

        if cc_rows:
            before_cnt_cc = get_ohlcv_count_supabase(supabase, coin_id)
            saved_cc, batch_count_cc = save_rows_supabase(supabase, coin_id, cc_rows)
            after_cnt_cc = get_ohlcv_count_supabase(supabase, coin_id)
            reflected_cc = max(0, after_cnt_cc - before_cnt_cc)

            log.info(f"  CC 보완: 요청 {saved_cc}건 / 배치 {batch_count_cc}")
            log.info(f"  CC 보완: 실제 반영 {reflected_cc}건 (count delta)")
            log.info(f"  CC 보완 최초 일자: {cc_rows[0]['date']}")
        else:
            log.info(f"  CC 보완 데이터 없음")

    log.info("\n" + "=" * 55)
    log.info("수집 완료! Supabase 저장 완료")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
