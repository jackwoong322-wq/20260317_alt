"""Iters 56-60: confidence scorer 파라미터 조합 + 검증 통합 테스트."""

import unittest
from lib.predictor.btc_signal_confidence_scorer import (
    adjust_confidence_by_history,
    adjust_confidence_by_position,
    compute_final_confidence,
)
from lib.predictor.btc_signal_validator import validate_signal_result
from lib.predictor.btc_investment_signal import SignalResult


def _make_result(confidence=0.75):
    return SignalResult(
        signal="ACCUMULATE", phase="BEAR", confidence=confidence,
        reason=["test"], box_progress_ratio=0.7,
        price_position=0.25, distance_to_target_pct=5.0, is_near_target=True,
    )


class TestConfidenceScorerCombinations(unittest.TestCase):
    """Iter 56-58: 파라미터 조합 테스트."""

    def test_history_bonus_max_capped(self):
        """연속 100회여도 MAX_CONSECUTIVE_BONUS만큼만 올라간다."""
        from lib.predictor.btc_signal_confidence_scorer import MAX_CONSECUTIVE_BONUS
        base = 0.5
        result = adjust_confidence_by_history(base, consecutive_count=100, is_signal_changed=False)
        self.assertAlmostEqual(result, base + MAX_CONSECUTIVE_BONUS, places=5)

    def test_history_change_penalty_and_bonus_cancel(self):
        """변화(is_changed=True) + 연속(count>1)이 동시에 오면 페널티만 적용."""
        base = 0.6
        # is_signal_changed=True이면 보너스 미적용 + 페널티 적용
        result = adjust_confidence_by_history(base, consecutive_count=5, is_signal_changed=True)
        self.assertLess(result, base)

    def test_position_near_target_bonus(self):
        from lib.predictor.btc_signal_confidence_scorer import NEAR_TARGET_BONUS
        base = 0.5
        result = adjust_confidence_by_position(base, 0.7, 0.7, is_near_target=True, phase="BEAR")
        self.assertAlmostEqual(result, base + NEAR_TARGET_BONUS, places=5)

    def test_position_inconsistency_penalty(self):
        """box_progress=0.7, day_progress=0.2 → 차이 0.5 > 0.3 → 페널티."""
        base = 0.7
        result = adjust_confidence_by_position(base, 0.7, 0.2, is_near_target=False, phase="BEAR")
        self.assertLess(result, base)

    def test_compute_final_always_in_range(self):
        for base in [0.0, 0.3, 0.6, 0.9, 1.0]:
            result = compute_final_confidence(
                base_confidence=base, consecutive_count=3, is_signal_changed=False,
                box_progress_ratio=0.7, day_progress_ratio=0.7,
                is_near_target=True, phase="BEAR",
            )
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.0)

    def test_compute_final_with_change_penalty(self):
        base = 0.8
        stable = compute_final_confidence(
            base, 3, False, 0.7, 0.7, True, "BEAR"
        )
        changed = compute_final_confidence(
            base, 3, True, 0.7, 0.7, True, "BEAR"
        )
        self.assertGreater(stable, changed)

    def test_compute_final_bull_same_as_bear_logic(self):
        """Bull/Bear 모두 동일한 scorer 로직 적용."""
        r_bear = compute_final_confidence(0.7, 2, False, 0.6, 0.6, True, "BEAR")
        r_bull = compute_final_confidence(0.7, 2, False, 0.6, 0.6, True, "BULL")
        self.assertAlmostEqual(r_bear, r_bull, places=5)


class TestValidatorWithScoredResult(unittest.TestCase):
    """Iter 59-60: scorer 적용 후 validator 통합."""

    def test_scored_result_passes_validator(self):
        from lib.predictor.btc_signal_confidence_scorer import compute_final_confidence
        r = _make_result(confidence=0.7)
        adjusted = compute_final_confidence(
            0.7, 3, False, 0.7, 0.7, True, "BEAR"
        )
        r.confidence = adjusted
        report = validate_signal_result(r)
        self.assertTrue(report.is_valid)

    def test_high_scored_confidence_gives_warning(self):
        from lib.predictor.btc_signal_confidence_scorer import compute_final_confidence
        r = _make_result(confidence=1.0)
        r.confidence = 1.0  # max score
        report = validate_signal_result(r)
        self.assertTrue(report.is_valid)
        # confidence=1.0 > 0.95 → warning
        high_warns = [w for w in report.warnings if "suspiciously" in w]
        self.assertEqual(len(high_warns), 1)

    def test_low_scored_confidence_gives_warning(self):
        r = _make_result(confidence=0.1)
        report = validate_signal_result(r)
        self.assertTrue(report.is_valid)
        low_warns = [w for w in report.warnings if "low" in w]
        self.assertEqual(len(low_warns), 1)


if __name__ == "__main__":
    unittest.main()
