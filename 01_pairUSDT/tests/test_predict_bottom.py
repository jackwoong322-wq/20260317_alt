"""Tests for predict_bottom.py — Iteration 6."""

import unittest
from unittest.mock import MagicMock
import pandas as pd
import numpy as np

from lib.predictor.predict_bottom import calc_bottom_btc, calc_bottom_alt


def _make_df_all(rows):
    """rows: list of dicts with symbol, cycle_number, box_index, lo, lo_day, end_x"""
    return pd.DataFrame(rows)


def _make_last(end_x=100, symbol="BTC", cycle_number=3):
    return pd.Series({"end_x": end_x, "symbol": symbol, "cycle_number": cycle_number})


class TestCalcBottomBtc(unittest.TestCase):

    def test_empty_df_returns_none(self):
        """BTC 데이터 없으면 (None, None)."""
        df_all = pd.DataFrame(columns=["symbol", "cycle_number", "box_index", "lo", "lo_day", "end_x"])
        last = _make_last(end_x=50)
        lo, day = calc_bottom_btc(df_all, max_cyc=3, last=last)
        self.assertIsNone(lo)
        self.assertIsNone(day)

    def test_single_cycle_only_returns_btc_bottom_increase(self):
        """Cy1만 있으면 rows_excl == 1개 → 기본 증가율 적용."""
        df_all = _make_df_all([
            {"symbol": "BTC", "cycle_number": 1, "box_index": 0, "lo": 10.0, "lo_day": 100, "end_x": 100},
        ])
        last = _make_last(end_x=50)
        lo, day = calc_bottom_btc(df_all, max_cyc=2, last=last)
        # rows_excl = [Cy1] → 1개만 있음 (min_cyc=1, excl는 min_cyc 초과만)
        # 실제로는 rows_excl이 비어있어 가중평균 분기로 감
        # 어느 분기든 lo는 float 이어야 함
        self.assertIsInstance(lo, float)

    def test_two_non_cy1_cycles_uses_increase(self):
        """Cy2, Cy3 두 사이클 → 증가폭 평균 방식."""
        df_all = _make_df_all([
            {"symbol": "BTC", "cycle_number": 1, "box_index": 0, "lo": 5.0, "lo_day": 100, "end_x": 100},
            {"symbol": "BTC", "cycle_number": 2, "box_index": 0, "lo": 10.0, "lo_day": 200, "end_x": 200},
            {"symbol": "BTC", "cycle_number": 3, "box_index": 0, "lo": 15.0, "lo_day": 300, "end_x": 300},
        ])
        last = _make_last(end_x=50)
        lo, day = calc_bottom_btc(df_all, max_cyc=4, last=last)
        # 증가폭: Cy3-Cy2 = 5.0 → bottom_lo = 15.0 + 5.0 = 20.0
        self.assertIsNotNone(lo)
        self.assertAlmostEqual(lo, 20.0, places=5)

    def test_bottom_day_lower_bound(self):
        """bottom_day는 항상 last['end_x'] + 2 이상."""
        df_all = _make_df_all([
            {"symbol": "BTC", "cycle_number": 1, "box_index": 0, "lo": 5.0, "lo_day": 1, "end_x": 1},
            {"symbol": "BTC", "cycle_number": 2, "box_index": 0, "lo": 10.0, "lo_day": 2, "end_x": 2},
            {"symbol": "BTC", "cycle_number": 3, "box_index": 0, "lo": 15.0, "lo_day": 3, "end_x": 3},
        ])
        last = _make_last(end_x=5000)
        lo, day = calc_bottom_btc(df_all, max_cyc=4, last=last)
        self.assertGreaterEqual(day, 5002)

    def test_non_btc_data_excluded(self):
        """BTC 아닌 코인 데이터는 무시."""
        df_all = _make_df_all([
            {"symbol": "ETH", "cycle_number": 2, "box_index": 0, "lo": 5.0, "lo_day": 100, "end_x": 100},
            {"symbol": "ETH", "cycle_number": 3, "box_index": 0, "lo": 10.0, "lo_day": 200, "end_x": 200},
        ])
        last = _make_last(end_x=50, symbol="BTC")
        lo, day = calc_bottom_btc(df_all, max_cyc=4, last=last)
        self.assertIsNone(lo)
        self.assertIsNone(day)

    def test_lo_clamped_by_max_pred_lo(self):
        """bottom_lo는 MAX_PRED_LO 이하로 클리핑."""
        # 극단적으로 큰 lo 값
        df_all = _make_df_all([
            {"symbol": "BTC", "cycle_number": 1, "box_index": 0, "lo": 5.0, "lo_day": 100, "end_x": 100},
            {"symbol": "BTC", "cycle_number": 2, "box_index": 0, "lo": 800.0, "lo_day": 200, "end_x": 200},
            {"symbol": "BTC", "cycle_number": 3, "box_index": 0, "lo": 9999.0, "lo_day": 300, "end_x": 300},
        ])
        last = _make_last(end_x=50)
        from lib.common.config import MAX_PRED_LO
        lo, day = calc_bottom_btc(df_all, max_cyc=4, last=last)
        if lo is not None:
            self.assertLessEqual(lo, MAX_PRED_LO)


