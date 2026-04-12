"""
암호화폐 OHLCV 업데이트 - USDT 페어

코인 목록:
  - DB의 coins 테이블에서 조회

데이터 업데이트:
  - ohlcv 테이블의 코인별 마지막 날짜 조회
  - 마지막 날짜 다음날부터 오늘까지 Binance에서 증분 수집

DB: Supabase (coins, ohlcv)
"""

import time
import logging
from datetime import datetime, timedelta, timezone

import requests

from lib.common.binance_public import fetch_klines_paginated
from lib.common.coingecko_ohlcv import fetch_daily_range as coingecko_fetch_daily_range
from lib.common.config import BINANCE_DELAY, SUPABASE_ANON_KEY, SUPABASE_URL

# ── 설정 ──────────────────────────────────────────────
BINANCE_QUOTE = "USDT"
MAX_RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("collector_usdt.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)
# Suppress verbose HTTP client logs from supabase/httpx internals.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ══════════════════════════════════════════════════════
# DB (Supabase)
# ══════════════════════════════════════════════════════


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError(
            "SUPABASE_URL/SUPABASE_ANON_KEY가 설정되지 않았습니다."
        )
    try:
        from supabase import create_client
    except ImportError as e:
        raise ImportError(
            "supabase 관련 import 실패: "
            f"{e}. (예: pip install -r requirements.txt 또는 pip install supabase PyJWT)"
        ) from e
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_coins_from_supabase(supabase) -> list[dict]:
    res = supabase.table("coins").select("id,symbol,name,rank").order("rank").execute()
    return res.data or []


def get_last_date_supabase(supabase, coin_id: str) -> str | None:
    res = (
        supabase.table("ohlcv")
        .select("date")
        .eq("coin_id", coin_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0].get("date")


# ══════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════


def ts_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def date_to_ts_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def next_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


def today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


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
            elif res.status_code == 451:
                log.error(
                    "HTTP 451: 접속 지역 제한 가능. Binance는 data-api.binance.vision 순차 시도 후 "
                    "CoinGecko로 폴백합니다. 계속 실패하면 약관·네트워크를 확인하세요."
                )
                log.error(f"HTTP 451 | {url} | {res.text[:300]}")
                return None
            else:
                log.error(f"HTTP {res.status_code} | {url} | {res.text[:200]}")
                return None
        except requests.RequestException as e:
            log.error(f"요청 오류 (시도 {attempt}/{retries}): {e}")
            time.sleep(5 * attempt)
    return None


# ══════════════════════════════════════════════════════
# Binance OHLCV
# ══════════════════════════════════════════════════════


def binance_fetch_klines(symbol: str, from_date: str | None = None) -> list[list]:
    """
    Binance spot 일봉 kline (호스트 순차: data.binance.com → vision → api…).
    from_date: 해당일 00:00 UTC부터. None이면 전체 구간.
    """
    start_time = date_to_ts_ms(from_date) if from_date else 0
    return fetch_klines_paginated(
        symbol, BINANCE_QUOTE, start_time, delay=BINANCE_DELAY
    )


def fetch_incremental_ohlcv_rows(
    symbol: str, cg_coin_id: str, from_date: str, today: str
) -> list[dict]:
    """Binance 전 호스트 실패 시 CoinGecko market_chart 로 폴백."""
    klines = binance_fetch_klines(symbol, from_date=from_date)
    if klines:
        return parse_binance_klines(klines)
    log.warning(
        "Binance kline 없음 → CoinGecko /coins/%s/market_chart (daily)",
        cg_coin_id,
    )
    return coingecko_fetch_daily_range(cg_coin_id, from_date, today)


def parse_binance_klines(klines: list[list]) -> list[dict]:
    return [
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
        for k in klines
    ]


# ══════════════════════════════════════════════════════
# DB 저장
# ══════════════════════════════════════════════════════


def save_rows_supabase(supabase, coin_id: str, rows: list[dict]) -> int:
    if not rows:
        return 0

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
    for i in range(0, len(payload), chunk_size):
        supabase.table("ohlcv").upsert(
            payload[i : i + chunk_size],
            on_conflict="coin_id,date",
        ).execute()
    return len(payload)


# ══════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════


def main():
    today = today_utc()

    log.info("=" * 55)
    log.info("암호화폐 OHLCV 업데이트 시작 (USDT 페어)")
    log.info("  MODE : supabase")
    log.info("  Target: supabase")
    log.info(f"  오늘 : {today}")
    log.info("=" * 55)

    supabase = get_supabase_client()

    # ── DB에서 코인 목록 조회 ────────────────────────
    coins = get_coins_from_supabase(supabase)

    if not coins:
        log.error("coins 테이블에 데이터가 없습니다. 먼저 코인 목록을 등록하세요.")
        return

    log.info(f"\n업데이트 대상: {len(coins)}개 코인\n")

    # ── 코인별 증분 업데이트 ─────────────────────────
    skipped = 0
    updated = 0

    for i, coin in enumerate(coins, 1):
        coin_id = coin["id"]
        symbol = coin["symbol"]
        last_date = get_last_date_supabase(supabase, coin_id)

        log.info(f"[{i}/{len(coins)}] {symbol} ({coin_id})")

        if not last_date:
            log.warning(f"  ohlcv 데이터 없음 → 건너뜀")
            skipped += 1
            continue

        from_date = next_date(last_date)

        if from_date > today:
            log.info(f"  이미 최신 상태 (마지막: {last_date}) → 건너뜀")
            skipped += 1
            continue

        log.info(f"  마지막: {last_date} → {from_date} ~ {today} 업데이트 중...")
        rows = fetch_incremental_ohlcv_rows(symbol, coin_id, from_date, today)

        if not rows:
            log.warning(f"  Binance/CoinGecko {symbol} 수신 데이터 없음")
            skipped += 1
            continue
        rows = [r for r in rows if r["date"] < today]  # 미완성 캔들 제외

        if not rows:
            log.info(f"  저장할 새 데이터 없음")
            skipped += 1
            continue

        saved = save_rows_supabase(supabase, coin_id, rows)
        log.info(f"  +{saved}일치 저장 ({rows[0]['date']} ~ {rows[-1]['date']})")
        updated += 1

    log.info("\n" + "=" * 55)
    log.info("업데이트 완료! Supabase 저장 완료")
    log.info(f"  업데이트: {updated}개 코인")
    log.info(f"  건너뜀  : {skipped}개 코인")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
