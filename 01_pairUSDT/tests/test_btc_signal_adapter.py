"""Tests for btc_signal_adapter.py — Iteration 11.

DataFrame에서 BTC 완료 박스 수·평균 박스 수·경과 일수를 추출하는
어댑터 함수들의 단위 테스트.
외부 DB 호출 없이 pandas DataFrame mock으로 검증.
"""

import unittest
import pandas as pd

from lib.predictor.btc_signal_adapter import (
    extract_completed_boxes,
    calc_avg_boxes_historical,
    calc_elapsed_days,
    calc_avg_cycle_days_historical,
    build_cycle_position_from_df,
)
from lib.predictor.btc_cycle_position import CyclePosition


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _btc_row(cycle, phase, box_index, start_x, end_x, is_completed=1, is_prediction=0, symbol="BTC"):
    return {
        "symbol": symbol, "cycle_number": cycle, "phase": phase,
        "box_index": box_index, "start_x": start_x, "end_x": end_x,
        "is_completed": is_completed, "is_prediction": is_prediction,
    }


class TestExtractCompletedBoxes(unittest.TestCase):

    def test_counts_completed_boxes(self):
        """완료된 Bear 박스만 카운트."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150),
            _btc_row(5, "BEAR", 1, 151, 200),
            _btc_row(5, "BEAR", 2, 201, 250, is_completed=0),  # 미완료 제외
        ])
        count = extract_completed_boxes(df, cycle_number=5, phase="BEAR")
        self.assertEqual(count, 2)

    def test_excludes_predictions(self):
        """is_prediction=1은 제외."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150, is_prediction=0),
            _btc_row(5, "BEAR", 1, 151, 200, is_prediction=1),  # 예측값 제외
        ])
        count = extract_completed_boxes(df, cycle_number=5, phase="BEAR")
        self.assertEqual(count, 1)

    def test_excludes_other_phase(self):
        """다른 phase는 카운트 안 함."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150),
            _btc_row(5, "BULL", 0, 100, 150),  # Bull 제외
        ])
        count = extract_completed_boxes(df, cycle_number=5, phase="BEAR")
        self.assertEqual(count, 1)

    def test_excludes_other_cycle(self):
        """다른 사이클 박스는 제외."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150),
            _btc_row(4, "BEAR", 0, 50, 90),  # 이전 사이클 제외
        ])
        count = extract_completed_boxes(df, cycle_number=5, phase="BEAR")
        self.assertEqual(count, 1)

    def test_empty_df_returns_zero(self):
        df = _make_df([])
        count = extract_completed_boxes(df, cycle_number=5, phase="BEAR")
        self.assertEqual(count, 0)

    def test_excludes_non_btc(self):
        """ETH 등 다른 코인은 제외."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150, symbol="ETH"),
        ])
        count = extract_completed_boxes(df, cycle_number=5, phase="BEAR")
        self.assertEqual(count, 0)


class TestCalcAvgBoxesHistorical(unittest.TestCase):

    def test_correct_average(self):
        """과거 2사이클 박스 수 평균 계산."""
        df = _make_df([
            _btc_row(3, "BEAR", 0, 100, 150),
            _btc_row(3, "BEAR", 1, 151, 200),   # cy3: 2박스
            _btc_row(4, "BEAR", 0, 200, 250),
            _btc_row(4, "BEAR", 1, 251, 300),
            _btc_row(4, "BEAR", 2, 301, 350),   # cy4: 3박스
        ])
        avg = calc_avg_boxes_historical(df, current_cycle=5, phase="BEAR")
        self.assertAlmostEqual(avg, 2.5)  # (2+3)/2

    def test_empty_returns_fallback_bear(self):
        """데이터 없으면 Bear fallback=3.0."""
        df = _make_df([])
        avg = calc_avg_boxes_historical(df, current_cycle=5, phase="BEAR")
        self.assertAlmostEqual(avg, 3.0)

    def test_empty_returns_fallback_bull(self):
        """데이터 없으면 Bull fallback=5.0."""
        df = _make_df([])
        avg = calc_avg_boxes_historical(df, current_cycle=5, phase="BULL")
        self.assertAlmostEqual(avg, 5.0)

    def test_current_cycle_excluded(self):
        """current_cycle 자신은 계산에서 제외."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150),  # 현재 사이클 제외되어야 함
            _btc_row(5, "BEAR", 1, 151, 200),
            _btc_row(4, "BEAR", 0, 50, 90),    # 과거 사이클: 1박스
            _btc_row(3, "BEAR", 0, 10, 40),    # 과거 사이클: 1박스
        ])
        avg = calc_avg_boxes_historical(df, current_cycle=5, phase="BEAR")
        self.assertAlmostEqual(avg, 1.0)

    def test_min_cycles_fallback(self):
        """사이클 수 < min_cycles이면 fallback."""
        df = _make_df([
            _btc_row(4, "BEAR", 0, 50, 90),   # 과거 1사이클만
        ])
        avg = calc_avg_boxes_historical(df, current_cycle=5, phase="BEAR", min_cycles=2)
        self.assertAlmostEqual(avg, 3.0)  # fallback


class TestCalcElapsedDays(unittest.TestCase):

    def test_correct_elapsed(self):
        """경과 일수 = end_x 최대 - start_x 최소 + 1."""
        df = _make_df([
            _btc_row(5, "BEAR", 0, 100, 150),
            _btc_row(5, "BEAR", 1, 151, 200),
        ])
        days = calc_elapsed_days(df, cycle_number=5, phase="BEAR")
        self.assertEqual(days, 200 - 100 + 1)

    def test_empty_returns_zero(self):
        df = _make_df([])
        self.assertEqual(calc_elapsed_days(df, 5, "BEAR"), 0)


class TestBuildCyclePositionFromDf(unittest.TestCase):

    def _make_btc_df(self):
        return _make_df([
            # 과거 cy3 BEAR: 3박스, 일수 100~250
            _btc_row(3, "BEAR", 0, 100, 150),
            _btc_row(3, "BEAR", 1, 151, 200),
            _btc_row(3, "BEAR", 2, 201, 250),
            # 과거 cy4 BEAR: 2박스, 일수 300~400
            _btc_row(4, "BEAR", 0, 300, 350),
            _btc_row(4, "BEAR", 1, 351, 400),
            # 현재 cy5 BEAR: 1박스 완료
            _btc_row(5, "BEAR", 0, 500, 550),
        ])

    def test_returns_cycle_position(self):
        df = self._make_btc_df()
        pos = build_cycle_position_from_df(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=25.0, box_lo=20.0, box_hi=40.0, target_price_pct=18.0,
        )
        self.assertIsInstance(pos, CyclePosition)
        self.assertEqual(pos.phase, "BEAR")

    def test_completed_boxes_extracted(self):
        """완료 박스 수가 올바르게 추출됨."""
        df = self._make_btc_df()
        pos = build_cycle_position_from_df(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=25.0, box_lo=20.0, box_hi=40.0, target_price_pct=18.0,
        )
        self.assertEqual(pos.completed_boxes, 1)

    def test_avg_boxes_computed(self):
        """과거 평균 박스 수: (3+2)/2 = 2.5."""
        df = self._make_btc_df()
        pos = build_cycle_position_from_df(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=25.0, box_lo=20.0, box_hi=40.0, target_price_pct=18.0,
        )
        self.assertAlmostEqual(pos.avg_boxes_historical, 2.5)


if __name__ == "__main__":
    unittest.main()
