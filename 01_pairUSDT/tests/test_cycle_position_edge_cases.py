"""Tests for btc_cycle_position with additional edge cases — Iteration 26.

CyclePosition 엣지 케이스:
- avg_cycle_days=0 시 day_progress fallback
- near_target_threshold 커스터마이징
- extra 딕셔너리 기본값 확인
"""

import unittest

from lib.predictor.btc_cycle_position import calc_btc_cycle_position, CyclePosition


class TestCyclePositionEdgeCases(unittest.TestCase):

    def test_zero_avg_cycle_days_fallback(self):
        """avg_cycle_days=0 → day_progress_ratio=0.0 fallback."""
        pos = calc_btc_cycle_position(
            phase="BEAR", cycle_number=5, completed_boxes=2,
            avg_boxes_historical=4.0, elapsed_days=100,
            avg_cycle_days=0,  # 0으로 설정
            current_price_pct=25.0, box_lo=20.0, box_hi=40.0,
            target_price_pct=18.0,
        )
        self.assertAlmostEqual(pos.day_progress_ratio, 0.0)

    def test_custom_near_target_threshold(self):
        """threshold를 5%로 좁히면 10% 거리는 near=False."""
        pos = calc_btc_cycle_position(
            phase="BEAR", cycle_number=5, completed_boxes=2,
            avg_boxes_historical=4.0, elapsed_days=100,
            avg_cycle_days=200, current_price_pct=30.0,
            box_lo=20.0, box_hi=40.0,
            target_price_pct=27.0,  # 10% 거리
            near_target_threshold_pct=5.0,  # 5% 임계값
        )
        self.assertFalse(pos.is_near_target)

    def test_wide_near_target_threshold(self):
        """threshold를 30%로 넓히면 10% 거리도 near=True."""
        pos = calc_btc_cycle_position(
            phase="BEAR", cycle_number=5, completed_boxes=2,
            avg_boxes_historical=4.0, elapsed_days=100,
            avg_cycle_days=200, current_price_pct=30.0,
            box_lo=20.0, box_hi=40.0,
            target_price_pct=27.0,  # 10% 거리
            near_target_threshold_pct=30.0,  # 30% 임계값
        )
        self.assertTrue(pos.is_near_target)

    def test_extra_is_empty_dict_by_default(self):
        """extra 필드는 기본 빈 딕셔너리."""
        pos = calc_btc_cycle_position(
            phase="BULL", cycle_number=4, completed_boxes=3,
            avg_boxes_historical=5.0, elapsed_days=200,
            avg_cycle_days=500, current_price_pct=80.0,
            box_lo=50.0, box_hi=120.0, target_price_pct=150.0,
        )
        self.assertIsInstance(pos.extra, dict)

    def test_bull_box_progress_over_average_allowed(self):
        """Bull box_progress > 1.0 허용."""
        pos = calc_btc_cycle_position(
            phase="BULL", cycle_number=4, completed_boxes=8,
            avg_boxes_historical=5.0, elapsed_days=400,
            avg_cycle_days=500, current_price_pct=100.0,
            box_lo=50.0, box_hi=120.0, target_price_pct=150.0,
        )
        self.assertAlmostEqual(pos.box_progress_ratio, 8 / 5.0)


class TestCalcPricePositionExtended(unittest.TestCase):

    def test_exact_at_25_percent(self):
        """25% 지점 계산 정확도."""
        from lib.predictor.btc_cycle_position import calc_price_position
        # (25-20)/(40-20) = 5/20 = 0.25
        result = calc_price_position(25.0, 20.0, 40.0)
        self.assertAlmostEqual(result, 0.25, places=6)

    def test_exact_at_75_percent(self):
        from lib.predictor.btc_cycle_position import calc_price_position
        # (35-20)/(40-20) = 15/20 = 0.75
        result = calc_price_position(35.0, 20.0, 40.0)
        self.assertAlmostEqual(result, 0.75, places=6)


if __name__ == "__main__":
    unittest.main()
