"""Tests for subbox/predict.py — Iteration 18.

_candidate_role 판정 로직 및 generate_sub_box_candidate 기본 케이스.
"""

import unittest

from lib.subbox.predict import _candidate_role, generate_sub_box_candidate


def _make_sub_box(upper=50.0, lower=40.0, sub_index=0, is_completed=0,
                  breakout_up=None, breakdown=None, start_x=100, end_x=110):
    bu = breakout_up if breakout_up is not None else upper * 1.005
    bd = breakdown if breakdown is not None else lower * 0.995
    return {
        "upper": upper, "lower": lower,
        "breakout_up_level": bu, "breakdown_level": bd,
        "sub_box_index": sub_index,
        "is_completed": is_completed,
        "start_x": start_x, "end_x": end_x,
        "range_pct": (upper - lower) / lower * 100.0 if lower > 0 else 0.0,
    }


class TestCandidateRole(unittest.TestCase):

    def test_breakout_watch(self):
        """close >= breakout_up_level → breakout_watch."""
        box = _make_sub_box(upper=50.0, lower=40.0, breakout_up=50.25)
        role = _candidate_role(box, current_close=51.0, previous_sub_box=None,
                               proximity_ratio=0.2, compression_ratio=0.75)
        self.assertEqual(role, "breakout_watch")

    def test_breakdown_watch(self):
        """close <= breakdown_level → breakdown_watch."""
        box = _make_sub_box(upper=50.0, lower=40.0, breakdown=39.8)
        role = _candidate_role(box, current_close=39.0, previous_sub_box=None,
                               proximity_ratio=0.2, compression_ratio=0.75)
        self.assertEqual(role, "breakdown_watch")

    def test_upper_test(self):
        """close 상단 20% 이내 → upper_test."""
        box = _make_sub_box(upper=50.0, lower=40.0, breakout_up=50.25, breakdown=39.8)
        # width=10, proximity 상단 = 50 - 10*0.2 = 48
        role = _candidate_role(box, current_close=49.0, previous_sub_box=None,
                               proximity_ratio=0.2, compression_ratio=0.75)
        self.assertEqual(role, "upper_test")

    def test_lower_test(self):
        """close 하단 20% 이내 → lower_test."""
        box = _make_sub_box(upper=50.0, lower=40.0, breakout_up=50.25, breakdown=39.8)
        # width=10, proximity 하단 = 40 + 10*0.2 = 42
        role = _candidate_role(box, current_close=41.0, previous_sub_box=None,
                               proximity_ratio=0.2, compression_ratio=0.75)
        self.assertEqual(role, "lower_test")

    def test_compression(self):
        """현재 range가 이전 대비 75% 이하 → compression."""
        prev_box = _make_sub_box(upper=60.0, lower=40.0)  # range=50%
        cur_box = _make_sub_box(upper=52.0, lower=48.0, breakout_up=52.26, breakdown=47.76)  # range=8.33%
        role = _candidate_role(cur_box, current_close=50.0, previous_sub_box=prev_box,
                               proximity_ratio=0.05, compression_ratio=0.75)
        self.assertEqual(role, "compression")

    def test_range_continuation_default(self):
        """다른 조건 미충족 → range_continuation."""
        box = _make_sub_box(upper=50.0, lower=40.0, breakout_up=50.25, breakdown=39.8)
        role = _candidate_role(box, current_close=45.0, previous_sub_box=None,
                               proximity_ratio=0.1, compression_ratio=0.75)
        self.assertEqual(role, "range_continuation")


class TestGenerateSubBoxCandidate(unittest.TestCase):

    def _make_parent(self, result="ACTIVE"):
        return {
            "box_index": 2, "phase": "BEAR", "result": result,
            "start_x": 100, "end_x": 200,
        }

    def _make_data(self):
        return [{"x": i, "high": 50.0, "low": 40.0, "close": 45.0}
                for i in range(100, 121)]

    def test_non_active_parent_returns_none(self):
        parent = self._make_parent(result="COMPLETED")
        result = generate_sub_box_candidate([], parent, self._make_data())
        self.assertIsNone(result)

    def test_no_active_sub_boxes_returns_none(self):
        """active sub_boxes 없으면 None."""
        sub_boxes = [_make_sub_box(is_completed=1)]  # 완료된 것만
        result = generate_sub_box_candidate(sub_boxes, self._make_parent(), self._make_data())
        self.assertIsNone(result)

    def test_returns_candidate_dict(self):
        """active sub_box 있으면 candidate dict 반환."""
        sub_boxes = [_make_sub_box(sub_index=0, is_completed=0, start_x=100, end_x=110)]
        result = generate_sub_box_candidate(sub_boxes, self._make_parent(), self._make_data())
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_candidate_is_prediction(self):
        """candidate의 is_prediction=1."""
        sub_boxes = [_make_sub_box(sub_index=0, is_completed=0, start_x=100, end_x=110)]
        result = generate_sub_box_candidate(sub_boxes, self._make_parent(), self._make_data())
        if result:
            self.assertEqual(result.get("is_prediction"), 1)


if __name__ == "__main__":
    unittest.main()
