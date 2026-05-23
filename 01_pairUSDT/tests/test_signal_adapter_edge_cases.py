"""Tests for btc_signal_adapter additional edge cases — Iteration 27.

calc_avg_cycle_days_historical의 빈 DF 처리 및
calc_elapsed_days 경계 조건 추가 테스트.
"""

import unittest
import pandas as pd

from lib.predictor.btc_signal_adapter import (
    calc_avg_cycle_days_historical,
    calc_elapsed_days,
)


def _btc_row(cycle, phase, box_index, start_x, end_x, is_completed=1, is_prediction=0):
    return {
        "symbol": "BTC", "cycle_number": cycle, "phase": phase,
        "box_index": box_index, "start_x": start_x, "end_x": end_x,
        "is_completed": is_completed, "is_prediction": is_prediction,
    }


class TestCalcAvgCycleDaysHistorical(unittest.TestCase):

    def test_correct_avg_days(self):
        """과거 2사이클 평균 일수 계산."""
        df = pd.DataFrame([
            _btc_row(3, "BEAR", 0, 100, 200),   # cy3: 101일
            _btc_row(3, "BEAR", 1, 201, 300),   # cy3: 계속 (100~300 = 201일)
            _btc_row(4, "BEAR", 0, 400, 500),   # cy4: 400~500 = 101일
        ])
        avg = calc_avg_cycle_days_historical(df, current_cycle=5, phase="BEAR")
        # cy3: 300-100+1=201, cy4: 500-400+1=101 → avg=151
        self.assertAlmostEqual(avg, 151.0)

    def test_empty_returns_bear_fallback(self):
        avg = calc_avg_cycle_days_historical(pd.DataFrame(), 5, "BEAR")
        self.assertAlmostEqual(avg, 180.0)

    def test_empty_returns_bull_fallback(self):
        avg = calc_avg_cycle_days_historical(pd.DataFrame(), 5, "BULL")
        self.assertAlmostEqual(avg, 365.0)

    def test_min_cycles_fallback(self):
        """1사이클만 있으면 fallback."""
        df = pd.DataFrame([_btc_row(4, "BEAR", 0, 100, 200)])
        avg = calc_avg_cycle_days_historical(df, current_cycle=5, phase="BEAR", min_cycles=2)
        self.assertAlmostEqual(avg, 180.0)


class TestCalcElapsedDaysExtended(unittest.TestCase):

    def test_single_box(self):
        """박스 1개 → end_x - start_x + 1."""
        df = pd.DataFrame([_btc_row(5, "BEAR", 0, 100, 150)])
        self.assertEqual(calc_elapsed_days(df, 5, "BEAR"), 51)

    def test_multiple_boxes_spans_full(self):
        """여러 박스 → 전체 범위."""
        df = pd.DataFrame([
            _btc_row(5, "BEAR", 0, 100, 150),
            _btc_row(5, "BEAR", 1, 151, 200),
        ])
        self.assertEqual(calc_elapsed_days(df, 5, "BEAR"), 101)

    def test_wrong_phase_returns_zero(self):
        """다른 phase → 0."""
        df = pd.DataFrame([_btc_row(5, "BULL", 0, 100, 150)])
        self.assertEqual(calc_elapsed_days(df, 5, "BEAR"), 0)


if __name__ == "__main__":
    unittest.main()
