"""BTC 투자 신호 시스템 공개 API 모음.

이 모듈은 BTC 투자 신호 파이프라인의
공개 진입점을 모두 노출한다.

사용 예:
    from lib.predictor.btc_signal_api import btc_investment_pipeline

    result = btc_investment_pipeline(
        df=your_dataframe,
        cycle_number=5,
        phase="BEAR",
        current_price_pct=20.0,
        box_lo=18.0,
        box_hi=35.0,
        target_price_pct=17.0,
    )
    # result["signal"]["signal"] → "ACCUMULATE"
    # result["description"]["message_ko"] → "Bear 후반입니다..."
    # result["validation"]["is_valid"] → True
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def btc_investment_pipeline(
    df,
    cycle_number: int,
    phase: str,
    current_price_pct: float,
    box_lo: float,
    box_hi: float,
    target_price_pct: float,
    near_target_threshold_pct: float = 15.0,
    generated_at: str | None = None,
    consecutive_count: int = 1,
    is_signal_changed: bool = False,
) -> dict:
    """BTC 투자 신호 전체 파이프라인.

    DataFrame → CyclePosition → SignalResult → 설명 + 검증 포함 전체 결과.

    Args:
        df: coin_analysis_results DataFrame
        cycle_number: 현재 BTC 사이클 번호
        phase: "BEAR" | "BULL"
        current_price_pct: 현재 BTC 정규화 가격 (%)
        box_lo: 현재 박스 하단 (%)
        box_hi: 현재 박스 상단 (%)
        target_price_pct: 예측 목표가 (Bear=bottom_lo, Bull=peak_hi)
        near_target_threshold_pct: 목표가 근접 임계값 (기본 15%)
        generated_at: 타임스탬프 (None이면 현재 UTC)
        consecutive_count: 연속 동일 신호 횟수 (기본 1, scorer 보정용)
        is_signal_changed: 직전 신호에서 변화 여부 (기본 False, scorer 보정용)

    Returns:
        {
            "symbol": "BTC",
            "cycle_number": ...,
            "phase": ...,
            "signal": { signal, phase, confidence, reason, ... },
            "display": { label, color, icon },
            "description": { stage, stage_name, action, message_ko, message_en, ... },
            "cycle_position": { completed_boxes, avg_boxes_historical, ... },
            "validation": { is_valid, errors, warnings }
        }
    """
    try:
        from lib.predictor.btc_signal_descriptor import build_full_signal_description
        from lib.predictor.btc_signal_adapter import build_cycle_position_from_df
        from lib.predictor.btc_investment_signal import generate_btc_signal
        from lib.predictor.btc_signal_validator import validate_signal_result

        # 1. 사이클 위치 계산
        pos = build_cycle_position_from_df(
            df=df, cycle_number=cycle_number, phase=phase,
            current_price_pct=current_price_pct,
            box_lo=box_lo, box_hi=box_hi,
            target_price_pct=target_price_pct,
            near_target_threshold_pct=near_target_threshold_pct,
        )

        # 2. 신호 생성 (신뢰도 보정 파라미터 전달)
        signal_result = generate_btc_signal(
            pos,
            consecutive_count=consecutive_count,
            is_signal_changed=is_signal_changed,
        )

        # 3. 검증
        validation = validate_signal_result(signal_result)

        # 4. 전체 설명 빌드
        payload = build_full_signal_description(
            df=df, cycle_number=cycle_number, phase=phase,
            current_price_pct=current_price_pct,
            box_lo=box_lo, box_hi=box_hi,
            target_price_pct=target_price_pct,
        )

        # 5. 검증 결과 추가
        payload["validation"] = {
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }

        log.info(
            "[btc_api] pipeline complete: cy=%d phase=%s signal=%s valid=%s consec=%d",
            cycle_number, phase,
            payload.get("signal", {}).get("signal", "?"),
            validation.is_valid,
            consecutive_count,
        )
        return payload

    except Exception as e:
        log.error("[btc_api] pipeline failed: %s", e)
        return {
            "symbol": "BTC",
            "cycle_number": cycle_number,
            "phase": phase,
            "error": str(e),
            "signal": {"signal": "WATCH", "phase": phase, "confidence": 0.0},
            "display": {"label": "오류", "color": "#636e72", "icon": "❓"},
            "description": {
                "stage": 0, "signal": "WATCH", "message_ko": f"오류: {e}",
                "message_en": f"Error: {e}",
            },
            "validation": {"is_valid": False, "errors": [str(e)], "warnings": []},
        }


def get_signal_summary(pipeline_result: dict) -> str:
    """btc_investment_pipeline 결과에서 단일 라인 요약 문자열 생성.

    Args:
        pipeline_result: btc_investment_pipeline() 반환값

    Returns:
        예: "[BEAR cy=5] ACCUMULATE (conf=0.82) — Bear 후반입니다."
    """
    try:
        phase = pipeline_result.get("phase", "?")
        cy = pipeline_result.get("cycle_number", "?")
        sig = pipeline_result.get("signal", {}).get("signal", "?")
        conf = pipeline_result.get("signal", {}).get("confidence", 0.0)
        msg_ko = pipeline_result.get("description", {}).get("message_ko", "")
        return f"[{phase} cy={cy}] {sig} (conf={conf:.2f}) — {msg_ko}"
    except Exception as e:
        log.error("[btc_api] get_signal_summary 실패: %s", e)
        return f"[ERROR] {e}"

