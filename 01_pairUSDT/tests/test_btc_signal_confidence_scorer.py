"""Tests for btc_signal_confidence_scorer.py — Iteration 24."""

import unittest

from lib.predictor.btc_signal_confidence_scorer import (
    adjust_confidence_by_history,
    adjust_confidence_by_position,
    compute_final_confidence,
    CONSECUTIVE_BONUS_PER_COUNT,
    MAX_CONSECUTIVE_BONUS,
    NEAR_TARGET_BONUS,
    INCONSISTENCY_PENALTY,
)


class TestAdjustConfidenceByHistory(unittest.TestCase):

    def test_no_change_no_consecutive(self):
        """변화 없고 연속 1개 → 조정 없음."""
        result = adjust_confidence_by_history(0.7, consecutive_count=1, is_signal_changed=False)
        self.assertAlmostEqual(result, 0.7)

    def test_consecutive_bonus_applied(self):
        """연속 3회 → 2 * 5% 보너스."""
        result = adjust_confidence_by_history(0.7, consecutive_count=3, is_signal_changed=False)
        expected = 0.7 + 2 * CONSECUTIVE_BONUS_PER_COUNT
        self.assertAlmostEqual(result, expected, places=4)

    def test_consecutive_bonus_capped(self):
        """연속 100회 → MAX_CONSECUTIVE_BONUS 상한."""
        result = adjust_confidence_by_history(0.5, consecutive_count=100, is_signal_changed=False)
        self.assertAlmostEqual(result, 0.5 + MAX_CONSECUTIVE_BONUS, places=4)

    def test_signal_change_penalty(self):
        """신호 변화 직후 → 10% 페널티."""
        result = adjust_confidence_by_history(0.7, consecutive_count=1, is_signal_changed=True)
        self.assertAlmostEqual(result, 0.7 - INCONSISTENCY_PENALTY, places=4)

    def test_change_suppresses_consecutive_bonus(self):
        """신호 변화 시 연속 보너스 미적용."""
        result_changed = adjust_confidence_by_history(0.7, consecutive_count=5, is_signal_changed=True)
        result_stable = adjust_confidence_by_history(0.7, consecutive_count=5, is_signal_changed=False)
        self.assertLess(result_changed, result_stable)

    def test_clamped_to_zero(self):
        """아주 낮은 confidence → 0.0 미만 클리핑."""
        result = adjust_confidence_by_history(0.05, consecutive_count=1, is_signal_changed=True)
        self.assertGreaterEqual(result, 0.0)

    def test_clamped_to_one(self):
        """아주 높은 confidence → 1.0 초과 클리핑."""
        result = adjust_confidence_by_history(0.95, consecutive_count=100, is_signal_changed=False)
        self.assertLessEqual(result, 1.0)


class TestAdjustConfidenceByPosition(unittest.TestCase):

    def test_near_target_bonus(self):
        """is_near_target=True → 10% 보너스."""
        result = adjust_confidence_by_position(0.7, 0.75, 0.72, is_near_target=True, phase="BEAR")
        self.assertAlmostEqual(result, 0.7 + NEAR_TARGET_BONUS, places=4)

    def test_not_near_target_no_bonus(self):
        """is_near_target=False → 보너스 없음."""
        result = adjust_confidence_by_position(0.7, 0.75, 0.72, is_near_target=False, phase="BEAR")
        self.assertAlmostEqual(result, 0.7, places=4)

    def test_large_progress_diff_penalty(self):
        """box/day progress 차이 > 0.3 → 페널티."""
        result = adjust_confidence_by_position(0.7, 0.9, 0.3, is_near_target=False, phase="BEAR")
        self.assertLess(result, 0.7)

    def test_small_progress_diff_no_penalty(self):
        """차이 <= 0.3 → 페널티 없음."""
        result = adjust_confidence_by_position(0.7, 0.75, 0.70, is_near_target=False, phase="BEAR")
        self.assertAlmostEqual(result, 0.7, places=4)

    def test_clamped_range(self):
        for near in [True, False]:
            r = adjust_confidence_by_position(0.5, 1.5, 0.0, is_near_target=near, phase="BULL")
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)


class TestComputeFinalConfidence(unittest.TestCase):

    def test_returns_float(self):
        result = compute_final_confidence(0.7, 2, False, 0.7, 0.65, True, "BEAR")
        self.assertIsInstance(result, float)

    def test_in_valid_range(self):
        for base in [0.0, 0.5, 1.0]:
            for count in [1, 5, 20]:
                r = compute_final_confidence(base, count, False, 0.7, 0.7, False, "BEAR")
                self.assertGreaterEqual(r, 0.0)
                self.assertLessEqual(r, 1.0)

    def test_near_target_increases_confidence(self):
        """near_target=True가 False보다 높은 신뢰도."""
        r_near = compute_final_confidence(0.7, 1, False, 0.75, 0.72, True, "BEAR")
        r_far = compute_final_confidence(0.7, 1, False, 0.75, 0.72, False, "BEAR")
        self.assertGreater(r_near, r_far)

    def test_consecutive_increases_confidence(self):
        """연속 신호가 많을수록 신뢰도 높아짐."""
        r_low = compute_final_confidence(0.6, 1, False, 0.7, 0.7, False, "BEAR")
        r_high = compute_final_confidence(0.6, 5, False, 0.7, 0.7, False, "BEAR")
        self.assertGreater(r_high, r_low)


if __name__ == "__main__":
    unittest.main()
