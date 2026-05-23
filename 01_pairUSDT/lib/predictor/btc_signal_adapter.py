"""BTC 신호 어댑터 — DataFrame → CyclePosition 자동 변환.

실제 coin_analysis_results DataFrame에서 BTC 현재 사이클의
완료 박스 수, 과거 평균 박스 수 등을 계산하여
CyclePosition 구조체로 변환한다.

주요 함수:
    extract_completed_boxes     — 현재 사이클 완료 박스 수 추출
    calc_avg_boxes_historical   — 과거 BTC 사이클 평균 박스 수 계산
    build_cycle_position_from_df — DataFrame → CyclePosition 변환 (단일 진입점)
"""

from __future__ import annotations

import logging

import pandas as pd

from lib.predictor.btc_cycle_position import calc_btc_cycle_position, CyclePosition

log = logging.getLogger(__name__)

BTC_SYMBOL = "BTC"


def extract_completed_boxes(
    df: pd.DataFrame,
    cycle_number: int,
    phase: str,
) -> int:
    """현재 사이클에서 완료된 BTC 박스 수 추출.

    Args:
        df: coin_analysis_results DataFrame (BTC 전체)
        cycle_number: 현재 사이클 번호
        phase: "BEAR" | "BULL"

    Returns:
        완료된 박스 수 (is_completed=1, is_prediction=0 기준)
    """
    if df.empty or "symbol" not in df.columns:
        return 0
    mask = (
        (df["symbol"].str.upper() == BTC_SYMBOL)
        & (df["cycle_number"] == cycle_number)
        & (df["phase"] == phase)
        & (df["is_completed"] == 1)
        & (df["is_prediction"] == 0)
    )
    count = int(mask.sum())
    log.debug("[adapter] cy=%d phase=%s completed_boxes=%d", cycle_number, phase, count)
    return count


def calc_avg_boxes_historical(
    df: pd.DataFrame,
    current_cycle: int,
    phase: str,
    min_cycles: int = 2,
) -> float:
    """과거 BTC 사이클(현재 사이클 제외)의 평균 박스 수 계산.

    Args:
        df: coin_analysis_results DataFrame (BTC 전체)
        current_cycle: 현재 사이클 번호 (제외 대상)
        phase: "BEAR" | "BULL"
        min_cycles: 최소 사이클 수 (이하면 fallback 반환)

    Returns:
        과거 완료 사이클의 평균 박스 수. 데이터 부족 시 3.0 (Bear) / 5.0 (Bull) fallback.
    """
    fallback = 3.0 if phase == "BEAR" else 5.0

    if df.empty or "symbol" not in df.columns:
        log.info("[adapter] 과거 %s 데이터 없음 → fallback=%.1f", phase, fallback)
        return fallback

    hist = df[
        (df["symbol"].str.upper() == BTC_SYMBOL)
        & (df["cycle_number"] < current_cycle)
        & (df["phase"] == phase)
        & (df["is_completed"] == 1)
        & (df["is_prediction"] == 0)
    ]
    if hist.empty:
        log.info("[adapter] 과거 %s 데이터 없음 → fallback=%.1f", phase, fallback)
        return fallback

    boxes_per_cycle = hist.groupby("cycle_number")["box_index"].count()
    if len(boxes_per_cycle) < min_cycles:
        log.info(
            "[adapter] 과거 %s 사이클 %d개 < min=%d → fallback=%.1f",
            phase, len(boxes_per_cycle), min_cycles, fallback,
        )
        return fallback

    avg = float(boxes_per_cycle.mean())
    log.info(
        "[adapter] phase=%s 과거 %d 사이클 평균 박스 수=%.2f (cycles=%s)",
        phase, len(boxes_per_cycle), avg, list(boxes_per_cycle.index),
    )
    return avg


