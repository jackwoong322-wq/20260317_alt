"""Iter 37: predict_peak.py 순수함수 추가 엣지케이스 테스트."""

import unittest
import pandas as pd
import numpy as np
from lib.predictor.predict_peak import _compute_btc_peak_from_hist


def _last_series(end_x=500):
    return pd.Series({"end_x": end_x, "symbol": "BTC", "cycle_number": 5})


def _make_bull_hist(cycles_hi: list[tuple[int, float, int]]) -> pd.DataFrame:
    """(cycle_number, hi, hi_day) 리스트 → DataFrame."""
    rows = []
    for cn, hi, hi_day in cycles_hi:
        rows.append({
            "cycle_number": cn, "hi": hi, "hi_day": hi_day,
            "end_x": hi_day + 10, "phase": "BULL",
        })
    return pd.DataFrame(rows)


class TestComputeBtcPeakFromHist(unittest.TestCase):

    def test_single_cycle_returns_none(self):
        hist = _make_bull_hist([(1, 50.0, 100)])
        result = _compute_btc_peak_from_hist(hist, _last_series())
        # 사이클 2개 미만 → 첫 반환값(peak_hi) None
        self.assertIsNone(result[0])

    def test_empty_df_returns_none(self):
        # 빈 DataFrame — _compute_btc_peak_from_hist는 groupby에서 아무것도 처리 못함
        empty = pd.DataFrame(columns=["cycle_number", "hi", "hi_day", "end_x", "phase"])
        result = _compute_btc_peak_from_hist(empty, _last_series())
        self.assertIsNone(result[0])


    def test_two_cycles_returns_positive_peak(self):
        hist = _make_bull_hist([(1, 40.0, 100), (2, 60.0, 150)])
        result = _compute_btc_peak_from_hist(hist, _last_series(end_x=200))
        peak_hi = result[0]
        self.assertIsNotNone(peak_hi)
        self.assertGreater(peak_hi, 0)

    def test_peak_day_after_end_x(self):
        """peak_day_pred는 last[end_x]+2 이상이어야 한다."""
        hist = _make_bull_hist([(1, 30.0, 50), (2, 45.0, 80)])
        last = _last_series(end_x=200)
        result = _compute_btc_peak_from_hist(hist, last)
        peak_day = result[1]
        if peak_day is not None:
            self.assertGreaterEqual(peak_day, 202)

    def test_three_cycles_weighted_ratio(self):
        """세 사이클이면 가중 비율이 적용되어야 한다."""
        hist = _make_bull_hist([
            (1, 20.0, 100), (2, 35.0, 200), (3, 55.0, 320)
        ])
        result = _compute_btc_peak_from_hist(hist, _last_series(end_x=400))
        peak_hi, peak_day, cyc_hi_rows, weights, ratio, _, count = result
        self.assertIsNotNone(peak_hi)
        self.assertEqual(count, 3)

    def test_count_matches_cycles(self):
        hist = _make_bull_hist([(1, 25.0, 80), (2, 38.0, 160), (3, 52.0, 250)])
        result = _compute_btc_peak_from_hist(hist, _last_series())
        self.assertEqual(result[-1], 3)  # len(cyc_hi_rows)

    def test_peak_hi_positive(self):
        hist = _make_bull_hist([(1, 10.0, 50), (2, 18.0, 100)])
        result = _compute_btc_peak_from_hist(hist, _last_series(end_x=150))
        if result[0] is not None:
            self.assertGreater(result[0], 0)

    def test_weights_exponential(self):
        """weights는 2^i 형태여야 한다."""
        hist = _make_bull_hist([(1, 20.0, 100), (2, 35.0, 200), (3, 55.0, 300)])
        result = _compute_btc_peak_from_hist(hist, _last_series(end_x=350))
        weights = result[3]
        if weights:
            expected = [2**i for i in range(len(weights))]
            self.assertEqual(list(weights), expected)


if __name__ == "__main__":
    unittest.main()
