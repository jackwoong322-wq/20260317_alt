"""Tests for predict_cycle_box_count.py — Iteration 16.

선형 회귀 기반 박스 수 예측 및 가드 로직 단위 테스트.
DB 연결 없이 순수 함수만 테스트.
"""

import unittest

from lib.predictor.predict_cycle_box_count import (
    _linear_regression_predict,
    _apply_guards,
    _nearest_previous_count,
    CyclePrediction,
)
from lib.common.config import MIN_BOX_COUNT, MAX_BEAR_CHAIN, BEAR_GUARD_DELTA


class TestLinearRegressionPredict(unittest.TestCase):

    def test_two_points_exact(self):
        """두 점 (1,2), (2,4) → 기울기=2, 절편=0 → next_x=3 → 6."""
        points = [(1, 2.0), (2, 4.0)]
        result = _linear_regression_predict(points, next_x=3)
        self.assertAlmostEqual(result, 6.0, places=5)

    def test_flat_line(self):
        """y가 동일하면 기울기=0 → 예측값 = 평균."""
        points = [(1, 3.0), (2, 3.0), (3, 3.0)]
        result = _linear_regression_predict(points, next_x=10)
        self.assertAlmostEqual(result, 3.0, places=5)

    def test_single_point_returns_zero(self):
        """1개 점은 회귀 불가 → 0.0."""
        self.assertAlmostEqual(_linear_regression_predict([(1, 5.0)], 2), 0.0)

    def test_empty_returns_zero(self):
        """빈 배열 → 0.0."""
        self.assertAlmostEqual(_linear_regression_predict([], 2), 0.0)

    def test_increasing_trend(self):
        """증가 추세 → 다음값은 마지막값보다 큼."""
        points = [(1, 2.0), (2, 3.0), (3, 4.0), (4, 5.0)]
        result = _linear_regression_predict(points, next_x=5)
        self.assertGreater(result, 5.0)

    def test_decreasing_trend(self):
        """감소 추세 → 다음값은 이전값보다 작음."""
        points = [(1, 10.0), (2, 8.0), (3, 6.0)]
        result = _linear_regression_predict(points, next_x=4)
        self.assertLess(result, 6.0)

    def test_all_x_same_returns_zero(self):
        """x 모두 동일 → 분모=0 → 0.0 반환 (ZeroDivision 없음)."""
        points = [(1, 2.0), (1, 4.0), (1, 6.0)]
        result = _linear_regression_predict(points, next_x=1)
        self.assertAlmostEqual(result, 0.0)


class TestApplyGuards(unittest.TestCase):

    def test_normal_case_no_guard(self):
        """정상 케이스: guard 미적용."""
        bear, bull, g_bear, g_bull = _apply_guards(
            raw_bear=3.5, raw_bull=4.5, prev_bear=4, prev_bull=4
        )
        self.assertEqual(bear, 4)   # round(3.5) = 4 (banker's rounding)
        self.assertGreaterEqual(bull, 4)  # max(round(4.5), prev_bull=4) = 4

    def test_bear_guard_prevents_large_drop(self):
        """Bear: 예측값이 이전 대비 GUARD_DELTA 이상 감소 시 하한 적용."""
        prev_bear = 5
        # raw_bear=1 → round=1, floor = prev_bear - BEAR_GUARD_DELTA = 5-2=3
        bear, _, g_bear, _ = _apply_guards(1.0, 5.0, prev_bear=5, prev_bull=5)
        self.assertGreaterEqual(bear, prev_bear - BEAR_GUARD_DELTA)
        self.assertTrue(g_bear)

    def test_bull_guard_prevents_decrease(self):
        """Bull: 예측값이 이전보다 감소하면 이전값으로 고정."""
        _, bull, _, g_bull = _apply_guards(4.0, 2.0, prev_bear=4, prev_bull=5)
        self.assertGreaterEqual(bull, 5)  # prev_bull 유지
        self.assertTrue(g_bull)

    def test_minimum_count_applied(self):
        """raw가 0 이하여도 MIN_BOX_COUNT 이상."""
        bear, bull, _, _ = _apply_guards(-1.0, -2.0, prev_bear=0, prev_bull=0)
        self.assertGreaterEqual(bear, MIN_BOX_COUNT)
        self.assertGreaterEqual(bull, MIN_BOX_COUNT)

    def test_no_guard_when_values_increase(self):
        """값이 자연스럽게 증가하면 guard=False."""
        prev_bear = 3
        # raw=4 → round=4, floor=max(3-delta, MIN)=1 → bear=4, no guard
        bear, _, g_bear, _ = _apply_guards(4.0, 5.0, prev_bear=3, prev_bull=4)
        self.assertFalse(g_bear)


class TestNearestPreviousCount(unittest.TestCase):

    def test_returns_last_before_target(self):
        counts = [(1, 3, 5), (2, 4, 6), (3, 5, 7)]
        result = _nearest_previous_count(counts, target_cycle_number=4, index=1)
        self.assertEqual(result, 5)  # cy3의 bear_count

    def test_no_previous_returns_min(self):
        counts = [(3, 5, 7)]
        result = _nearest_previous_count(counts, target_cycle_number=2, index=1)
        self.assertEqual(result, MIN_BOX_COUNT)

    def test_exact_target_excluded(self):
        """target_cycle_number 자신은 포함 안 됨."""
        counts = [(1, 2, 3), (2, 4, 5)]
        result = _nearest_previous_count(counts, target_cycle_number=2, index=1)
        self.assertEqual(result, 2)  # cy1만 포함


if __name__ == "__main__":
    unittest.main()
