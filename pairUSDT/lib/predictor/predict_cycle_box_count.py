"""
BTC/알트 공통: 사이클별 Bear/Bull 박스 수 예측 (선형 회귀 + 가드).

- is_completed=1인 과거 사이클만 집계하여 cycle_number별 bear_count, bull_count 산출.
- 최소제곱법 선형 회귀로 다음 사이클 박스 수 예측 후, 명세의 가드 규칙 적용.
- 결과는 Bear/Bull 체인 상한(max_bear_chain, max_bull_chain)에 사용.
- coin_id를 넘기면 해당 코인 완성 사이클 기준, None이면 BTC(symbol) 기준(하위 호환).
"""

import sqlite3
from typing import NamedTuple

from lib.common.config import (
    BEAR_GUARD_DELTA,
    MAX_BEAR_CHAIN,
    MAX_BULL_CHAIN,
    MIN_BOX_COUNT,
)


class CyclePrediction(NamedTuple):
    """한 사이클에 대한 Bear/Bull 박스 수 예측 결과 (명세 반환 형식)."""
    cycle_number: int
    bear_count: int
    bull_count: int
    total_count: int
    method: str
    guard_applied: dict  # {"bear": bool, "bull": bool}


METHOD_LINEAR_REGRESSION = "linear_regression"


def get_completed_cycle_box_counts(
    conn: sqlite3.Connection, coin_id: int
) -> list[tuple[int, int, int]]:
    """
    is_completed=1인 해당 코인(coin_id) 사이클만 대상으로 cycle_number별 bear_count, bull_count 집계.
    반환: [(cycle_number, bear_count, bull_count), ...] 정렬된 리스트.
    """
    rows = conn.execute(
        """
        SELECT cycle_number,
               SUM(CASE WHEN UPPER(phase) = 'BEAR' THEN 1 ELSE 0 END) AS bear_count,
               SUM(CASE WHEN UPPER(phase) = 'BULL' THEN 1 ELSE 0 END) AS bull_count
        FROM coin_analysis_results
        WHERE coin_id = ? AND is_completed = 1
        GROUP BY cycle_number
        ORDER BY cycle_number
        """,
        (coin_id,),
    ).fetchall()
    return [(int(r[0]), int(r[1]), int(r[2])) for r in rows]


def get_btc_completed_cycle_box_counts(conn: sqlite3.Connection) -> list[tuple[int, int, int]]:
    """
    is_completed=1인 BTC 사이클만 대상으로 cycle_number별 bear_count, bull_count 집계.
    반환: [(cycle_number, bear_count, bull_count), ...] 정렬된 리스트.
    (하위 호환·테스트용: symbol 기준. 실전에서는 coin_id로 get_completed_cycle_box_counts 사용)
    """
    rows = conn.execute(
        """
        SELECT cycle_number,
               SUM(CASE WHEN UPPER(phase) = 'BEAR' THEN 1 ELSE 0 END) AS bear_count,
               SUM(CASE WHEN UPPER(phase) = 'BULL' THEN 1 ELSE 0 END) AS bull_count
        FROM coin_analysis_results
        WHERE UPPER(symbol) = 'BTC' AND is_completed = 1
        GROUP BY cycle_number
        ORDER BY cycle_number
        """
    ).fetchall()
    return [(int(r[0]), int(r[1]), int(r[2])) for r in rows]


def _linear_regression_predict(points: list[tuple[int, float]], next_x: int) -> float:
    """
    최소제곱법 선형 회귀: predict(next_x) = a * next_x + b.
    a = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²),  b = (Σy - a*Σx) / n.
    points: [(x, y), ...]. 빈 배열 또는 1개면 회귀 불가 → 0.0 반환(호출부에서 fallback).
    """
    if len(points) < 2:
        return 0.0
    n = len(points)
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_xx = sum(p[0] * p[0] for p in points)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.0
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    return a * next_x + b


