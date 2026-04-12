"""
Binance spot 공개 API: 호스트 순차 시도.
1순위는 config 의 BINANCE_REST_BASE_CHAIN[0] (기본 https://data.binance.com).
data.binance.com 은 /api/v3 가 없어 404 → data-api.binance.vision 등으로 자동 폴백.
"""

from __future__ import annotations

import logging
import time

import requests

from lib.common.config import BINANCE_DELAY, BINANCE_REST_BASE_CHAIN

log = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _get_json(url: str, params: dict | None) -> dict | list | None:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            res = requests.get(url, params=params, timeout=30)
            if res.status_code == 200:
                return res.json()
            if res.status_code == 429:
                wait = 60 * attempt
                log.warning("Binance rate limit → %s초 대기 후 재시도", wait)
                time.sleep(wait)
                continue
            if res.status_code == 451:
                log.warning(
                    "HTTP 451 (지역 제한) %s — 다음 Binance 호스트 시도",
                    url[:72],
                )
                return None
            if res.status_code == 404:
                log.debug("HTTP 404 %s", url[:96])
                return None
            log.error("HTTP %s | %s | %s", res.status_code, url, res.text[:200])
            return None
        except requests.RequestException as e:
            log.error("Binance 요청 오류 (%s/%s): %s", attempt, _MAX_RETRIES, e)
            time.sleep(5 * attempt)
    return None


def spot_get_first_working(
    path: str, params: dict | None = None
) -> tuple[dict | list | None, str | None]:
    """path 예: /api/v3/klines — 첫 성공 호스트와 JSON 반환."""
    for base in BINANCE_REST_BASE_CHAIN:
        url = f"{base}{path}"
        data = _get_json(url, params)
        if data is not None:
            if base != BINANCE_REST_BASE_CHAIN[0]:
                log.info("Binance API 사용 호스트: %s", base)
            return data, base
    return None, None


def spot_get_same_base(
    base: str, path: str, params: dict | None = None
) -> dict | list | None:
    return _get_json(f"{base}{path}", params)


def fetch_klines_paginated(
    symbol: str, quote: str, start_ms: int = 0, delay: float | None = None
) -> list[list]:
    """일봉 kline 전부. 첫 페이지에서 성공한 호스트로 이후 페이지만 요청."""
    path = "/api/v3/klines"
    sym = f"{symbol}{quote}"
    wait = BINANCE_DELAY if delay is None else delay
    base: str | None = None
    start_time = start_ms
    all_klines: list[list] = []

    while True:
        params = {
            "symbol": sym,
            "interval": "1d",
            "startTime": start_time,
            "limit": 1000,
        }
        if base:
            data = spot_get_same_base(base, path, params)
        else:
            data, base = spot_get_first_working(path, params)
            if not base:
                return []

        time.sleep(wait)

        if not data:
            break

        all_klines.extend(data)

        if len(data) < 1000:
            break

        start_time = data[-1][6] + 1

    return all_klines
