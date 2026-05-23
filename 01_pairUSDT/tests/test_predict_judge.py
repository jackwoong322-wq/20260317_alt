"""Unit tests for predict_judge — BULL/BEAR 판정 로직.

DevLoop Iteration 4 — 투자 판정 핵심 로직 테스트
"""
import sys
import os
import unittest
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lib.predictor.predict_judge import (
    _check_lower_low_slope,
    _check_force_bear,
    judge_bull_bear,
)


def _make_series(symbol="ADA", lo=50.0, end_x=100, gain_pct=0.0, lo_change_pct=0.0):
    return pd.Series({
        "symbol": symbol,
        "lo": lo,
        "end_x": end_x,
        "gain_pct": gain_pct,
        "lo_change_pct": lo_change_pct,
    })


def _make_df(rows):
    return pd.DataFrame(rows, columns=["lo", "end_x", "gain_pct", "lo_change_pct"])


class TestCheckLowerLowSlope(unittest.TestCase):

    def test_single_row_no_lower_low(self):
        """이전 행이 없으면 lower_low=False."""
        last = _make_series(lo=40.0)
        grp = _make_df([{"lo": 40.0, "end_x": 100, "gain_pct": 0, "lo_change_pct": 0}])
        lower_low, prev_lo, slope_down, gain, lo_chg = _check_lower_low_slope(last, grp)
        self.assertFalse(lower_low)
        self.assertIsNone(prev_lo)

    def test_lower_low_true_when_lo_decreases(self):
        """현재 lo < 이전 lo 이면 lower_low=True."""
        last = _make_series(lo=30.0)
        grp = _make_df([
            {"lo": 50.0, "end_x": 90, "gain_pct": 0, "lo_change_pct": 0},
            {"lo": 30.0, "end_x": 100, "gain_pct": 0, "lo_change_pct": 0},
        ])
        lower_low, _, _, _, _ = _check_lower_low_slope(last, grp)
        self.assertTrue(lower_low)

    def test_slope_down_via_gain_pct(self):
        """gain_pct < -10 이면 slope_down=True."""
        last = _make_series(lo=40.0, gain_pct=-15.0)
        grp = _make_df([{"lo": 40.0, "end_x": 100, "gain_pct": -15.0, "lo_change_pct": 0}])
        _, _, slope_down, gain, _ = _check_lower_low_slope(last, grp)
        self.assertTrue(slope_down)
        self.assertAlmostEqual(gain, -15.0)

    def test_slope_down_via_lo_change_pct(self):
        """lo_change_pct < -5 이면 slope_down=True."""
        last = _make_series(lo=40.0, lo_change_pct=-8.0)
        grp = _make_df([{"lo": 40.0, "end_x": 100, "gain_pct": 0, "lo_change_pct": -8.0}])
        _, _, slope_down, _, lo_chg = _check_lower_low_slope(last, grp)
        self.assertTrue(slope_down)
        self.assertAlmostEqual(lo_chg, -8.0)

    def test_no_slope_down_mild_values(self):
        """약한 하락 값 → slope_down=False."""
        last = _make_series(lo=40.0, gain_pct=-5.0, lo_change_pct=-2.0)
        grp = _make_df([{"lo": 40.0, "end_x": 100, "gain_pct": -5.0, "lo_change_pct": -2.0}])
        _, _, slope_down, _, _ = _check_lower_low_slope(last, grp)
        self.assertFalse(slope_down)


