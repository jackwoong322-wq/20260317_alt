"""BTC 투자 신호 페이로드 직렬화 모듈.

SignalResult를 FastAPI 응답 또는 Supabase 저장용 dict로 변환한다.

주요 함수:
    signal_to_dict        — SignalResult → dict
    signal_to_api_payload — API 응답용 표준 포맷 생성
    build_btc_signal_response — 전체 파이프라인: df + 메타 → API payload
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

# 신호별 표시 텍스트 (한국어)
SIGNAL_DISPLAY = {
    "ACCUMULATE": {"label": "매수 적극", "color": "#00b894", "icon": "📈"},
    "WATCH":      {"label": "관망",      "color": "#fdcb6e", "icon": "👀"},
    "CAUTION":    {"label": "주의",      "color": "#e17055", "icon": "⚠️"},
    "EXIT":       {"label": "매도 준비", "color": "#d63031", "icon": "📉"},
}


def signal_to_dict(signal_result) -> dict[str, Any]:
    """SignalResult → 직렬화 가능한 dict 변환.

    Returns:
        {
            "signal": "ACCUMULATE",
            "phase": "BEAR",
            "confidence": 0.85,
            "reason": [...],
            "box_progress_ratio": 0.75,
            "price_position": 0.2,
            "distance_to_target_pct": -8.5,
            "is_near_target": True,
        }
    """
    if signal_result is None:
        return {}
    return {
        "signal": signal_result.signal,
        "phase": signal_result.phase,
        "confidence": round(float(signal_result.confidence), 4),
        "reason": list(signal_result.reason),
        "box_progress_ratio": round(float(signal_result.box_progress_ratio), 4),
        "price_position": round(float(signal_result.price_position), 4),
        "distance_to_target_pct": round(float(signal_result.distance_to_target_pct), 4),
        "is_near_target": bool(signal_result.is_near_target),
    }


def signal_to_api_payload(
    signal_result,
    cycle_number: int,
    symbol: str = "BTC",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """API 응답용 표준 포맷 생성.

    Returns:
        {
            "symbol": "BTC",
            "cycle_number": 5,
            "generated_at": "2026-05-20T14:00:00Z",
            "signal": { ... signal_to_dict() ... },
            "display": { "label": "매수 적극", "color": "#00b894", "icon": "📈" }
        }
    """
    if generated_at is None:
        generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    base = signal_to_dict(signal_result)
    signal_key = base.get("signal", "WATCH")
    display = SIGNAL_DISPLAY.get(signal_key, SIGNAL_DISPLAY["WATCH"])

    return {
        "symbol": str(symbol).upper(),
        "cycle_number": int(cycle_number),
        "generated_at": generated_at,
        "signal": base,
        "display": display,
    }


def build_btc_signal_response(
    df,
    cycle_number: int,
    phase: str,
    current_price_pct: float,
    box_lo: float,
    box_hi: float,
    target_price_pct: float,
    near_target_threshold_pct: float = 15.0,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """전체 파이프라인: DataFrame + 메타 정보 → API payload.

    Args:
        df: coin_analysis_results DataFrame
        cycle_number: 현재 BTC 사이클 번호
        phase: "BEAR" | "BULL"
        current_price_pct: 현재 BTC 가격 (%)
        box_lo: 현재 박스 하단
        box_hi: 현재 박스 상단
        target_price_pct: 예측 목표가 (Bear=bottom_lo, Bull=peak_hi)
        near_target_threshold_pct: 근접 판단 임계값
        generated_at: 타임스탬프 (None이면 현재 UTC)

    Returns:
        API payload dict
    """
    try:
        from lib.predictor.btc_signal_adapter import build_cycle_position_from_df
        from lib.predictor.btc_investment_signal import generate_btc_signal

        pos = build_cycle_position_from_df(
            df=df,
            cycle_number=cycle_number,
            phase=phase,
            current_price_pct=current_price_pct,
            box_lo=box_lo,
            box_hi=box_hi,
            target_price_pct=target_price_pct,
            near_target_threshold_pct=near_target_threshold_pct,
        )
        signal_result = generate_btc_signal(pos)
        payload = signal_to_api_payload(
            signal_result, cycle_number=cycle_number, generated_at=generated_at
        )
        payload["cycle_position"] = {
            "completed_boxes": pos.completed_boxes,
            "avg_boxes_historical": round(pos.avg_boxes_historical, 2),
            "box_progress_ratio": round(pos.box_progress_ratio, 4),
            "day_progress_ratio": round(pos.day_progress_ratio, 4),
            "price_position": round(pos.price_position, 4),
        }
        return payload

    except Exception as e:
        log.error("[btc_signal_payload] 빌드 실패: %s", e)
        return {
            "symbol": "BTC",
            "cycle_number": cycle_number,
            "error": str(e),
            "signal": {"signal": "WATCH", "phase": phase, "confidence": 0.0, "reason": [str(e)]},
            "display": SIGNAL_DISPLAY["WATCH"],
        }
