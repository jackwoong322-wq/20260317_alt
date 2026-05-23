"""Tests for predict_features.py — Iteration 8."""

import unittest
import pandas as pd
import numpy as np

from lib.predictor.predict_features import build_feature_vector


def _make_last(
    phase="BULL",
    box_index=2,
    end_x=150,
    lo=20.0,
    hi=50.0,
    coin_rank=5,
    symbol="BTC",
    norm_range_pct=0.1,
    norm_hi_change_pct=0.05,
    norm_lo_change_pct=-0.03,
    norm_gain_pct=0.08,
    norm_duration=0.4,
    cycle_number=3,
):
    return pd.Series({
        "phase": phase,
        "box_index": box_index,
        "end_x": end_x,
        "lo": lo,
        "hi": hi,
        "coin_rank": coin_rank,
        "symbol": symbol,
        "norm_range_pct": norm_range_pct,
        "norm_hi_change_pct": norm_hi_change_pct,
        "norm_lo_change_pct": norm_lo_change_pct,
        "norm_gain_pct": norm_gain_pct,
        "norm_duration": norm_duration,
        "cycle_number": cycle_number,
    })


def _make_cycle_stats(coin_id=1, max_cyc=3, total_days=300, low_x=100, min_lo=15.0):
    return {(coin_id, max_cyc): {"total_days": total_days, "low_x": low_x, "min_lo": min_lo}}


def _make_coin_stats(coin_id=1, avg_cycle_days=300, mean_lo=18.0, min_lo=10.0):
    return {coin_id: {"avg_cycle_days": avg_cycle_days, "mean_lo": mean_lo, "min_lo": min_lo}}


def _make_phase_box_stats(coin_id=1, phase="BULL", avg_count=4.0):
    return {(coin_id, phase): avg_count}


class TestBuildFeatureVector(unittest.TestCase):

    def test_returns_two_tuple(self):
        """반환값은 (dict, float) 2-tuple."""
        last = _make_last()
        feat, avg_days = build_feature_vector(
            last=last,
            coin_id=1,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(),
            coin_stats=_make_coin_stats(),
            phase_box_stats=_make_phase_box_stats(),
        )
        self.assertIsInstance(feat, dict)
        self.assertIsInstance(avg_days, float)

    def test_required_keys_present(self):
        """필수 키가 모두 포함되어야 함."""
        last = _make_last()
        feat, _ = build_feature_vector(
            last=last,
            coin_id=1,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(),
            coin_stats=_make_coin_stats(),
            phase_box_stats=_make_phase_box_stats(),
        )
        required_keys = [
            "norm_range_pct", "norm_hi_change_pct", "norm_lo_change_pct",
            "norm_gain_pct", "norm_duration", "hi_rel_to_cycle_lo",
            "lo_rel_to_cycle_lo", "coin_rank", "is_bull", "box_index",
            "cycle_progress_ratio", "cycle_low_pos_ratio",
            "rel_to_prev_cycle_low", "rel_to_prev_support_mean",
            "phase_box_index_ratio", "phase_avg_box_count",
            "btc_prev_peak_ratio", "log_cycle_number",
        ]
        for key in required_keys:
            self.assertIn(key, feat, f"Key '{key}' missing from feature vector")

    def test_is_bull_flag_correct(self):
        """BULL phase → is_bull=1, BEAR → is_bull=0."""
        for phase, expected in [("BULL", 1), ("BEAR", 0)]:
            last = _make_last(phase=phase)
            feat, _ = build_feature_vector(
                last=last,
                coin_id=1,
                max_cyc=3,
                cycle_stats=_make_cycle_stats(),
                coin_stats=_make_coin_stats(),
                phase_box_stats=_make_phase_box_stats(phase=phase),
            )
            self.assertEqual(feat["is_bull"], expected)

    def test_log_cycle_number_correct(self):
        """log_cycle_number = log(max_cyc + 1)."""
        last = _make_last()
        feat, _ = build_feature_vector(
            last=last,
            coin_id=1,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(),
            coin_stats=_make_coin_stats(),
            phase_box_stats=_make_phase_box_stats(),
        )
        expected = float(np.log(4))  # log(3+1)
        self.assertAlmostEqual(feat["log_cycle_number"], expected, places=5)

    def test_avg_cycle_days_returned(self):
        """coin_stats에 avg_cycle_days가 있으면 그 값을 avg_days로 반환."""
        last = _make_last()
        _, avg_days = build_feature_vector(
            last=last,
            coin_id=1,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(),
            coin_stats=_make_coin_stats(avg_cycle_days=400),
            phase_box_stats=_make_phase_box_stats(),
        )
        self.assertAlmostEqual(avg_days, 400.0)

    def test_btc_prev_peak_ratio_nonzero_for_btc(self):
        """BTC + max_cyc>1 + btc_cycle_max_hi 있으면 btc_prev_peak_ratio != 0."""
        last = _make_last(symbol="BTC", hi=120.0)
        feat, _ = build_feature_vector(
            last=last,
            coin_id=1,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(),
            coin_stats=_make_coin_stats(),
            phase_box_stats=_make_phase_box_stats(),
            btc_cycle_max_hi={2: 100.0},  # prev cycle hi
        )
        # btc_prev_peak_ratio = 120.0 / 100.0 = 1.2
        self.assertAlmostEqual(feat["btc_prev_peak_ratio"], 1.2, places=5)

    def test_btc_prev_peak_ratio_zero_for_alt(self):
        """ALT 코인은 btc_prev_peak_ratio = 0."""
        last = _make_last(symbol="ETH", hi=80.0)
        feat, _ = build_feature_vector(
            last=last,
            coin_id=2,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(coin_id=2),
            coin_stats=_make_coin_stats(coin_id=2),
            phase_box_stats=_make_phase_box_stats(coin_id=2),
            btc_cycle_max_hi={2: 100.0},
        )
        self.assertAlmostEqual(feat["btc_prev_peak_ratio"], 0.0, places=5)

    def test_empty_coin_stats_uses_defaults(self):
        """coin_stats 없으면 avg_cycle_days = total_days."""
        last = _make_last()
        feat, avg_days = build_feature_vector(
            last=last,
            coin_id=99,
            max_cyc=3,
            cycle_stats=_make_cycle_stats(coin_id=99),
            coin_stats={},  # 해당 coin_id 없음
            phase_box_stats={},
        )
        # avg_cycle_days fallback → total_days = 300
        self.assertAlmostEqual(avg_days, 300.0)


if __name__ == "__main__":
    unittest.main()
