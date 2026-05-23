"""Tests for predict_peak.py — Iteration 5."""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from lib.predictor.predict_peak import (
    _compute_btc_peak_from_hist,
    calc_peak_hybrid_for_coin,
    calc_peak_btc,
    calc_peak_alt,
)


def _make_hist(rows):
    """rows: list of (cycle_number, box_index, hi, hi_day, end_x, phase)"""
    return pd.DataFrame(rows, columns=["cycle_number", "box_index", "hi", "hi_day", "end_x", "phase"])


def _make_last(end_x=100, symbol="BTC"):
    return pd.Series({"end_x": end_x, "symbol": symbol, "coin_id": 1})


class TestComputeBtcPeakFromHist(unittest.TestCase):

    def test_returns_none_for_single_cycle(self):
        """사이클이 1개면 비율 계산 불가 → None 반환."""
        hist = _make_hist([(1, 0, 50.0, 200, 200, "BULL")])
        last = _make_last(end_x=50)
        result = _compute_btc_peak_from_hist(hist, last)
        # 7-tuple, first two elements should be None
        self.assertIsNone(result[0])
        self.assertIsNone(result[1])

    def test_returns_none_for_empty_ratios(self):
        """log_prev <= 1e-6 이면 ratios 빔 → None 반환."""
        hist = _make_hist([
            (1, 0, 0.0, 100, 100, "BULL"),
            (2, 0, 0.0, 200, 200, "BULL"),
        ])
        last = _make_last(end_x=50)
        result = _compute_btc_peak_from_hist(hist, last)
        self.assertIsNone(result[0])

    def test_two_cycles_returns_peak_hi(self):
        """2사이클이면 비율 1개로 peak_hi 계산 가능."""
        hist = _make_hist([
            (1, 0, 100.0, 200, 200, "BULL"),
            (2, 0, 200.0, 400, 400, "BULL"),
        ])
        last = _make_last(end_x=50)
        peak_hi, peak_day, cyc_hi_rows, weights, weighted_avg_ratio, _, count = (
            _compute_btc_peak_from_hist(hist, last)
        )
        self.assertIsNotNone(peak_hi)
        self.assertGreater(peak_hi, 0)
        self.assertEqual(count, 2)

    def test_peak_day_lower_bound(self):
        """peak_day는 항상 last['end_x'] + 2 이상."""
        hist = _make_hist([
            (1, 0, 100.0, 5, 5, "BULL"),
            (2, 0, 200.0, 8, 8, "BULL"),
        ])
        last = _make_last(end_x=1000)
        peak_hi, peak_day, *_ = _compute_btc_peak_from_hist(hist, last)
        if peak_day is not None:
            self.assertGreaterEqual(peak_day, 1000 + 2)

    def test_three_cycles_weighted_avg(self):
        """3사이클: 가중 평균 비율 계산 검증."""
        hist = _make_hist([
            (1, 0, 100.0, 200, 200, "BULL"),
            (2, 0, 200.0, 400, 400, "BULL"),
            (3, 0, 300.0, 600, 600, "BULL"),
        ])
        last = _make_last(end_x=10)
        peak_hi, peak_day, cyc_hi_rows, weights, _, _, count = (
            _compute_btc_peak_from_hist(hist, last)
        )
        self.assertEqual(count, 3)
        self.assertIsNotNone(peak_hi)
        # 가중치는 [1, 2] — 최신 사이클에 더 높은 가중치
        self.assertEqual(weights, [1, 2])

    def test_returns_seven_tuple(self):
        """반환값이 항상 7-tuple."""
        hist = _make_hist([(1, 0, 50.0, 100, 100, "BULL")])
        last = _make_last()
        result = _compute_btc_peak_from_hist(hist, last)
        self.assertEqual(len(result), 7)


