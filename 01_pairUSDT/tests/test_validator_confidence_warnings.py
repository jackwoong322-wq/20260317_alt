"""Iter 34: validate_signal_result confidence 경고 테스트."""

import unittest
from lib.predictor.btc_signal_validator import validate_signal_result
from lib.predictor.btc_investment_signal import SignalResult


def _make_result(signal="ACCUMULATE", phase="BEAR", confidence=0.75,
                 box_prog=0.7, price_pos=0.25, dist=5.0, near=True):
    return SignalResult(
        signal=signal, phase=phase, confidence=confidence,
        reason=["test reason"],
        box_progress_ratio=box_prog, price_position=price_pos,
        distance_to_target_pct=dist, is_near_target=near,
    )


class TestValidatorConfidenceWarnings(unittest.TestCase):

    def test_normal_confidence_no_warning(self):
        r = validate_signal_result(_make_result(confidence=0.7))
        self.assertTrue(r.is_valid)
        self.assertEqual(r.warnings, [])

    def test_low_confidence_adds_warning(self):
        r = validate_signal_result(_make_result(confidence=0.2))
        self.assertTrue(r.is_valid)  # 경고지 에러 아님
        self.assertEqual(len(r.warnings), 1)
        self.assertIn("low", r.warnings[0])

    def test_high_confidence_adds_warning(self):
        r = validate_signal_result(_make_result(confidence=0.98))
        self.assertTrue(r.is_valid)
        self.assertEqual(len(r.warnings), 1)
        self.assertIn("suspiciously high", r.warnings[0])

    def test_boundary_low_no_warning(self):
        """0.3 경계값은 경고 없음."""
        r = validate_signal_result(_make_result(confidence=0.3))
        low_warns = [w for w in r.warnings if "low" in w]
        self.assertEqual(low_warns, [])

    def test_boundary_high_no_warning(self):
        """0.95 경계값은 경고 없음."""
        r = validate_signal_result(_make_result(confidence=0.95))
        high_warns = [w for w in r.warnings if "suspiciously" in w]
        self.assertEqual(high_warns, [])

    def test_zero_confidence_adds_low_warning(self):
        r = validate_signal_result(_make_result(confidence=0.0))
        self.assertTrue(r.is_valid)
        low_warns = [w for w in r.warnings if "low" in w]
        self.assertEqual(len(low_warns), 1)

    def test_one_confidence_adds_high_warning(self):
        r = validate_signal_result(_make_result(confidence=1.0))
        high_warns = [w for w in r.warnings if "suspiciously" in w]
        self.assertEqual(len(high_warns), 1)

    def test_invalid_confidence_is_error_not_warning(self):
        r = validate_signal_result(_make_result(confidence=1.5))
        self.assertFalse(r.is_valid)
        self.assertTrue(any("out of" in e for e in r.errors))


if __name__ == "__main__":
    unittest.main()
