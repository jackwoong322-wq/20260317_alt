"""BTC 투자 신호 통합 디스크립터.

Bear/Bull 단계 디스크립터를 통합하여 phase에 따라
자동으로 적합한 설명 메시지를 생성하는 단일 진입점.

주요 함수:
    describe_btc_signal — phase에 따라 Bear/Bull 디스크립터 자동 라우팅
    build_full_signal_description — 전체 정보 포함 통합 딕셔너리 반환
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def describe_btc_signal(signal_result, cycle_position) -> dict:
    """phase에 따라 Bear/Bull 디스크립터 자동 라우팅.

    Args:
        signal_result: btc_investment_signal.SignalResult | None
        cycle_position: btc_cycle_position.CyclePosition

    Returns:
        describe_bear_signal() 또는 describe_bull_signal() 반환값
    """
    try:
        progress = cycle_position.box_progress_ratio
        phase = cycle_position.phase

        if phase == "BEAR":
            from lib.predictor.bear_stage_descriptor import describe_bear_signal
            return describe_bear_signal(signal_result, progress)
        else:
            from lib.predictor.bull_stage_descriptor import describe_bull_signal
            return describe_bull_signal(signal_result, progress)

    except Exception as e:
        log.error("[btc_signal_descriptor] 설명 생성 실패: %s", e)
        return {
            "stage": 0, "stage_name": "알 수 없음",
            "signal": "WATCH", "action": "관망",
            "message_ko": "신호 생성 중 오류가 발생했습니다.",
            "message_en": "Error generating signal description.",
            "confidence": 0.0, "color": "#636e72", "emoji": "❓",
            "reason": [str(e)], "box_progress_ratio": 0.0,
        }


def build_full_signal_description(
    df,
    cycle_number: int,
    phase: str,
    current_price_pct: float,
    box_lo: float,
    box_hi: float,
    target_price_pct: float,
    near_target_threshold_pct: float = 15.0,
) -> dict:
    """전체 파이프라인: DataFrame → 신호 + 설명 통합.

    Returns:
        {
            "symbol": "BTC",
            "cycle_number": ...,
            "phase": ...,
            "signal": { ... },       # signal_to_dict()
            "display": { ... },      # SIGNAL_DISPLAY
            "description": { ... },  # describe_btc_signal()
            "cycle_position": { ... }
        }
    """
    try:
        from lib.predictor.btc_signal_payload import build_btc_signal_response
        from lib.predictor.btc_signal_adapter import build_cycle_position_from_df
        from lib.predictor.btc_investment_signal import generate_btc_signal

        pos = build_cycle_position_from_df(
            df=df, cycle_number=cycle_number, phase=phase,
            current_price_pct=current_price_pct,
            box_lo=box_lo, box_hi=box_hi,
            target_price_pct=target_price_pct,
            near_target_threshold_pct=near_target_threshold_pct,
        )
        signal_result = generate_btc_signal(pos)
        payload = build_btc_signal_response(
            df=df, cycle_number=cycle_number, phase=phase,
            current_price_pct=current_price_pct,
            box_lo=box_lo, box_hi=box_hi,
            target_price_pct=target_price_pct,
        )
        description = describe_btc_signal(signal_result, pos)
        payload["description"] = description
        payload["phase"] = phase
        return payload

    except Exception as e:
        log.error("[btc_signal_descriptor] 전체 빌드 실패: %s", e)
        return {"error": str(e), "signal": {"signal": "WATCH"}}