class TestCheckForceBear(unittest.TestCase):

    def _grp(self, lo=50.0, end_x=100):
        return _make_df([{"lo": lo, "end_x": end_x, "gain_pct": 0, "lo_change_pct": 0}])

    def test_before_bottom_day_forces_bear(self):
        """현재 end_x < bottom_day → force_bear=True, 이유='before_bottom'."""
        last = _make_series(lo=50.0, end_x=80)
        grp = self._grp(lo=50.0, end_x=80)
        force_bear, reasons, _ = _check_force_bear(
            last, grp, bottom_day=100, bottom_lo=40.0,
            lower_low=False, slope_down=False, btc_anchor=None
        )
        self.assertTrue(force_bear)
        self.assertIn("before_bottom", reasons)

    def test_lower_low_no_bottom_forces_bear(self):
        """bottom_day=None, lower_low=True → force_bear=True."""
        last = _make_series(lo=30.0, end_x=100)
        grp = self._grp(lo=30.0, end_x=100)
        force_bear, reasons, _ = _check_force_bear(
            last, grp, bottom_day=None, bottom_lo=None,
            lower_low=True, slope_down=False, btc_anchor=None
        )
        self.assertTrue(force_bear)
        self.assertIn("lower_low", reasons)

    def test_btc_anchor_triggers_force_bear(self):
        """BTC anchor slope_down + cycle_progress > 0.6 → force_bear=True for non-BTC."""
        last = _make_series(symbol="ETH", lo=50.0, end_x=100)
        grp = self._grp(lo=50.0, end_x=100)
        btc_anchor = {"slope_down": True, "cycle_progress_ratio": 0.75}
        force_bear, reasons, triggered = _check_force_bear(
            last, grp, bottom_day=None, bottom_lo=None,
            lower_low=False, slope_down=False, btc_anchor=btc_anchor
        )
        self.assertTrue(force_bear)
        self.assertTrue(triggered)
        self.assertIn("btc_anchor", reasons)

    def test_btc_itself_not_affected_by_anchor(self):
        """BTC 코인은 btc_anchor 영향을 받지 않는다."""
        last = _make_series(symbol="BTC", lo=50.0, end_x=100)
        grp = self._grp(lo=50.0, end_x=100)
        btc_anchor = {"slope_down": True, "cycle_progress_ratio": 0.9}
        force_bear, _, triggered = _check_force_bear(
            last, grp, bottom_day=None, bottom_lo=None,
            lower_low=False, slope_down=False, btc_anchor=btc_anchor
        )
        self.assertFalse(force_bear)
        self.assertFalse(triggered)

    def test_no_conditions_no_force_bear(self):
        """아무 조건도 없으면 force_bear=False."""
        last = _make_series(lo=50.0, end_x=150)
        grp = self._grp(lo=50.0, end_x=150)
        force_bear, reasons, _ = _check_force_bear(
            last, grp, bottom_day=100, bottom_lo=40.0,
            lower_low=False, slope_down=False, btc_anchor=None
        )
        self.assertFalse(force_bear)
        self.assertEqual(reasons, [])


class TestJudgeBullBear(unittest.TestCase):

    def _call(self, symbol="ADA", lo=50.0, end_x=100, prob_bull=0.7, prob_bear=0.3,
              bottom_day=None, btc_anchor=None, gain_pct=0.0, lo_change_pct=0.0,
              grp_rows=None):
        last = _make_series(symbol=symbol, lo=lo, end_x=end_x,
                            gain_pct=gain_pct, lo_change_pct=lo_change_pct)
        if grp_rows is None:
            grp_rows = [{"lo": lo, "end_x": end_x, "gain_pct": gain_pct,
                         "lo_change_pct": lo_change_pct}]
        grp = _make_df(grp_rows)
        return judge_bull_bear(
            last=last, grp=grp, max_cyc=3,
            prob_bull=prob_bull, prob_bear=prob_bear,
            bottom_day=bottom_day, btc_anchor=btc_anchor, bottom_lo=None
        )

    def test_model_says_bull_no_override(self):
        """prob_bull > prob_bear, force 조건 없음 → pred_is_bull=1."""
        result = self._call(prob_bull=0.8, prob_bear=0.2)
        pred_is_bull = result[0]
        self.assertEqual(pred_is_bull, 1)

    def test_model_says_bear(self):
        """prob_bull < prob_bear → pred_is_bull=0."""
        result = self._call(prob_bull=0.3, prob_bear=0.7)
        self.assertEqual(result[0], 0)

    def test_force_bear_overrides_bull_probability(self):
        """prob_bull > prob_bear 이어도 force_bear 조건 충족 시 pred_is_bull=0."""
        result = self._call(
            prob_bull=0.9, prob_bear=0.1,
            end_x=50, bottom_day=100  # before_bottom → force_bear
        )
        self.assertEqual(result[0], 0)

    def test_return_tuple_length(self):
        """반환 튜플이 9개 요소여야 한다."""
        result = self._call()
        self.assertEqual(len(result), 9)

    def test_force_bear_flag_in_result(self):
        """force_bear 플래그(index 6)가 bool이어야 한다."""
        result = self._call()
        self.assertIsInstance(result[6], bool)

    def test_force_reason_is_list(self):
        """force_reason(index 7)이 리스트여야 한다."""
        result = self._call()
        self.assertIsInstance(result[7], list)


if __name__ == "__main__":
    unittest.main()
