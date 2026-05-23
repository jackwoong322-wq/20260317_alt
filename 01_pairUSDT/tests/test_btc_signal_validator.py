"""Tests for btc_signal_validator.py — Iteration 25."""

import unittest

from lib.predictor.btc_investment_signal import SignalResult, SIGNAL_ACCUMULATE, SIGNAL_WATCH
from lib.predictor.btc_signal_validator import (
    validate_signal_result, ValidationReport, VALID_SIGNALS, VALID_PHASES,
)


def _make_valid_signal():
    return SignalResult(
        signal=SIGNAL_ACCUMULATE, phase="BEAR", confidence=0.85,
        reason=["box_progress=80%", "near_bottom=True"],
        box_progress_ratio=0.8, price_position=0.2,
        distance_to_target_pct=-8.0, is_near_target=True,
    )


class TestValidateSignalResult(unittest.TestCase):

    def test_valid_signal_passes(self):
        report = validate_signal_result(_make_valid_signal())
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.errors), 0)

    def test_none_returns_invalid(self):
        report = validate_signal_result(None)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("None" in e for e in report.errors))

    def test_invalid_signal_value(self):
        sig = _make_valid_signal()
        sig.signal = "BUY"  # 유효하지 않은 값
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("invalid signal" in e for e in report.errors))

    def test_confidence_out_of_range_low(self):
        sig = _make_valid_signal()
        sig.confidence = -0.1
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)

    def test_confidence_out_of_range_high(self):
        sig = _make_valid_signal()
        sig.confidence = 1.1
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)

    def test_negative_box_progress(self):
        sig = _make_valid_signal()
        sig.box_progress_ratio = -0.1
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)

    def test_large_box_progress_is_warning(self):
        """box_progress > 2.0 → 에러 아닌 경고."""
        sig = _make_valid_signal()
        sig.box_progress_ratio = 2.5
        report = validate_signal_result(sig)
        self.assertTrue(report.is_valid)  # 경고만, 에러 아님
        self.assertTrue(any("2.0" in w for w in report.warnings))

    def test_invalid_price_position(self):
        sig = _make_valid_signal()
        sig.price_position = 1.5
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)

    def test_empty_reason_is_error(self):
        sig = _make_valid_signal()
        sig.reason = []
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)

    def test_invalid_phase(self):
        sig = _make_valid_signal()
        sig.phase = "NEUTRAL"
        report = validate_signal_result(sig)
        self.assertFalse(report.is_valid)

    def test_multiple_errors_accumulated(self):
        """여러 오류 동시 감지."""
        sig = _make_valid_signal()
        sig.signal = "INVALID"
        sig.confidence = 1.5
        sig.phase = "NEUTRAL"
        report = validate_signal_result(sig)
        self.assertGreaterEqual(len(report.errors), 3)

    def test_validation_report_is_instance(self):
        report = validate_signal_result(_make_valid_signal())
        self.assertIsInstance(report, ValidationReport)

    def test_all_valid_signals_pass(self):
        """모든 4가지 유효 신호 통과."""
        for signal_val in VALID_SIGNALS:
            sig = _make_valid_signal()
            sig.signal = signal_val
            report = validate_signal_result(sig)
            self.assertTrue(report.is_valid, f"{signal_val} failed")

    def test_both_phases_pass(self):
        """BEAR, BULL 둘 다 통과."""
        for phase in VALID_PHASES:
            sig = _make_valid_signal()
            sig.phase = phase
            report = validate_signal_result(sig)
            self.assertTrue(report.is_valid, f"{phase} failed")


if __name__ == "__main__":
    unittest.main()
