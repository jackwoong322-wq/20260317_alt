"""BTC 투자 신호 신뢰도 점수 보정 모듈.

SignalResult의 기본 confidence를 추가 조건으로 보정한다.
- 연속 같은 신호 횟수(consecutive_count) 기반 보너스
- day_progress와 box_progress 일관성 기반 페널티
- is_near_target 조건 기반 보너스

주요 함수:
    adjust_confidence_by_history  — 히스토리 기반 신뢰도 조정
    adjust_confidence_by_position — 위치 일관성 기반 신뢰도 조정
    compute_final_confidence      — 최종 신뢰도 계산
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# 상수
CONSECUTIVE_BONUS_PER_COUNT = 0.05   # 연속 신호당 보너스
MAX_CONSECUTIVE_BONUS = 0.20          # 최대 연속 보너스
NEAR_TARGET_BONUS = 0.10              # 목표 근접 시 보너스
INCONSISTENCY_PENALTY = 0.10          # 일관성 불일치 시 페널티
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0


def adjust_confidence_by_history(
    base_confidence: float,
    consecutive_count: int,
    is_signal_changed: bool,
) -> float:
    """히스토리 기반 신뢰도 조정.

    - 연속 같은 신호: 횟수당 5% 보너스 (최대 20%)
    - 신호 변화 직후: 10% 페널티 (불확실성)

    Args:
        base_confidence: 기본 신뢰도
        consecutive_count: 연속 같은 신호 횟수
        is_signal_changed: 직전 신호에서 변화 여부

    Returns:
        조정된 신뢰도 (0~1 클리핑)
    """
    adjusted = base_confidence

    # 연속 보너스 (신호 변화 직후가 아닐 때만)
    if not is_signal_changed and consecutive_count > 1:
        bonus = min(
            (consecutive_count - 1) * CONSECUTIVE_BONUS_PER_COUNT,
            MAX_CONSECUTIVE_BONUS,
        )
        adjusted += bonus
        log.debug("[scorer] consecutive_bonus=+%.2f (count=%d)", bonus, consecutive_count)

    # 신호 변화 직후 페널티
    if is_signal_changed:
        adjusted -= INCONSISTENCY_PENALTY
        log.debug("[scorer] change_penalty=-%.2f", INCONSISTENCY_PENALTY)

    return float(max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, adjusted)))


def adjust_confidence_by_position(
    base_confidence: float,
    box_progress_ratio: float,
    day_progress_ratio: float,
    is_near_target: bool,
    phase: str,
) -> float:
    """위치 일관성 기반 신뢰도 조정.

    Bear: box_progress와 day_progress가 일치할수록 보너스
    Bull: 동일
    is_near_target=True: 추가 보너스

    Args:
        base_confidence: 기본 신뢰도
        box_progress_ratio: CyclePosition.box_progress_ratio
        day_progress_ratio: CyclePosition.day_progress_ratio
        is_near_target: 목표가 근접 여부
        phase: "BEAR" | "BULL"

    Returns:
        조정된 신뢰도 (0~1 클리핑)
    """
    adjusted = base_confidence

    # day_progress와 box_progress 일관성 (차이가 클수록 페널티)
    progress_diff = abs(box_progress_ratio - day_progress_ratio)
    if progress_diff > 0.3:
        penalty = min(progress_diff - 0.3, INCONSISTENCY_PENALTY)
        adjusted -= penalty
        log.debug("[scorer] inconsistency_penalty=-%.2f (diff=%.2f)", penalty, progress_diff)

    # 목표가 근접 보너스
    if is_near_target:
        adjusted += NEAR_TARGET_BONUS
        log.debug("[scorer] near_target_bonus=+%.2f", NEAR_TARGET_BONUS)

    return float(max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, adjusted)))


def compute_final_confidence(
    base_confidence: float,
    consecutive_count: int,
    is_signal_changed: bool,
    box_progress_ratio: float,
    day_progress_ratio: float,
    is_near_target: bool,
    phase: str,
) -> float:
    """최종 신뢰도 계산 (히스토리 + 위치 보정 복합).

    Returns:
        최종 신뢰도 (0.0~1.0)
    """
    step1 = adjust_confidence_by_history(
        base_confidence, consecutive_count, is_signal_changed
    )
    step2 = adjust_confidence_by_position(
        step1, box_progress_ratio, day_progress_ratio, is_near_target, phase
    )
    log.info(
        "[scorer] base=%.3f → history=%.3f → final=%.3f (phase=%s cy_count=%d near=%s)",
        base_confidence, step1, step2, phase, consecutive_count, is_near_target,
    )
    return round(step2, 4)
