"""Unit tests for lib.common.utils pure functions.

DevLoop Iteration 2 — common utils 커버리지 확보
"""
import sys
import os
import math
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lib.common.utils import (
    signed_log1p,
    _signed_log1p,
    safe_log1p,
    _log1p,
    safe_range_pct,
    _safe_div_pct,
    _ease_in_out,
    _wave_offset,
)


class TestSignedLog1p(unittest.TestCase):
    def test_positive_value(self):
        result = signed_log1p(1.0)
        self.assertAlmostEqual(result, math.log1p(1.0))

    def test_negative_value(self):
        result = signed_log1p(-1.0)
        self.assertAlmostEqual(result, -math.log1p(1.0))

    def test_zero(self):
        self.assertAlmostEqual(signed_log1p(0.0), 0.0)

    def test_none_returns_none(self):
        self.assertIsNone(signed_log1p(None))

    def test_private_variant_matches(self):
        """_signed_log1p와 signed_log1p는 동일해야 한다."""
        for v in [-10.0, -1.0, 0.0, 1.0, 10.0]:
            self.assertAlmostEqual(_signed_log1p(v), signed_log1p(v))

    def test_private_none_returns_none(self):
        self.assertIsNone(_signed_log1p(None))


class TestSafeLog1p(unittest.TestCase):
    def test_positive_value(self):
        self.assertAlmostEqual(safe_log1p(1.0), math.log1p(1.0))

    def test_zero(self):
        self.assertAlmostEqual(safe_log1p(0.0), 0.0)

    def test_none_returns_none(self):
        self.assertIsNone(safe_log1p(None))

    def test_negative_returns_none(self):
        """음수 입력 시 None 반환 (안전 로직)."""
        self.assertIsNone(safe_log1p(-0.1))

    def test_log1p_positive(self):
        self.assertAlmostEqual(_log1p(1.0), math.log1p(1.0))

    def test_log1p_none_returns_none(self):
        self.assertIsNone(_log1p(None))

    def test_log1p_negative_clamps_to_zero(self):
        """_log1p: 음수는 0으로 클램프 후 log1p(0) = 0."""
        self.assertAlmostEqual(_log1p(-5.0), 0.0)


class TestSafeRangePct(unittest.TestCase):
    def test_normal_case(self):
        """(hi - lo) / lo * 100."""
        result = safe_range_pct(110.0, 100.0)
        self.assertAlmostEqual(result, 10.0)

    def test_lo_zero_returns_zero(self):
        """lo=0이면 ZeroDivision 방지로 0 반환."""
        self.assertEqual(safe_range_pct(100.0, 0.0), 0.0)

    def test_equal_hi_lo(self):
        self.assertAlmostEqual(safe_range_pct(50.0, 50.0), 0.0)


class TestSafeDivPct(unittest.TestCase):
    def test_normal(self):
        result = _safe_div_pct(110.0, 100.0)
        self.assertAlmostEqual(result, 10.0)

    def test_denom_zero_returns_zero(self):
        self.assertEqual(_safe_div_pct(100.0, 0.0), 0.0)

    def test_denom_none_returns_zero(self):
        self.assertEqual(_safe_div_pct(100.0, None), 0.0)

    def test_negative_result(self):
        result = _safe_div_pct(90.0, 100.0)
        self.assertAlmostEqual(result, -10.0)


class TestEaseInOut(unittest.TestCase):
    def test_at_zero(self):
        self.assertAlmostEqual(_ease_in_out(0.0), 0.0)

    def test_at_one(self):
        self.assertAlmostEqual(_ease_in_out(1.0), 1.0)

    def test_at_half(self):
        """t=0.5: 0.5^2 * (3 - 2*0.5) = 0.25 * 2 = 0.5."""
        self.assertAlmostEqual(_ease_in_out(0.5), 0.5)

    def test_clamped_below_zero(self):
        """t < 0 이면 0으로 클램프."""
        self.assertAlmostEqual(_ease_in_out(-1.0), 0.0)

    def test_clamped_above_one(self):
        """t > 1 이면 1로 클램프."""
        self.assertAlmostEqual(_ease_in_out(2.0), 1.0)

    def test_output_in_range(self):
        """임의 t에서 결과가 [0,1] 범위."""
        for t in [0.1, 0.25, 0.75, 0.9]:
            v = _ease_in_out(t)
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)


class TestWaveOffset(unittest.TestCase):
    def test_zero_segment_days(self):
        """segment_days=0이면 0 반환."""
        self.assertEqual(_wave_offset(5, 0, 0), 0.0)

    def test_at_start(self):
        """day == day_start (progress=0): sin(0) = 0."""
        result = _wave_offset(0, 0, 10, amplitude_pct=3.0)
        self.assertAlmostEqual(result, 0.0)

    def test_output_bounded(self):
        """기본 amplitude_pct=3% 기준 ±0.03 범위 내."""
        for day in range(0, 11):
            v = _wave_offset(day, 0, 10, amplitude_pct=3.0)
            self.assertLessEqual(abs(v), 0.03 + 1e-9)

    def test_amplitude_scales(self):
        """amplitude_pct가 클수록 최대값도 커진다."""
        v_small = abs(_wave_offset(2, 0, 10, amplitude_pct=1.0))
        v_large = abs(_wave_offset(2, 0, 10, amplitude_pct=10.0))
        # 동일 position에서 amplitude만 다르면 비례
        self.assertAlmostEqual(v_large / v_small, 10.0, places=5)


if __name__ == "__main__":
    unittest.main()
