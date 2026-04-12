"""
CoinGecko 공개 API로 일봉 수준 OHLCV 근사 (market_chart, interval=daily).

무료 티어는 통상 최대 365일. 가격만 있으므로 open=high=low=close=종가로 둠.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests

from lib.common.config import COINGECKO_API_BASE, COINGECKO_DELAY

log = logging.getLogger(__name__)

_MAX_RETRIES = 3


def ts_ms_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _cg_get(url: str, params: dict[str, Any]) -> dict | None:
    headers: dict[str, str] = {}
    # Pro / Demo 키가 있으면 전달 (환경에 맞게 하나만 설정해도 됨)
    for key_name, header_name in (
        ("COINGECKO_PRO_API_KEY", "x-cg-pro-api-key"),
        ("COINGECKO_DEMO_API_KEY", "x-cg-demo-api-key"),
    ):
        v = os.getenv(key_name)
        if v:
            headers[header_name] = v
            break

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            res = requests.get(url, params=params, headers=headers or None, timeout=45)
            if res.status_code == 200:
                return res.json()
            if res.status_code == 429:
                wait = 60 * attempt
                log.warning("CoinGecko rate limit → %s초 대기", wait)
                time.sleep(wait)
                continue
            log.error("CoinGecko HTTP %s | %s | %s", res.status_code, url, res.text[:240])
            return None
        except requests.RequestException as e:
            log.error("CoinGecko 요청 오류 (%s/%s): %s", attempt, _MAX_RETRIES, e)
            time.sleep(5 * attempt)
    return None


def _volumes_by_date(total_volumes: list[list]) -> dict[str, float]:
    m: dict[str, float] = {}
    for t_ms, vol in total_volumes or []:
        d = ts_ms_to_date(int(t_ms))
        m[d] = float(vol)
    return m


def market_chart_to_rows(data: dict) -> list[dict]:
    """market_chart JSON → ohlcv 행 (종가 기준, 거래량 USD)."""
    vol_by_date = _volumes_by_date(data.get("total_volumes") or [])
    rows: list[dict] = []
    for t_ms, price in data.get("prices") or []:
        d = ts_ms_to_date(int(t_ms))
        p = float(price)
        rows.append(
            {
                "date": d,
                "open": p,
                "high": p,
                "low": p,
                "close": p,
                "volume_base": 0.0,
                "volume_quote": vol_by_date.get(d, 0.0),
                "trade_count": 0,
                "source": "coingecko",
            }
        )
    rows.sort(key=lambda r: r["date"])
    return rows


def fetch_market_chart_daily(cg_id: str, days: int) -> list[dict]:
    """
    GET /coins/{id}/market_chart?vs_currency=usd&days=&interval=daily
    days: 1~365 (무료 티어 권장 상한)
    """
    safe_days = min(365, max(int(days), 1))
    url = f"{COINGECKO_API_BASE}/coins/{quote(cg_id, safe='')}/market_chart"
    params = {"vs_currency": "usd", "days": safe_days, "interval": "daily"}
    time.sleep(COINGECKO_DELAY)
    raw = _cg_get(url, params)
    if not raw:
        return []
    return market_chart_to_rows(raw)


def fetch_daily_range(cg_id: str, from_date: str, before_date: str) -> list[dict]:
    """
    from_date 이상, before_date 미만만 반환 (before_date: 미완성 일봉 제외용).
    요청 폭에 맞춰 days 산출 (최대 365).
    """
    fd = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    bd = datetime.strptime(before_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    span = max((bd - fd).days + 5, 1)
    days = min(365, span)
    rows = fetch_market_chart_daily(cg_id, days)
    return [r for r in rows if from_date <= r["date"] < before_date]


def fetch_recent_daily(cg_id: str, days: int = 365) -> list[dict]:
    """최근 N일 (전체 백필용, 무료 티어는 365 상한)."""
    return fetch_market_chart_daily(cg_id, min(days, 365))