class TestCalcPeakHybridForCoin(unittest.TestCase):

    def _make_df_all(self):
        return pd.DataFrame([
            {"coin_id": 1, "cycle_number": 1, "box_index": 0, "hi": 100.0,
             "hi_day": 200, "end_x": 200, "phase": "BULL"},
            {"coin_id": 1, "cycle_number": 2, "box_index": 0, "hi": 200.0,
             "hi_day": 400, "end_x": 400, "phase": "BULL"},
        ])

    def test_empty_hist_returns_none(self):
        """해당 coin_id / phase 데이터 없으면 (None, None)."""
        df_all = self._make_df_all()
        last = _make_last(end_x=50, symbol="BTC")
        # coin_id=99 → hist.empty
        peak_hi, peak_day = calc_peak_hybrid_for_coin(
            df_all, coin_id=99, max_cyc=3, last=last, cross_median=None, label="TEST"
        )
        self.assertIsNone(peak_hi)
        self.assertIsNone(peak_day)

    def test_cross_median_none_uses_self_ratio(self):
        """cross_median=None이면 self_ratio만 사용."""
        df_all = self._make_df_all()
        last = _make_last(end_x=50, symbol="BTC")
        peak_hi, peak_day = calc_peak_hybrid_for_coin(
            df_all, coin_id=1, max_cyc=3, last=last, cross_median=None, label="BTC"
        )
        # 2사이클 있으므로 결과 반환 가능
        self.assertIsNotNone(peak_hi)

    def test_cross_median_blends_ratios(self):
        """cross_median이 있으면 0.5 블렌딩 적용."""
        df_all = self._make_df_all()
        last = _make_last(end_x=50, symbol="BTC")
        peak_hi_with, _ = calc_peak_hybrid_for_coin(
            df_all, coin_id=1, max_cyc=3, last=last, cross_median=0.75, label="BTC"
        )
        peak_hi_without, _ = calc_peak_hybrid_for_coin(
            df_all, coin_id=1, max_cyc=3, last=last, cross_median=None, label="BTC"
        )
        # cross_median이 다르면 결과도 달라야 함
        if peak_hi_with is not None and peak_hi_without is not None:
            self.assertNotAlmostEqual(peak_hi_with, peak_hi_without, places=3)

    def test_calc_peak_btc_delegates(self):
        """calc_peak_btc는 calc_peak_hybrid_for_coin 의 래퍼."""
        df_all = self._make_df_all()
        last = _make_last(end_x=50, symbol="BTC")
        r1 = calc_peak_btc(df_all, max_cyc=3, last=last, coin_id=1, cross_median=None)
        r2 = calc_peak_hybrid_for_coin(
            df_all, coin_id=1, max_cyc=3, last=last, cross_median=None, label="BTC"
        )
        self.assertEqual(r1, r2)


class TestCalcPeakAlt(unittest.TestCase):

    def test_no_model_returns_none(self):
        """peak_models가 비어있으면 모두 None."""
        X_pred = pd.DataFrame([{"f": 1}])
        last = _make_last(symbol="ALT")
        peak_hi, peak_day, pb, pt = calc_peak_alt(
            peak_models={}, peak_group="ALT_BEAR", X_pred=X_pred, last=last
        )
        self.assertIsNone(peak_hi)
        self.assertIsNone(peak_day)
        self.assertIsNone(pb)
        self.assertIsNone(pt)

    def test_fallback_group_used(self):
        """요청한 그룹 없으면 fallback 그룹(ALT_BEAR/ALT_BULL) 사용."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [5.0]
        mock_model.predict_proba.return_value = [[0.4, 0.6]]
        last = _make_last(symbol="UNKNOWN")
        last["end_x"] = 10
        X_pred = pd.DataFrame([{"f": 1}])
        peak_models = {
            "ALT_BEAR": {
                "peak_hi": mock_model,
                "peak_day": mock_model,
                "trend": mock_model,
            }
        }
        peak_hi, peak_day, pb, pt = calc_peak_alt(
            peak_models=peak_models,
            peak_group="NONEXISTENT_GROUP",
            X_pred=X_pred,
            last=last,
        )
        self.assertIsNotNone(peak_hi)


if __name__ == "__main__":
    unittest.main()
