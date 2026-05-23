"""Tests for bear_pattern_matcher.py — Iteration 7."""

import unittest
import math

from lib.predictor.bear_pattern_matcher import _similarity, match_bear_pattern


class TestSimilarity(unittest.TestCase):

    def test_identical_boxes_score_one(self):
        """완전히 동일한 박스 → 유사도 1.0."""
        box = {"decline_intensity": 5.0, "rise_rate": 2.0, "duration": 30}
        score = _similarity(box, box)
        self.assertAlmostEqual(score, 1.0, places=5)

    def test_completely_different_boxes_low_score(self):
        """극단적으로 다른 박스 → 유사도 낮음."""
        cur = {"decline_intensity": 100.0, "rise_rate": 100.0, "duration": 1000}
        ref = {"decline_intensity": 0.001, "rise_rate": 0.001, "duration": 1}
        score = _similarity(cur, ref)
        self.assertLess(score, 0.5)

    def test_none_fields_neutral_weight(self):
        """None 값 필드는 중립 가중치(0.5) 적용 → 점수는 0~1 범위."""
        cur = {"decline_intensity": None, "rise_rate": None, "duration": None}
        ref = {"decline_intensity": None, "rise_rate": None, "duration": None}
        score = _similarity(cur, ref)
        self.assertAlmostEqual(score, 0.5, places=5)

    def test_score_in_range(self):
        """유사도 점수는 항상 0~1 사이."""
        cur = {"decline_intensity": 3.0, "rise_rate": 1.5, "duration": 20}
        ref = {"decline_intensity": 7.0, "rise_rate": 0.5, "duration": 50}
        score = _similarity(cur, ref)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_missing_duration_uses_neutral(self):
        """duration 없으면 중립(0.5) 적용."""
        cur = {"decline_intensity": 5.0, "rise_rate": 2.0}
        ref = {"decline_intensity": 5.0, "rise_rate": 2.0}
        score = _similarity(cur, ref)
        # decline과 rise가 동일 → 각각 1.0 * 가중치, duration 0.5 * 가중치
        # = (0.5*1 + 0.3*1 + 0.2*0.5) / 1.0 = 0.9
        self.assertAlmostEqual(score, 0.9, places=5)


class TestMatchBearPattern(unittest.TestCase):

    def test_empty_current_returns_zero_offset(self):
        """current_boxes가 비면 fallback=0."""
        offset, score = match_bear_pattern([], [{"decline_intensity": 1.0}])
        self.assertEqual(offset, 0)
        self.assertAlmostEqual(score, 0.0)

    def test_empty_ref_returns_count_offset(self):
        """ref_boxes가 비면 fallback = len(current_boxes)."""
        cur = [{"decline_intensity": 1.0}, {"decline_intensity": 2.0}]
        offset, score = match_bear_pattern(cur, [])
        self.assertEqual(offset, 2)
        self.assertAlmostEqual(score, 0.0)

    def test_both_empty_returns_zero(self):
        """둘 다 비면 fallback=0."""
        offset, score = match_bear_pattern([], [])
        self.assertEqual(offset, 0)

    def test_best_match_returns_next_offset(self):
        """마지막 cur 박스와 가장 유사한 ref 박스 찾은 뒤 +1 오프셋."""
        cur = [{"decline_intensity": 5.0, "rise_rate": 2.0, "duration": 30}]
        ref = [
            {"decline_intensity": 1.0, "rise_rate": 0.1, "duration": 5},    # 유사도 낮음
            {"decline_intensity": 5.1, "rise_rate": 2.1, "duration": 31},   # 유사도 높음 → idx=1
            {"decline_intensity": 2.0, "rise_rate": 0.5, "duration": 10},
        ]
        offset, score = match_bear_pattern(cur, ref)
        # 가장 유사한 ref는 idx=1 → offset = 2
        self.assertEqual(offset, 2)
        self.assertGreater(score, 0.9)

    def test_single_ref_always_matched(self):
        """ref가 1개면 항상 그 박스가 매핑 → offset=1."""
        cur = [{"decline_intensity": 1.0}]
        ref = [{"decline_intensity": 99.0}]
        offset, score = match_bear_pattern(cur, ref)
        self.assertEqual(offset, 1)

    def test_offset_type_is_int(self):
        """오프셋은 정수 타입."""
        cur = [{"decline_intensity": 3.0, "rise_rate": 1.0, "duration": 20}]
        ref = [{"decline_intensity": 3.0, "rise_rate": 1.0, "duration": 20}]
        offset, _ = match_bear_pattern(cur, ref)
        self.assertIsInstance(offset, int)

    def test_score_type_is_float(self):
        """유사도 점수는 float."""
        cur = [{"decline_intensity": 3.0}]
        ref = [{"decline_intensity": 3.0}]
        _, score = match_bear_pattern(cur, ref)
        self.assertIsInstance(score, float)


if __name__ == "__main__":
    unittest.main()
