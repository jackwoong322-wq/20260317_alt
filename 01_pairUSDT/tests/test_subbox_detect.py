"""Tests for subbox/detect.py pure functions — Iteration 17.

sub_box_label (A→Z→AA), _range_pct, slice_parent_box_data,
detect_sub_boxes 엔트리 포인트 기본 케이스.
"""

import unittest

from lib.subbox.detect import (
    sub_box_label,
    _range_pct,
    slice_parent_box_data,
    detect_sub_boxes,
)


class TestSubBoxLabel(unittest.TestCase):

    def test_first_labels(self):
        """0→A, 1→B, 25→Z."""
        self.assertEqual(sub_box_label(0), "A")
        self.assertEqual(sub_box_label(1), "B")
        self.assertEqual(sub_box_label(25), "Z")

    def test_two_char_labels(self):
        """26→AA, 27→AB."""
        self.assertEqual(sub_box_label(26), "AA")
        self.assertEqual(sub_box_label(27), "AB")

    def test_negative_raises(self):
        """음수 → ValueError."""
        with self.assertRaises(ValueError):
            sub_box_label(-1)

    def test_labels_unique(self):
        """0~51 범위에서 레이블 중복 없음."""
        labels = [sub_box_label(i) for i in range(52)]
        self.assertEqual(len(labels), len(set(labels)))


class TestRangePct(unittest.TestCase):

    def test_normal(self):
        """(50-40)/40 * 100 = 25%."""
        self.assertAlmostEqual(_range_pct(50.0, 40.0), 25.0)

    def test_zero_lower_returns_zero(self):
        """하단=0이면 0.0."""
        self.assertAlmostEqual(_range_pct(50.0, 0.0), 0.0)

    def test_equal_upper_lower(self):
        """상단=하단 → 0%."""
        self.assertAlmostEqual(_range_pct(30.0, 30.0), 0.0)


class TestSliceParentBoxData(unittest.TestCase):

    def _make_data(self):
        return [
            {"x": 100, "high": 50.0, "low": 40.0, "close": 45.0},
            {"x": 110, "high": 55.0, "low": 42.0, "close": 48.0},
            {"x": 120, "high": 52.0, "low": 38.0, "close": 40.0},
            {"x": 130, "high": 60.0, "low": 50.0, "close": 55.0},
        ]

    def test_slice_within_range(self):
        """start_x~end_x 범위만 반환."""
        data = self._make_data()
        parent = {"start_x": 100, "end_x": 120, "box_index": 0,
                  "phase": "BEAR", "result": "ACTIVE"}
        result = slice_parent_box_data(data, parent)
        self.assertEqual(len(result), 3)  # x=100, 110, 120

    def test_result_sorted_by_x(self):
        """결과는 x 오름차순 정렬."""
        data = list(reversed(self._make_data()))  # 역순
        parent = {"start_x": 100, "end_x": 130, "box_index": 0,
                  "phase": "BEAR", "result": "ACTIVE"}
        result = slice_parent_box_data(data, parent)
        xs = [p["x"] for p in result]
        self.assertEqual(xs, sorted(xs))

    def test_empty_data(self):
        parent = {"start_x": 100, "end_x": 130, "box_index": 0,
                  "phase": "BEAR", "result": "ACTIVE"}
        result = slice_parent_box_data([], parent)
        self.assertEqual(result, [])


class TestDetectSubBoxes(unittest.TestCase):

    def _make_data_points(self, n=20, base=45.0):
        """단조 증가 데이터 생성."""
        return [
            {"x": 100 + i, "high": base + i * 0.5, "low": base - 1.0, "close": base + i * 0.3}
            for i in range(n)
        ]

    def test_non_active_returns_empty(self):
        """result != ACTIVE → 빈 리스트."""
        parent = {"start_x": 100, "end_x": 120, "box_index": 0,
                  "phase": "BEAR", "result": "COMPLETED"}
        result = detect_sub_boxes(self._make_data_points(), parent)
        self.assertEqual(result, [])

    def test_too_few_points_returns_empty(self):
        """min_duration 미달 데이터 → 빈 리스트."""
        data = self._make_data_points(n=3)
        parent = {"start_x": 100, "end_x": 102, "box_index": 0,
                  "phase": "BEAR", "result": "ACTIVE"}
        result = detect_sub_boxes(data, parent, min_duration=5)
        self.assertEqual(result, [])

    def test_returns_list(self):
        """정상 데이터 → 리스트 반환."""
        data = self._make_data_points(n=20)
        parent = {"start_x": 100, "end_x": 119, "box_index": 0,
                  "phase": "BEAR", "result": "ACTIVE"}
        result = detect_sub_boxes(data, parent)
        self.assertIsInstance(result, list)

    def test_invalid_min_duration_raises(self):
        """min_duration <= 1 → ValueError."""
        data = self._make_data_points()
        parent = {"start_x": 100, "end_x": 119, "box_index": 0,
                  "phase": "BEAR", "result": "ACTIVE"}
        with self.assertRaises(ValueError):
            detect_sub_boxes(data, parent, min_duration=1)


if __name__ == "__main__":
    unittest.main()
