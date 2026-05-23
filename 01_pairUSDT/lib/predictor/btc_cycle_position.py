"""BTC 사이클 내 박스 진행률 및 위치 계산 모듈.

현재 사이클에서 BTC가 Bear/Bull 박스권의 몇 번째 단계에 있는지를 계산하고,
과거 사이클 대비 진행률(0.0~1.0)을 반환한다.

주요 함수:
    calc_bear_box_progress  — Bear 박스 진행률 계산
    calc_bull_box_progress  — Bull 박스 진행률 계산
    calc_price_position     — 현재가격의 박스권 내 위치 (0=하단, 1=상단)
    calc_btc_cycle_position — 통합 포지션 계산 (단일 진입점)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class CyclePosition:
    """BTC 사이클 내 현재 위치 정보."""

    phase: str                     # "BEAR" | "BULL"
    cycle_number: int
    completed_boxes: int           # 현재 사이클에서 완료된 박스 수
    avg_boxes_historical: float    # 과거 사이클 평균 박스 수
    box_progress_ratio: float      # 박스 진행률: completed / avg (0~1, 1 이상 가능)
    day_progress_ratio: float      # 일수 진행률: elapsed_days / avg_cycle_days (0~1)
    price_position: float          # 현재가격의 박스권 내 위치 (0=하단, 1=상단)
    distance_to_target_pct: float  # 예측 목표가(bottom/peak)까지 남은 % 거리
    is_near_target: bool           # 목표가 근접 여부 (거리 < 15%)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """직렬화 가능한 dict 변환 (API 응답/로깅용)."""
        return {
            "phase": self.phase,
            "cycle_number": self.cycle_number,
            "completed_boxes": self.completed_boxes,
            "avg_boxes_historical": round(self.avg_boxes_historical, 2),
            "box_progress_ratio": round(self.box_progress_ratio, 4),
            "day_progress_ratio": round(self.day_progress_ratio, 4),
            "price_position": round(self.price_position, 4),
            "distance_to_target_pct": round(self.distance_to_target_pct, 4),
            "is_near_target": self.is_near_target,
        }



def calc_bear_box_progress(
    completed_bear_boxes: int,
    avg_bear_boxes: float,
) -> float:
    """Bear 박스 진행률 계산.

    Args:
        completed_bear_boxes: 현재 사이클에서 완료된 Bear 박스 수
        avg_bear_boxes: 과거 BTC Bear 사이클 평균 박스 수

    Returns:
        진행률 (0.0~1.0+). 1.0 초과면 평균 이상 진행.
    """
    if avg_bear_boxes <= 0:
        log.warning("[BTC pos] avg_bear_boxes=0, progress=0.0 fallback")
        return 0.0
    ratio = completed_bear_boxes / avg_bear_boxes
    return float(ratio)


def calc_bull_box_progress(
    completed_bull_boxes: int,
    avg_bull_boxes: float,
) -> float:
    """Bull 박스 진행률 계산.

    Args:
        completed_bull_boxes: 현재 사이클에서 완료된 Bull 박스 수
        avg_bull_boxes: 과거 BTC Bull 사이클 평균 박스 수

    Returns:
        진행률 (0.0~1.0+).
    """
    if avg_bull_boxes <= 0:
        log.warning("[BTC pos] avg_bull_boxes=0, progress=0.0 fallback")
        return 0.0
    ratio = completed_bull_boxes / avg_bull_boxes
    return float(ratio)


def calc_price_position(
    current_price_pct: float,
    box_lo: float,
    box_hi: float,
) -> float:
    """현재 가격(%)의 박스권 내 상대 위치 계산.

    Returns:
        0.0 = 하단(lo), 1.0 = 상단(hi). 범위 밖은 클리핑.
    """
    if box_hi <= box_lo:
        return 0.5
    ratio = (current_price_pct - box_lo) / (box_hi - box_lo)
    return float(max(0.0, min(1.0, ratio)))


def calc_distance_to_target(
    current_price_pct: float,
    target_price_pct: float,
) -> float:
    """현재가 대비 목표가까지의 거리 (%).

    Bear면 target = bottom_lo (하락 목표)
    Bull이면 target = peak_hi (상승 목표)

    Returns:
        양수: 목표가가 현재가보다 위 (상승 여지)
        음수: 목표가가 현재가보다 아래 (하락 여지)
        0.0: current_price_pct이 0에 가까울 때 fallback
    """
    if abs(current_price_pct) < 1e-6:
        return 0.0
    return (target_price_pct - current_price_pct) / abs(current_price_pct) * 100.0


def calc_btc_cycle_position(
    phase: str,
    cycle_number: int,
    completed_boxes: int,
    avg_boxes_historical: float,
    elapsed_days: int,
    avg_cycle_days: float,
    current_price_pct: float,
    box_lo: float,
    box_hi: float,
    target_price_pct: float,
    near_target_threshold_pct: float = 15.0,
) -> CyclePosition:
    """BTC 사이클 위치 통합 계산.

    Args:
        phase: "BEAR" 또는 "BULL"
        cycle_number: 현재 사이클 번호
        completed_boxes: 완료된 박스 수
        avg_boxes_historical: 과거 평균 박스 수
        elapsed_days: 현재 사이클 경과 일수
        avg_cycle_days: 과거 평균 사이클 일수
        current_price_pct: 현재 가격 (정규화 %)
        box_lo: 현재 박스 하단
        box_hi: 현재 박스 상단
        target_price_pct: 예측 목표가 (Bear=bottom_lo, Bull=peak_hi)
        near_target_threshold_pct: 목표가 근접 판단 임계값 (기본 15%)

    Returns:
        CyclePosition 구조체
    """
    if phase == "BEAR":
        box_progress = calc_bear_box_progress(completed_boxes, avg_boxes_historical)
    else:
        box_progress = calc_bull_box_progress(completed_boxes, avg_boxes_historical)

    day_progress = float(elapsed_days / avg_cycle_days) if avg_cycle_days > 0 else 0.0
    day_progress = max(0.0, min(1.5, day_progress))  # 1.5 이상은 클리핑

    price_pos = calc_price_position(current_price_pct, box_lo, box_hi)
    distance = calc_distance_to_target(current_price_pct, target_price_pct)
    is_near = abs(distance) < near_target_threshold_pct

    log.info(
        "[BTC pos] phase=%s cy=%d boxes=%d/%.1f(%.0f%%) days=%d/%.0f(%.0f%%) "
        "price_pos=%.2f dist_to_target=%.1f%% near=%s",
        phase, cycle_number, completed_boxes, avg_boxes_historical, box_progress * 100,
        elapsed_days, avg_cycle_days, day_progress * 100,
        price_pos, distance, is_near,
    )

    return CyclePosition(
        phase=phase,
        cycle_number=cycle_number,
        completed_boxes=completed_boxes,
        avg_boxes_historical=avg_boxes_historical,
        box_progress_ratio=box_progress,
        day_progress_ratio=day_progress,
        price_position=price_pos,
        distance_to_target_pct=distance,
        is_near_target=is_near,
    )