class TestCalcBottomAlt(unittest.TestCase):

    def _make_mock_models(self, lo_val=2.0, day_val=150, proba=(0.6, 0.4)):
        mock_lo = MagicMock()
        mock_lo.predict.return_value = [lo_val]
        mock_day = MagicMock()
        mock_day.predict.return_value = [float(day_val)]
        mock_trend = MagicMock()
        mock_trend.predict_proba.return_value = [list(proba)]
        return {"bottom_lo": mock_lo, "bottom_day": mock_day, "trend": mock_trend}

    def test_no_model_returns_none(self):
        """bottom_models에 그룹 없으면 모두 None."""
        X_pred = pd.DataFrame([{"f": 1}])
        last = _make_last(symbol="ALT")
        lo, day, pb, pt = calc_bottom_alt(
            bottom_models={}, group_name="ALT_BEAR", X_pred=X_pred, last=last
        )
        self.assertIsNone(lo)
        self.assertIsNone(day)
        self.assertIsNone(pb)
        self.assertIsNone(pt)

    def test_model_returns_values(self):
        """정상 모델이면 lo, day, pb, pt 반환."""
        X_pred = pd.DataFrame([{"f": 1}])
        last = _make_last(end_x=100, symbol="ETH")
        bmodels = self._make_mock_models(lo_val=1.5, day_val=200, proba=(0.3, 0.7))
        lo, day, pb, pt = calc_bottom_alt(
            bottom_models={"ETH_BEAR": bmodels},
            group_name="ETH_BEAR",
            X_pred=X_pred,
            last=last,
        )
        self.assertIsNotNone(lo)
        self.assertGreaterEqual(day, 102)  # end_x+2 하한

    def test_prob_sum_is_one(self):
        """pb + pt ≈ 1.0."""
        X_pred = pd.DataFrame([{"f": 1}])
        last = _make_last(end_x=10, symbol="XRP")
        bmodels = self._make_mock_models(proba=(0.45, 0.55))
        _, _, pb, pt = calc_bottom_alt(
            bottom_models={"XRP_BEAR": bmodels},
            group_name="XRP_BEAR",
            X_pred=X_pred,
            last=last,
        )
        self.assertAlmostEqual(pb + pt, 1.0, places=5)

    def test_day_lower_bound(self):
        """day는 end_x + 2 이상."""
        X_pred = pd.DataFrame([{"f": 1}])
        last = _make_last(end_x=500, symbol="BTC")
        bmodels = self._make_mock_models(day_val=1)  # 매우 낮은 예측일
        lo, day, pb, pt = calc_bottom_alt(
            bottom_models={"BTC_BEAR": bmodels},
            group_name="BTC_BEAR",
            X_pred=X_pred,
            last=last,
        )
        self.assertGreaterEqual(day, 502)


if __name__ == "__main__":
    unittest.main()
