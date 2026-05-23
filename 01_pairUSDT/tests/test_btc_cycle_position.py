"""Tests for btc_cycle_position.py — Iteration 9.

btc_cycle_position 모듈은 BTC 사이클 내 현재 위치(박스 진행률, 일수 진행률,
가격 위치, 목표가까지 거리)를 계산하는 투자 타이밍 판단의 핵심 입력 모듈이다.
"""

import unittest

from lib.predictor.btc_cycle_position import (
    calc_bear_box_progress,
    calc_bull_box_progress,
    calc_price_position,
    calc_distance_to_target,
    calc_btc_cycle_position,
    CyclePosition,
)


class TestCalcBearBoxProgress(unittest.TestCase):

    def test_no_boxes_completed(self):
        """완료 박스 0개 → 진행률 0."""
        self.assertAlmostEqual(calc_bear_box_progress(0, 4.0), 0.0)

    def test_half_completed(self):
        """2/4 완료 → 진행률 0.5."""
        self.assertAlmostEqual(calc_bear_box_progress(2, 4.0), 0.5)

    def test_fully_completed(self):
        """4/4 완료 → 진행률 1.0."""
        self.assertAlmostEqual(calc_bear_box_progress(4, 4.0), 1.0)

    def test_beyond_average(self):
        """평균 초과 완료 → 1.0 이상 허용."""
        self.assertAlmostEqual(calc_bear_box_progress(6, 4.0), 1.5)

    def test_zero_avg_returns_zero(self):
        """avg=0이면 ZeroDivision 없이 0.0 반환."""
        self.assertAlmostEqual(calc_bear_box_progress(3, 0.0), 0.0)


class TestCalcBullBoxProgress(unittest.TestCase):

    def test_no_boxes_completed(self):
        self.assertAlmostEqual(calc_bull_box_progress(0, 5.0), 0.0)

    def test_three_of_five(self):
        self.assertAlmostEqual(calc_bull_box_progress(3, 5.0), 0.6)

    def test_zero_avg_returns_zero(self):
        self.assertAlmostEqual(calc_bull_box_progress(2, 0.0), 0.0)


class TestCalcPricePosition(unittest.TestCase):

    def test_at_lower(self):
        """가격이 lo = 하단 → 0.0."""
        self.assertAlmostEqual(calc_price_position(20.0, 20.0, 50.0), 0.0)

    def test_at_upper(self):
        """가격이 hi = 상단 → 1.0."""
        self.assertAlmostEqual(calc_price_position(50.0, 20.0, 50.0), 1.0)

    def test_midpoint(self):
        """중간가 → 0.5."""
        self.assertAlmostEqual(calc_price_position(35.0, 20.0, 50.0), 0.5)

    def test_below_lower_clamps_to_zero(self):
        """lo 미만은 0으로 클리핑."""
        self.assertAlmostEqual(calc_price_position(10.0, 20.0, 50.0), 0.0)

    def test_above_upper_clamps_to_one(self):
        """hi 초과는 1로 클리핑."""
        self.assertAlmostEqual(calc_price_position(60.0, 20.0, 50.0), 1.0)

    def test_equal_lo_hi_returns_half(self):
        """lo == hi면 0.5 반환."""
        self.assertAlmostEqual(calc_price_position(30.0, 30.0, 30.0), 0.5)


class TestCalcDistanceToTarget(unittest.TestCase):

    def test_bear_target_below_current(self):
        """Bear: target < current → 음수 (하락 여지)."""
        dist = calc_distance_to_target(30.0, 20.0)
        self.assertLess(dist, 0.0)

    def test_bull_target_above_current(self):
        """Bull: target > current → 양수 (상승 여지)."""
        dist = calc_distance_to_target(30.0, 60.0)
        self.assertGreater(dist, 0.0)

    def test_at_target(self):
        """현재가 == 목표가 → 0.0."""
        self.assertAlmostEqual(calc_distance_to_target(30.0, 30.0), 0.0)

    def test_zero_current_returns_zero(self):
        """현재가 0이면 fallback 0.0."""
        self.assertAlmostEqual(calc_distance_to_target(0.0, 30.0), 0.0)

    def test_distance_magnitude(self):
        """30에서 45까지: 50% 상승 여지."""
        dist = calc_distance_to_target(30.0, 45.0)
        self.assertAlmostEqual(dist, 50.0, places=4)


class TestCalcBtcCyclePosition(unittest.TestCase):

    def _make_bear_position(self, completed=2, avg=4.0, elapsed=100, avg_days=200,
                             current=25.0, lo=20.0, hi=40.0, target=18.0):
        return calc_btc_cycle_position(
            phase="BEAR",
            cycle_number=5,
            completed_boxes=completed,
            avg_boxes_historical=avg,
            elapsed_days=elapsed,
            avg_cycle_days=avg_days,
            current_price_pct=current,
            box_lo=lo,
            box_hi=hi,
            target_price_pct=target,
        )

    def test_returns_cycle_position_instance(self):
        pos = self._make_bear_position()
        self.assertIsInstance(pos, CyclePosition)

    def test_phase_preserved(self):
        pos = self._make_bear_position()
        self.assertEqual(pos.phase, "BEAR")

    def test_box_progress_correct(self):
        pos = self._make_bear_position(completed=2, avg=4.0)
        self.assertAlmostEqual(pos.box_progress_ratio, 0.5)

    def test_day_progress_correct(self):
        pos = self._make_bear_position(elapsed=100, avg_days=200)
        self.assertAlmostEqual(pos.day_progress_ratio, 0.5)

    def test_day_progress_clamped(self):
        """일수 진행률은 1.5 이상으로 클리핑."""
        pos = self._make_bear_position(elapsed=10000, avg_days=100)
        self.assertLessEqual(pos.day_progress_ratio, 1.5)

    def test_is_near_target_when_close(self):
        """현재가가 목표가에 가까우면 is_near_target=True."""
        pos = calc_btc_cycle_position(
            phase="BEAR", cycle_number=5, completed_boxes=3,
            avg_boxes_historical=4.0, elapsed_days=150, avg_cycle_days=200,
            current_price_pct=20.0, box_lo=18.0, box_hi=30.0,
            target_price_pct=21.0,  # 5% 거리 → near
        )
        self.assertTrue(pos.is_near_target)

    def test_is_not_near_target_when_far(self):
        """현재가가 목표가에서 멀면 is_near_target=False."""
        pos = calc_btc_cycle_position(
            phase="BULL", cycle_number=5, completed_boxes=2,
            avg_boxes_historical=5.0, elapsed_days=100, avg_cycle_days=400,
            current_price_pct=30.0, box_lo=20.0, box_hi=100.0,
            target_price_pct=200.0,  # 567% 거리 → far
        )
        self.assertFalse(pos.is_near_target)

    def test_bull_phase_box_progress(self):
        """Bull phase: bull_box_progress 사용."""
        pos = calc_btc_cycle_position(
            phase="BULL", cycle_number=4, completed_boxes=3,
            avg_boxes_historical=6.0, elapsed_days=200, avg_cycle_days=500,
            current_price_pct=80.0, box_lo=50.0, box_hi=120.0,
            target_price_pct=150.0,
        )
        self.assertAlmostEqual(pos.box_progress_ratio, 3 / 6)


if __name__ == "__main__":
    unittest.main()
