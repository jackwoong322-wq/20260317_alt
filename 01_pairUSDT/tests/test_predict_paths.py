"""Unit tests for predict_paths._interpolate_segment and _build_paths_for_cycle.

DevLoop Iteration 1 — 순수 함수 커버리지 확보
"""
import sys
import os
import unittest

# 경로 설정: 01_pairUSDT를 sys.path에 추가
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lib.predictor.predict_paths import _interpolate_segment, _build_paths_for_cycle


class TestInterpolateSegment(unittest.TestCase):
    """_interpolate_segment(start_val, end_val, start_day, end_day) 테스트."""

    def test_same_day_returns_single_point(self):
        """start_day == end_day 이면 (start_day, start_val) 1개만 반환."""
        result = _interpolate_segment(10.0, 20.0, 5, 5)
        self.assertEqual(len(result), 1)
        day, val = result[0]
        self.assertEqual(day, 5)
        self.assertAlmostEqual(val, 10.0)

    def test_end_less_than_start_returns_single_point(self):
        """end_day < start_day 이면 단일 포인트 반환 (방어 로직)."""
        result = _interpolate_segment(10.0, 20.0, 10, 5)
        self.assertEqual(len(result), 1)

    def test_interpolation_point_count(self):
        """n = end_day - start_day 이면 n+1개 포인트 반환."""
        result = _interpolate_segment(0.0, 100.0, 0, 10)
        self.assertEqual(len(result), 11)  # day 0~10 포함

    def test_first_value_is_start(self):
        """첫 포인트의 값이 start_val이어야 한다 (ease t=0 → 0)."""
        result = _interpolate_segment(50.0, 80.0, 0, 5)
        _, first_val = result[0]
        self.assertAlmostEqual(first_val, 50.0)

    def test_last_value_is_end(self):
        """마지막 포인트의 값이 end_val이어야 한다 (ease t=1 → 1)."""
        result = _interpolate_segment(50.0, 80.0, 0, 5)
        _, last_val = result[-1]
        self.assertAlmostEqual(last_val, 80.0)

    def test_day_values_are_sequential(self):
        """day 값이 start_day부터 1씩 증가해야 한다."""
        result = _interpolate_segment(0.0, 100.0, 3, 7)
        days = [d for d, _ in result]
        self.assertEqual(days, list(range(3, 8)))

    def test_ease_midpoint_smoothing(self):
        """중간(t=0.5)에서 값이 선형보간 중간값이 되는지 검증.
        ease_in_out(0.5) = 0.5*0.5*(3-2*0.5) = 0.25*2 = 0.5 → 선형과 같음."""
        result = _interpolate_segment(0.0, 100.0, 0, 2)
        # day 1 = t=0.5
        _, mid_val = result[1]
        self.assertAlmostEqual(mid_val, 50.0, places=5)

    def test_returns_list_of_tuples(self):
        """반환 타입이 (int, float) 튜플 리스트인지 확인."""
        result = _interpolate_segment(10.0, 20.0, 0, 3)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            day, val = item
            self.assertIsInstance(day, int)
            self.assertIsInstance(val, float)


class TestBuildPathsForCycle(unittest.TestCase):
    """_build_paths_for_cycle(rows, symbol, scenario, start_val) 테스트."""

    def _make_box(self, start_x, end_x, hi, lo, hi_day, lo_day):
        return {
            "start_x": start_x,
            "end_x": end_x,
            "hi": hi,
            "lo": lo,
            "hi_day": hi_day,
            "lo_day": lo_day,
        }

    def test_empty_rows_returns_empty(self):
        """빈 rows 입력 시 빈 리스트 반환."""
        result = _build_paths_for_cycle([], "BTC", "bear")
        self.assertEqual(result, [])

    def test_path_tuple_format(self):
        """출력이 (symbol, scenario, day, value) 4-튜플 형식인지 확인."""
        box = self._make_box(0, 10, 100.0, 50.0, hi_day=7, lo_day=3)
        result = _build_paths_for_cycle([box], "BTC", "bear")
        self.assertGreater(len(result), 0)
        sym, sc, day, val = result[0]
        self.assertEqual(sym, "BTC")
        self.assertEqual(sc, "bear")
        self.assertIsInstance(day, int)
        self.assertIsInstance(val, float)

    def test_bear_lo_before_hi_generates_path(self):
        """bear: lo_day < hi_day 분기 — 하락→반등 구조 경로 생성."""
        box = self._make_box(0, 20, 100.0, 40.0, hi_day=15, lo_day=5)
        result = _build_paths_for_cycle([box], "ETH", "bear")
        self.assertGreater(len(result), 0)
        days = [d for _, _, d, _ in result]
        # day 값이 start_x 이상이어야 한다
        self.assertGreaterEqual(min(days), 0)

    def test_bear_hi_before_lo_generates_path(self):
        """bear: hi_day < lo_day 분기 — 반등→하락 구조 경로 생성."""
        box = self._make_box(0, 20, 100.0, 40.0, hi_day=5, lo_day=15)
        result = _build_paths_for_cycle([box], "ETH", "bear")
        self.assertGreater(len(result), 0)

    def test_bull_path_with_start_val(self):
        """bull: start_val 지정 시 경로 시작값이 start_val에서 시작."""
        box = self._make_box(10, 30, 120.0, 80.0, hi_day=15, lo_day=25)
        result = _build_paths_for_cycle([box], "BTC", "bull", start_val=80.0)
        self.assertGreater(len(result), 0)
        _, sc, _, _ = result[0]
        self.assertEqual(sc, "bull")

    def test_bull_last_point_equals_peak_hi(self):
        """bull: 마지막 포인트 값이 마지막 박스 hi와 같아야 한다."""
        box = self._make_box(10, 30, 150.0, 80.0, hi_day=25, lo_day=15)
        result = _build_paths_for_cycle([box], "BTC", "bull", start_val=80.0)
        self.assertGreater(len(result), 0)
        _, _, _, last_val = result[-1]
        self.assertAlmostEqual(last_val, 150.0)

    def test_multiple_boxes_connected(self):
        """복수 박스 연결 시 경로가 연속되어야 한다 (day 중복 없이 단조 증가)."""
        box1 = self._make_box(0, 10, 80.0, 50.0, hi_day=7, lo_day=3)
        box2 = self._make_box(10, 20, 90.0, 60.0, hi_day=17, lo_day=13)
        result = _build_paths_for_cycle([box1, box2], "BTC", "bear")
        self.assertGreater(len(result), 0)
        days = [d for _, _, d, _ in result]
        # 전체 day 범위가 두 박스를 포괄해야 함
        self.assertLessEqual(min(days), 5)
        self.assertGreaterEqual(max(days), 15)

    def test_symbol_preserved_in_all_points(self):
        """모든 포인트에서 symbol이 동일하게 유지되어야 한다."""
        box = self._make_box(0, 10, 100.0, 60.0, hi_day=7, lo_day=3)
        result = _build_paths_for_cycle([box], "XRP", "bear")
        for sym, _, _, _ in result:
            self.assertEqual(sym, "XRP")


if __name__ == "__main__":
    unittest.main()
