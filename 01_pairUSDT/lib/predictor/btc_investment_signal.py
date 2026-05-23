"""BTC 투자 타이밍 신호 생성기.

CyclePosition 데이터를 입력받아 Bear/Bull 사이클 단계별
투자 액션 신호를 4단계로 분류한다.

신호 정의:
    ACCUMULATE — Bear 후반 저점 근처: 적극 분할 매수 구간
    WATCH      — 방향 미결·중반: 관망, 소규모 포지션 유지
    CAUTION    — Bull 후반 고점 임박: 비중 축소 준비
    EXIT       — 사이클 피크 임박: 매도/완전 청산 준비

주요 함수:
    classify_bear_signal — Bear 사이클 신호 분류
    classify_bull_signal — Bull 사이클 신호 분류
    generate_btc_signal  — 통합 신호 생성 (단일 진입점)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_signal_confidence_scorer import compute_final_confidence

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────
# 신호 상수
# ────────────────────────────────────────────────
SIGNAL_ACCUMULATE = "ACCUMULATE"
SIGNAL_WATCH = "WATCH"
SIGNAL_CAUTION = "CAUTION"
SIGNAL_EXIT = "EXIT"

# Bear 신호 임계값
BEAR_ACCUMULATE_BOX_PROGRESS_MIN = 0.6   # 박스 60% 이상 진행
BEAR_ACCUMULATE_PRICE_POSITION_MAX = 0.35  # 박스 하단 35% 이내
BEAR_ACCUMULATE_NEAR_TARGET = True        # 목표(bottom) 근처여야 함

BEAR_WATCH_BOX_PROGRESS_MIN = 0.3        # 박스 30% 이상이면 Watch

# Bull 신호 임계값
BULL_EXIT_BOX_PROGRESS_MIN = 0.8         # 박스 80% 이상 진행
BULL_EXIT_PRICE_POSITION_MIN = 0.75      # 박스 상단 75% 이상
BULL_EXIT_NEAR_TARGET = True             # 목표(peak) 근처여야 함

BULL_CAUTION_BOX_PROGRESS_MIN = 0.6     # 박스 60% 이상이면 Caution
BULL_CAUTION_PRICE_POSITION_MIN = 0.5   # 박스 중간 이상


@dataclass
class SignalResult:
    """투자 타이밍 신호 결과."""

    signal: str                  # ACCUMULATE | WATCH | CAUTION | EXIT
    phase: str                   # BEAR | BULL
    confidence: float            # 0.0~1.0 (신호 강도)
    reason: list[str]            # 신호 판정 이유
    box_progress_ratio: float    # 박스 진행률
    price_position: float        # 박스권 내 가격 위치
    distance_to_target_pct: float  # 목표가까지 거리 %
    is_near_target: bool


def classify_bear_signal(pos: CyclePosition) -> SignalResult:
    """Bear 사이클 신호 분류.

    판단 로직:
    - ACCUMULATE: 박스 진행률 >= 60% AND 가격이 하단 35% 이내 AND 목표(bottom) 근접
    - WATCH (초기): 박스 진행률 30~60% 또는 방향 불확실
    - WATCH (일반): 그 외
    """
    reasons: list[str] = []
    progress = pos.box_progress_ratio
    price_pos = pos.price_position
    day_prog = pos.day_progress_ratio

    # 평균 초과 케이스: 박스 수가 이미 역사 평균을 넘음 → 매수 시기일 가능성
    if progress > 1.0 and day_prog >= 0.7:
        reasons.append(f"box_progress={progress:.0%} > 100% (평균 초과)")
        reasons.append(f"day_progress={day_prog:.0%} >= 70% → 역사적 매수 구간 가능")
        confidence = min(1.0, 0.75 + (progress - 1.0) * 0.5)
        return SignalResult(
            signal=SIGNAL_ACCUMULATE,
            phase="BEAR",
            confidence=round(confidence, 3),
            reason=reasons,
            box_progress_ratio=progress,
            price_position=price_pos,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )


    if (
        progress >= BEAR_ACCUMULATE_BOX_PROGRESS_MIN
        and price_pos <= BEAR_ACCUMULATE_PRICE_POSITION_MAX
        and pos.is_near_target
    ):
        reasons.append(f"box_progress={progress:.0%} >= 60%")
        reasons.append(f"price_position={price_pos:.2f} <= 35%(하단 근처)")
        reasons.append("near_bottom=True")
        confidence = min(1.0, progress * (1.0 - price_pos) * 1.5)
        return SignalResult(
            signal=SIGNAL_ACCUMULATE,
            phase="BEAR",
            confidence=round(confidence, 3),
            reason=reasons,
            box_progress_ratio=progress,
            price_position=price_pos,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )

    # ACCUMULATE (목표 도달 임박하지 않아도 박스 후반+하단)
    if progress >= BEAR_ACCUMULATE_BOX_PROGRESS_MIN and price_pos <= BEAR_ACCUMULATE_PRICE_POSITION_MAX:
        reasons.append(f"box_progress={progress:.0%} >= 60%")
        reasons.append(f"price_position={price_pos:.2f} 하단 35% 이내")
        reasons.append("near_bottom=False (신중 매수)")
        confidence = min(0.7, progress * (1.0 - price_pos))
        return SignalResult(
            signal=SIGNAL_ACCUMULATE,
            phase="BEAR",
            confidence=round(confidence, 3),
            reason=reasons,
            box_progress_ratio=progress,
            price_position=price_pos,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )

    # WATCH
    if progress >= BEAR_WATCH_BOX_PROGRESS_MIN:
        reasons.append(f"box_progress={progress:.0%} 30~60% → 관망")
    else:
        reasons.append(f"box_progress={progress:.0%} < 30% → Bear 초입, 관망")

    return SignalResult(
        signal=SIGNAL_WATCH,
        phase="BEAR",
        confidence=0.5,
        reason=reasons,
        box_progress_ratio=progress,
        price_position=price_pos,
        distance_to_target_pct=pos.distance_to_target_pct,
        is_near_target=pos.is_near_target,
    )


def classify_bull_signal(pos: CyclePosition) -> SignalResult:
    """Bull 사이클 신호 분류.

    판단 로직:
    - EXIT:    박스 진행률 >= 80% AND 가격 상단 75% 이상 AND 목표(peak) 근접
    - EXIT(강력): 박스 평균 초과(>100%) AND 일수 진행률 >= 80%
    - CAUTION: 박스 진행률 >= 60% AND 가격 중간 이상
    - WATCH:   그 외 Bull 초중반
    """
    reasons: list[str] = []
    progress = pos.box_progress_ratio
    price_pos = pos.price_position
    day_prog = pos.day_progress_ratio

    # Bull 평균 초과 케이스: 릤도 시기 강력 표시
    if progress > 1.0 and day_prog >= 0.8:
        reasons.append(f"box_progress={progress:.0%} > 100% (평균 초과)")
        reasons.append(f"day_progress={day_prog:.0%} >= 80% → 역사적 정점 근반 가능")
        confidence = min(1.0, 0.85 + (progress - 1.0) * 0.5)
        return SignalResult(
            signal=SIGNAL_EXIT,
            phase="BULL",
            confidence=round(confidence, 3),
            reason=reasons,
            box_progress_ratio=progress,
            price_position=price_pos,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )

    # EXIT 조건
    if (
        progress >= BULL_EXIT_BOX_PROGRESS_MIN
        and price_pos >= BULL_EXIT_PRICE_POSITION_MIN
        and pos.is_near_target
    ):
        reasons.append(f"box_progress={progress:.0%} >= 80%")
        reasons.append(f"price_position={price_pos:.2f} >= 75%(상단 근체)")
        reasons.append("near_peak=True")
        confidence = min(1.0, progress * price_pos * 1.2)
        return SignalResult(
            signal=SIGNAL_EXIT,
            phase="BULL",
            confidence=round(confidence, 3),
            reason=reasons,
            box_progress_ratio=progress,
            price_position=price_pos,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )

    # CAUTION 조건
    if progress >= BULL_CAUTION_BOX_PROGRESS_MIN and price_pos >= BULL_CAUTION_PRICE_POSITION_MIN:
        reasons.append(f"box_progress={progress:.0%} >= 60%")
        reasons.append(f"price_position={price_pos:.2f} >= 50%(중상단)")
        confidence = min(0.8, progress * price_pos)
        return SignalResult(
            signal=SIGNAL_CAUTION,
            phase="BULL",
            confidence=round(confidence, 3),
            reason=reasons,
            box_progress_ratio=progress,
            price_position=price_pos,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )

    # WATCH
    reasons.append(f"box_progress={progress:.0%} Bull 초중반 → 관망 유지")
    return SignalResult(
        signal=SIGNAL_WATCH,
        phase="BULL",
        confidence=0.4,
        reason=reasons,
        box_progress_ratio=progress,
        price_position=price_pos,
        distance_to_target_pct=pos.distance_to_target_pct,
        is_near_target=pos.is_near_target,
    )


def generate_btc_signal(
    pos: CyclePosition,
    consecutive_count: int = 1,
    is_signal_changed: bool = False,
) -> SignalResult:
    """BTC 사이클 위치로부터 투자 타이밍 신호 생성.

    신뢰도 보정기(btc_signal_confidence_scorer)를 통합하여
    히스토리 연속성과 위치 일관성을 반영한 최종 confidence를 계산한다.

    Args:
        pos: btc_cycle_position.calc_btc_cycle_position() 반환값
        consecutive_count: 연속 동일 신호 횟수 (기본 1)
        is_signal_changed: 직전 신호에서 변화 여부 (기본 False)

    Returns:
        SignalResult — signal, confidence(보정됨), reason 포함
    """
    try:
        if pos.phase == "BEAR":
            result = classify_bear_signal(pos)
        else:
            result = classify_bull_signal(pos)

        # 신뢰도 보정 적용
        adjusted_confidence = compute_final_confidence(
            base_confidence=result.confidence,
            consecutive_count=consecutive_count,
            is_signal_changed=is_signal_changed,
            box_progress_ratio=pos.box_progress_ratio,
            day_progress_ratio=pos.day_progress_ratio,
            is_near_target=pos.is_near_target,
            phase=pos.phase,
        )
        result.confidence = adjusted_confidence

        log.info(
            "[BTC signal] phase=%s cy=%d signal=%s confidence=%.3f(조정) "
            "box_prog=%.0f%% price_pos=%.2f dist=%.1f%% near=%s",
            result.phase, pos.cycle_number, result.signal, result.confidence,
            result.box_progress_ratio * 100, result.price_position,
            result.distance_to_target_pct, result.is_near_target,
        )
        return result

    except Exception as e:
        log.error("[BTC signal] 신호 생성 실패: %s → WATCH fallback", e)
        return SignalResult(
            signal=SIGNAL_WATCH,
            phase=pos.phase,
            confidence=0.0,
            reason=[f"error: {e}"],
            box_progress_ratio=pos.box_progress_ratio,
            price_position=pos.price_position,
            distance_to_target_pct=pos.distance_to_target_pct,
            is_near_target=pos.is_near_target,
        )
