"""Iters 71-75: predict_features 순수함수 추가 엣지케이스 테스트."""

import unittest
import pandas as pd
import numpy as np
from lib.predictor.predict_features import build_feature_vector


def _last(**kw):
    defaults = {
        "norm_range_pct": 5.0, "norm_hi_change_pct": 3.0,
        "norm_lo_change_pct": -2.0, "norm_gain_pct": 1.0,
        "norm_duration": 0.5, "hi": 30.0, "lo": 10.0,
        "coin_rank": 1, "phase": "BEAR", "box_index": 2,
        "end_x": 180, "symbol": "BTC",
    }
    defaults.update(kw)
    return pd.Series(defaults)


def _cycle_stats(total_days=360, low_x=200, min_lo=8.0):
    return {(1, 3): {"total_days": total_days, "low_x": low_x, "min_lo": min_lo}}


def _coin_stats(avg_cycle_days=360, mean_lo=10.0, min_lo=8.0):
    return {1: {"avg_cycle_days": avg_cycle_days, "mean_lo": mean_lo, "min_lo": min_lo}}


def _phase_box_stats(cnt=5):
    return {(1, "BEAR"): cnt}


class TestBuildFeatureVector(unittest.TestCase):

    def test_returns_tuple(self):
        feat, avg_days = build_feature_vector(
            _last(), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(),
            coin_stats=_coin_stats(),
            phase_box_stats=_phase_box_stats(),
        )
        self.assertIsInstance(feat, dict)
        self.assertIsInstance(avg_days, float)

    def test_required_keys_present(self):
        feat, _ = build_feature_vector(
            _last(), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(),
            coin_stats=_coin_stats(),
            phase_box_stats=_phase_box_stats(),
        )
        for k in ["norm_range_pct", "is_bull", "box_index", "cycle_progress_ratio",
                  "log_cycle_number", "btc_prev_peak_ratio"]:
            self.assertIn(k, feat)

    def test_is_bull_for_bear(self):
        feat, _ = build_feature_vector(
            _last(phase="BEAR"), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(), coin_stats=_coin_stats(),
            phase_box_stats=_phase_box_stats(),
        )
        self.assertEqual(feat["is_bull"], 0)

    def test_is_bull_for_bull(self):
        feat, _ = build_feature_vector(
            _last(phase="BULL"), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(), coin_stats=_coin_stats(),
            phase_box_stats={(1, "BULL"): 5},
        )
        self.assertEqual(feat["is_bull"], 1)

    def test_log_cycle_number_positive(self):
        feat, _ = build_feature_vector(
            _last(), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(), coin_stats=_coin_stats(),
            phase_box_stats=_phase_box_stats(),
        )
        self.assertGreater(feat["log_cycle_number"], 0)

    def test_cycle_progress_ratio_in_range(self):
        feat, _ = build_feature_vector(
            _last(end_x=180), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(total_days=360),
            coin_stats=_coin_stats(avg_cycle_days=360),
            phase_box_stats=_phase_box_stats(),
        )
        self.assertAlmostEqual(feat["cycle_progress_ratio"], 0.5, places=5)

    def test_btc_prev_peak_ratio_set(self):
        feat, _ = build_feature_vector(
            _last(symbol="BTC", hi=30.0), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(), coin_stats=_coin_stats(),
            phase_box_stats=_phase_box_stats(),
            btc_cycle_max_hi={2: 20.0},
        )
        self.assertAlmostEqual(feat["btc_prev_peak_ratio"], 1.5, places=5)

    def test_avg_days_returned(self):
        _, avg = build_feature_vector(
            _last(), coin_id=1, max_cyc=3,
            cycle_stats=_cycle_stats(),
            coin_stats=_coin_stats(avg_cycle_days=400),
            phase_box_stats=_phase_box_stats(),
        )
        self.assertAlmostEqual(avg, 400.0)


if __name__ == "__main__":
    unittest.main()