def calc_elapsed_days(
    df: pd.DataFrame,
    cycle_number: int,
    phase: str,
) -> int:
    """현재 사이클 경과 일수 계산 (start_x 최소 ~ end_x 최대).

    Returns:
        경과 일수. 데이터 없으면 0.
    """
    if df.empty or "symbol" not in df.columns:
        return 0
    mask = (
        (df["symbol"].str.upper() == BTC_SYMBOL)
        & (df["cycle_number"] == cycle_number)
        & (df["phase"] == phase)
    )
    sub = df[mask]
    if sub.empty:
        return 0
    start = int(sub["start_x"].min())
    end = int(sub["end_x"].max())
    return max(0, end - start + 1)


def calc_avg_cycle_days_historical(
    df: pd.DataFrame,
    current_cycle: int,
    phase: str,
    min_cycles: int = 2,
) -> float:
    """과거 BTC 사이클 평균 일수 계산.

    Returns:
        평균 일수. 데이터 부족 시 180.0 (Bear) / 365.0 (Bull) fallback.
    """
    fallback = 180.0 if phase == "BEAR" else 365.0

    if df.empty or "symbol" not in df.columns:
        return fallback

    hist = df[
        (df["symbol"].str.upper() == BTC_SYMBOL)
        & (df["cycle_number"] < current_cycle)
        & (df["phase"] == phase)
        & (df["is_completed"] == 1)
        & (df["is_prediction"] == 0)
    ]
    if hist.empty:
        return fallback

    days_per_cycle = hist.groupby("cycle_number").apply(
        lambda g: int(g["end_x"].max()) - int(g["start_x"].min()) + 1,
        include_groups=False,
    )
    if len(days_per_cycle) < min_cycles:
        return fallback

    return float(days_per_cycle.mean())


def build_cycle_position_from_df(
    df: pd.DataFrame,
    cycle_number: int,
    phase: str,
    current_price_pct: float,
    box_lo: float,
    box_hi: float,
    target_price_pct: float,
    near_target_threshold_pct: float = 15.0,
) -> CyclePosition:
    """DataFrame에서 CyclePosition을 자동 생성하는 단일 진입점.

    Args:
        df: coin_analysis_results DataFrame (BTC 포함)
        cycle_number: 현재 사이클 번호
        phase: "BEAR" | "BULL"
        current_price_pct: 현재 BTC 정규화 가격 (%)
        box_lo: 현재 박스 하단 (%)
        box_hi: 현재 박스 상단 (%)
        target_price_pct: 예측 목표가 (Bear=bottom_lo, Bull=peak_hi)
        near_target_threshold_pct: 목표가 근접 임계값 (기본 15%)

    Returns:
        CyclePosition
    """
    completed = extract_completed_boxes(df, cycle_number, phase)
    avg_boxes = calc_avg_boxes_historical(df, cycle_number, phase)
    elapsed = calc_elapsed_days(df, cycle_number, phase)
    avg_days = calc_avg_cycle_days_historical(df, cycle_number, phase)

    return calc_btc_cycle_position(
        phase=phase,
        cycle_number=cycle_number,
        completed_boxes=completed,
        avg_boxes_historical=avg_boxes,
        elapsed_days=elapsed,
        avg_cycle_days=avg_days,
        current_price_pct=current_price_pct,
        box_lo=box_lo,
        box_hi=box_hi,
        target_price_pct=target_price_pct,
        near_target_threshold_pct=near_target_threshold_pct,
    )


def to_position_summary(pos: CyclePosition) -> str:
    """CyclePosition을 단일 라인 사람 읽기용 요약 문자열로 변환.

    Returns:
        예: "[BEAR cy=5] boxes=7/10.0(70%) price=0.25 near=True"
    """
    return (
        f"[{pos.phase} cy={pos.cycle_number}] "
        f"boxes={pos.completed_boxes}/{pos.avg_boxes_historical:.1f}"
        f"({pos.box_progress_ratio:.0%}) "
        f"price={pos.price_position:.2f} "
        f"near={pos.is_near_target}"
    )

