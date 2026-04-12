"""
Binance spot 공개 API: 호스트 순차 시도 및 프로세스 단위 캐시.

BINANCE_HOSTS 를 순서대로 시도하고, 첫 200 응답 호스트를 _working_host 에 캐시해
이후 kline 페이지 요청에 재사용한다.
"""

from __future__ import annotations

import logging
import time

import requests

from lib.common.config import BINANCE_DELAY, BINANCE_HOSTS, BINANCE_REST_BASE_CHAIN

log = logging.getLogger(__name__)

_MAX_RETRIES = 3

_working_host: str | None = None


def _get_working_host(symbol: str, quote: str) -> str | None:
    global _working_host
    if _working_host:
        return _working_host
    test_params = {"symbol": symbol + quote, "interval": "1d", "limit": 1}
    for host in BINANCE_REST_BASE_CHAIN:
        try:
            r = requests.get(
                f"{host.rstrip('/')}/api/v3/klines", params=test_params, timeout=10
            )
            if r.status_code == 200:
                _working_host = host.rstrip("/")
                return _working_host
        except Exception:
            continue
    return None


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
        b = base.rstrip("/")
        url = f"{b}{path}"
        data = _get_json(url, params)
        if data is not None:
            if b != BINANCE_HOSTS[0].rstrip("/"):
                log.info("Binance API 사용 호스트: %s", b)
            return data, b
    return None, None


def spot_get_same_base(
    base: str, path: str, params: dict | None = None
) -> dict | list | None:
    return _get_json(f"{base.rstrip('/')}{path}", params)


def _fetch_klines_page(host: str, params: dict) -> list | None:
    """단일 kline 페이지. 비정상 응답·예외 시 None (예외 전파 없음)."""
    url = f"{host.rstrip('/')}/api/v3/klines"
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data, list) else None
            if r.status_code == 429:
                time.sleep(60 * attempt)
                continue
        except Exception:
            if attempt == _MAX_RETRIES:
                return None
            time.sleep(5 * attempt)
    return None


def fetch_klines_paginated(
    symbol: str, quote: str, start_ms: int = 0, delay: float | None = None
) -> list[list]:
    """
    일봉 kline 전부. _get_working_host 로 확정한 호스트로 모든 페이지 요청.
    모든 호스트 실패 시 [].
    """
    sym = f"{symbol}{quote}"
    wait = BINANCE_DELAY if delay is None else delay
    host = _get_working_host(symbol, quote)
    if not host:
        return []

    start_time = start_ms
    all_klines: list[list] = []

    while True:
        params = {
            "symbol": sym,
            "interval": "1d",
            "startTime": start_time,
            "limit": 1000,
        }
        data = _fetch_klines_page(host, params)
        time.sleep(wait)

        if not data:
            break

        all_klines.extend(data)

        if len(data) < 1000:
            break

        start_time = data[-1][6] + 1

    return all_klines
