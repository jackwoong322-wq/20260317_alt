"""Iters 66-70: ValidationReport 메서드 + CyclePosition 복합 테스트."""

import unittest
from lib.predictor.btc_signal_validator import ValidationReport, validate_signal_result
from lib.predictor.btc_investment_signal import SignalResult
from lib.predictor.btc_cycle_position import (
    calc_bear_box_progress, calc_bull_box_progress,
    calc_price_position, calc_distance_to_target,
)


def _make_result(**kw):
    defaults = dict(
        signal="ACCUMULATE", phase="BEAR", confidence=0.75,
        reason=["ok"], box_progress_ratio=0.7,
        price_position=0.25, distance_to_target_pct=5.0, is_near_target=True,
    )
    defaults.update(kw)
    return SignalResult(**defaults)


class TestValidationReport(unittest.TestCase):
    """Iter 66-67: ValidationReport 메서드 직접 테스트."""

    def test_add_error_sets_invalid(self):
        r = ValidationReport(is_valid=True)
        r.add_error("test error")
        self.assertFalse(r.is_valid)
        self.assertIn("test error", r.errors)

    def test_add_warning_keeps_valid(self):
        r = ValidationReport(is_valid=True)
        r.add_warning("test warn")
        self.assertTrue(r.is_valid)
        self.assertIn("test warn", r.warnings)

    def test_multiple_errors(self):
        r = ValidationReport(is_valid=True)
        r.add_error("e1")
        r.add_error("e2")
        self.assertEqual(len(r.errors), 2)
        self.assertFalse(r.is_valid)

    def test_no_errors_no_warnings(self):
        r = validate_signal_result(_make_result())
        self.assertTrue(r.is_valid)
        self.assertEqual(r.errors, [])

    def test_invalid_signal_gives_error(self):
        r = validate_signal_result(_make_result(signal="INVALID"))
        self.assertFalse(r.is_valid)

    def test_negative_box_progress_error(self):
        r = validate_signal_result(_make_result(box_progress_ratio=-0.1))
        self.assertFalse(r.is_valid)

    def test_empty_reason_error(self):
        r = validate_signal_result(_make_result(reason=[]))
        self.assertFalse(r.is_valid)

    def test_price_position_out_of_range(self):
        r = validate_signal_result(_make_result(price_position=1.5))
        self.assertFalse(r.is_valid)


class TestCyclePositionPureFunctions(unittest.TestCase):
    """Iter 68-70: CyclePosition 순수함수 추가 테스트."""

    def test_bear_progress_zero_avg(self):
        """avg=0이면 0.0 반환 (ZeroDivision 방지)."""
        self.assertEqual(calc_bear_box_progress(5, 0), 0.0)

    def test_bull_progress_zero_avg(self):
        self.assertEqual(calc_bull_box_progress(5, 0), 0.0)

    def test_bear_progress_exact(self):
        self.assertAlmostEqual(calc_bear_box_progress(3, 10), 0.3)

    def test_bull_progress_over_one(self):
        r = calc_bull_box_progress(12, 10)
        self.assertGreater(r, 1.0)

    def test_price_position_below_lo(self):
        """가격이 lo 아래면 0.0으로 클리핑."""
        self.assertEqual(calc_price_position(5.0, 10.0, 20.0), 0.0)

    def test_price_position_above_hi(self):
        """가격이 hi 위면 1.0으로 클리핑."""
        self.assertEqual(calc_price_position(25.0, 10.0, 20.0), 1.0)

    def test_price_position_midpoint(self):
        self.assertAlmostEqual(calc_price_position(15.0, 10.0, 20.0), 0.5)

    def test_price_position_equal_lo_hi(self):
        """lo == hi이면 0.5 반환."""
        self.assertEqual(calc_price_position(10.0, 10.0, 10.0), 0.5)

    def test_distance_to_target_zero_current(self):
        """current=0이면 0.0 반환."""
        self.assertEqual(calc_distance_to_target(0.0, 15.0), 0.0)

    def test_distance_positive_when_target_above(self):
        """목표가 > 현재가 → 양수."""
        d = calc_distance_to_target(20.0, 25.0)
        self.assertGreater(d, 0)

    def test_distance_negative_when_target_below(self):
        """목표가 < 현재가 → 음수."""
        d = calc_distance_to_target(20.0, 15.0)
        self.assertLess(d, 0)


if __name__ == "__main__":
    unittest.main()
