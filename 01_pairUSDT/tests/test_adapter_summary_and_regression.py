"""Iters 41-43: to_position_summary + linear_regression + apply_guards 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_signal_adapter import to_position_summary
from lib.predictor.predict_cycle_box_count import (
    _linear_regression_predict, _apply_guards,
)


def _make_pos(**kw):
    defaults = dict(
        phase="BEAR", cycle_number=5, completed_boxes=7,
        avg_boxes_historical=10.0, box_progress_ratio=0.7,
        day_progress_ratio=0.65, price_position=0.25,
        distance_to_target_pct=5.0, is_near_target=True,
    )
    defaults.update(kw)
    return CyclePosition(**defaults)


class TestToPositionSummary(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(to_position_summary(_make_pos()), str)

    def test_contains_phase(self):
        s = to_position_summary(_make_pos(phase="BEAR"))
        self.assertIn("BEAR", s)

    def test_contains_cycle_number(self):
        s = to_position_summary(_make_pos(cycle_number=5))
        self.assertIn("cy=5", s)

    def test_contains_pct(self):
        s = to_position_summary(_make_pos(box_progress_ratio=0.7))
        self.assertIn("70%", s)

    def test_contains_near_target(self):
        s = to_position_summary(_make_pos(is_near_target=True))
        self.assertIn("near=True", s)

    def test_bull_phase(self):
        s = to_position_summary(_make_pos(phase="BULL"))
        self.assertIn("BULL", s)

    def test_zero_progress(self):
        s = to_position_summary(_make_pos(box_progress_ratio=0.0, completed_boxes=0))
        self.assertIn("0%", s)


class TestLinearRegressionPredict(unittest.TestCase):

    def test_empty_returns_zero(self):
        self.assertEqual(_linear_regression_predict([], next_x=5), 0.0)

    def test_single_point_returns_zero(self):
        self.assertEqual(_linear_regression_predict([(1, 3.0)], next_x=2), 0.0)

    def test_perfect_linear(self):
        # y = 2x + 1
        points = [(1, 3.0), (2, 5.0), (3, 7.0)]
        result = _linear_regression_predict(points, next_x=4)
        self.assertAlmostEqual(result, 9.0, places=5)

    def test_horizontal_line(self):
        # y = 5 (slope=0)
        points = [(1, 5.0), (2, 5.0), (3, 5.0)]
        result = _linear_regression_predict(points, next_x=10)
        self.assertAlmostEqual(result, 5.0, places=5)

    def test_extrapolation(self):
        points = [(1, 2.0), (2, 4.0)]
        result = _linear_regression_predict(points, next_x=5)
        self.assertAlmostEqual(result, 10.0, places=5)


class TestApplyGuards(unittest.TestCase):

    def test_normal_values_no_guard(self):
        bear, bull, g_b, g_u = _apply_guards(3.0, 5.0, prev_bear=3, prev_bull=5)
        self.assertEqual(bear, 3)
        self.assertEqual(bull, 5)

    def test_bear_guard_applied(self):
        # raw_bear=1, prev_bear=4, BEAR_GUARD_DELTA=1 → bear_floor=3 > 1 → guard
        from lib.common.config import BEAR_GUARD_DELTA
        bear, bull, g_b, g_u = _apply_guards(1.0, 5.0, prev_bear=4, prev_bull=5)
        self.assertGreaterEqual(bear, max(1, 4 - BEAR_GUARD_DELTA))

    def test_min_box_count_enforced(self):
        # raw=0 → min box count applied
        from lib.common.config import MIN_BOX_COUNT
        bear, bull, _, _ = _apply_guards(0.0, 0.0, prev_bear=1, prev_bull=1)
        self.assertGreaterEqual(bear, MIN_BOX_COUNT)
        self.assertGreaterEqual(bull, MIN_BOX_COUNT)

    def test_bull_guard_applied(self):
        # bull raw < prev_bull → guard
        bear, bull, g_b, g_u = _apply_guards(3.0, 2.0, prev_bear=3, prev_bull=5)
        self.assertGreaterEqual(bull, 5)
        self.assertTrue(g_u)


if __name__ == "__main__":
    unittest.main()
