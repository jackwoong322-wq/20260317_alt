"""
ZECUSDT daily OHLCV collector.

Fetches ZECUSDT candles from Binance and stores them in Supabase tables:
- coins
- ohlcv
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from lib.common.binance_public import fetch_klines_paginated, spot_get_first_working
from lib.common.config import BINANCE_DELAY, SUPABASE_ANON_KEY, SUPABASE_URL

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _SCRIPT_DIR.parent
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_SCRIPT_DIR / ".env", override=False)

BINANCE_QUOTE = "USDT"
TARGET_COIN = {
    "id": "zcash",
    "symbol": "ZEC",
    "name": "Zcash",
    "rank": 999,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("collector_zec_usdt.log"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL/SUPABASE_ANON_KEY is not configured.")
    try:
        from supabase import create_client
    except ImportError as exc:
        raise ImportError(
            "Failed to import supabase. Install dependencies with "
            "`pip install -r requirements.txt` or `pip install supabase PyJWT`."
        ) from exc
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def ts_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def binance_has_usdt_symbol(symbol: str) -> bool:
    data, _used_base = spot_get_first_working("/api/v3/exchangeInfo", None)
    if not data:
        raise RuntimeError("Failed to fetch Binance exchangeInfo.")

    pair = f"{symbol.upper()}{BINANCE_QUOTE}"
    for item in data.get("symbols", []):
        if item.get("symbol") == pair and item.get("status") == "TRADING":
            return True
    return False


def binance_fetch_all_klines(symbol: str) -> list[list]:
    return fetch_klines_paginated(symbol, BINANCE_QUOTE, 0, delay=BINANCE_DELAY)


def parse_binance_klines(klines: list[list]) -> list[dict]:
    rows = []
    for kline in klines:
        rows.append(
            {
                "date": ts_to_date(kline[0]),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume_base": float(kline[5]),
                "volume_quote": float(kline[7]),
                "trade_count": int(kline[8]),
                "source": "binance",
            }
        )
    return rows


def save_coin_supabase(supabase, coin: dict) -> None:
    payload = {
        "id": coin["id"],
        "symbol": coin["symbol"],
        "name": coin["name"],
        "rank": coin["rank"],
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    supabase.table("coins").upsert(payload, on_conflict="id").execute()


def save_rows_supabase(supabase, coin_id: str, rows: list[dict]) -> tuple[int, int]:
    if not rows:
        return 0, 0

    payload = [
        {
            "coin_id": coin_id,
            "date": row["date"],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume_base": row["volume_base"],
            "volume_quote": row["volume_quote"],
            "trade_count": row["trade_count"],
            "source": row["source"],
        }
        for row in rows
    ]

    chunk_size = 500
    batch_count = 0
    for index in range(0, len(payload), chunk_size):
        batch_count += 1
        supabase.table("ohlcv").upsert(
            payload[index : index + chunk_size],
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


def main() -> None:
    coin = TARGET_COIN
    coin_id = coin["id"]
    symbol = coin["symbol"]

    log.info("=" * 55)
    log.info("ZECUSDT Binance collector start")
    log.info("Mode   : supabase")
    log.info("Source : Binance")
    log.info(f"Target : {symbol}{BINANCE_QUOTE}")
    log.info("=" * 55)

    supabase = get_supabase_client()

    if not binance_has_usdt_symbol(symbol):
        log.error(f"Binance trading pair not found or not trading: {symbol}{BINANCE_QUOTE}")
        return

    save_coin_supabase(supabase, coin)

    log.info(f"Fetching Binance klines: {symbol}{BINANCE_QUOTE}")
    klines = binance_fetch_all_klines(symbol)
    rows = parse_binance_klines(klines)

    if not rows:
        log.warning(f"No Binance OHLCV rows found for {symbol}{BINANCE_QUOTE}")
        return

    before_count = get_ohlcv_count_supabase(supabase, coin_id)
    saved_count, batch_count = save_rows_supabase(supabase, coin_id, rows)
    after_count = get_ohlcv_count_supabase(supabase, coin_id)
    reflected_count = max(0, after_count - before_count)

    log.info(f"Requested rows : {saved_count}")
    log.info(f"Batch count    : {batch_count}")
    log.info(f"Inserted delta : {reflected_count}")
    log.info(f"Date range     : {rows[0]['date']} ~ {rows[-1]['date']}")
    log.info("=" * 55)
    log.info("ZECUSDT Binance collector complete")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