def _apply_guards(
    raw_bear: float,
    raw_bull: float,
    prev_bear: int,
    prev_bull: int,
) -> tuple[int, int, bool, bool]:
    """
    예측값 보정: round 적용 후 Bear/Bull 가드.
    Bear 최솟값: max(round(raw), prev_bear - BEAR_GUARD_DELTA). Bull: max(round(raw), prev_bull).
    둘 다 MIN_BOX_COUNT 이상. 상한(MAX_BEAR_CHAIN/MAX_BULL_CHAIN)은 호출부에서 적용.
    """
    bear_rounded = max(MIN_BOX_COUNT, round(raw_bear))
    bull_rounded = max(MIN_BOX_COUNT, round(raw_bull))
    bear_floor = max(prev_bear - BEAR_GUARD_DELTA, MIN_BOX_COUNT)
    bull_floor = max(prev_bull, MIN_BOX_COUNT)
    bear_final = max(bear_rounded, bear_floor)
    bull_final = max(bull_rounded, bull_floor)
    guard_bear = bear_final != bear_rounded
    guard_bull = bull_final != bull_rounded
    return bear_final, bull_final, guard_bear, guard_bull


def predict_cycle_box_counts(
    conn: sqlite3.Connection,
    target_cycle_number: int,
    coin_id: int | None = None,
) -> CyclePrediction | None:
    """
    target_cycle_number에 대한 Bear/Bull 박스 수 예측.
    coin_id가 주어지면 해당 코인의 완성 사이클 기준, None이면 BTC(symbol) 기준.
    완성된 사이클이 2개 미만이면 회귀 불가 → None 반환(fallback은 호출부에서 기존 상수 사용).
    """
    if coin_id is not None:
        counts = get_completed_cycle_box_counts(conn, coin_id)
    else:
        counts = get_btc_completed_cycle_box_counts(conn)
    if len(counts) < 2:
        return None
    max_cyc = max(c[0] for c in counts)
    prev_bear = next((c[1] for c in counts if c[0] == target_cycle_number - 1), MIN_BOX_COUNT)
    prev_bull = next((c[2] for c in counts if c[0] == target_cycle_number - 1), MIN_BOX_COUNT)

    if target_cycle_number <= max_cyc:
        observed = next((c for c in counts if c[0] == target_cycle_number), None)
        if observed is None:
            return None
        raw_bear, raw_bull = float(observed[1]), float(observed[2])
    else:
        points_bear = [(c[0], float(c[1])) for c in counts]
        points_bull = [(c[0], float(c[2])) for c in counts]
        for cyc in range(max_cyc + 1, target_cycle_number + 1):
            raw_bear = _linear_regression_predict(points_bear, cyc)
            raw_bull = _linear_regression_predict(points_bull, cyc)
            bear_count, bull_count, guard_bear, guard_bull = _apply_guards(
                raw_bear, raw_bull, prev_bear, prev_bull
            )
            if cyc < target_cycle_number:
                points_bear.append((cyc, float(bear_count)))
                points_bull.append((cyc, float(bull_count)))
                prev_bear, prev_bull = bear_count, bull_count
        return CyclePrediction(
            cycle_number=target_cycle_number,
            bear_count=bear_count,
            bull_count=bull_count,
            total_count=bear_count + bull_count,
            method=METHOD_LINEAR_REGRESSION,
            guard_applied={"bear": guard_bear, "bull": guard_bull},
        )

    bear_count, bull_count, guard_bear, guard_bull = _apply_guards(
        raw_bear, raw_bull, prev_bear, prev_bull
    )
    return CyclePrediction(
        cycle_number=target_cycle_number,
        bear_count=bear_count,
        bull_count=bull_count,
        total_count=bear_count + bull_count,
        method=METHOD_LINEAR_REGRESSION,
        guard_applied={"bear": guard_bear, "bull": guard_bull},
    )
