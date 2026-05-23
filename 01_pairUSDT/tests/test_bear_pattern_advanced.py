"""Iters 76-80: bear_pattern_matcher 심화 테스트 (실제 API 기반)."""

import unittest
import math
from lib.predictor.bear_pattern_matcher import (
    _similarity,
    match_bear_pattern,
)


def _box(decline=5.0, rise=2.0, duration=50):
    return {"decline_intensity": decline, "rise_rate": rise,
            "duration": duration, "box_index": 0}


class TestSimilarityFunction(unittest.TestCase):
    """Iter 76-77: _similarity 순수함수 테스트."""

    def test_identical_boxes_high_score(self):
        b = _box()
        score = _similarity(b, b)
        self.assertGreaterEqual(score, 0.9)

    def test_very_different_boxes_low_score(self):
        cur = _box(decline=1.0, rise=1.0, duration=10)
        ref = _box(decline=100.0, rise=100.0, duration=1000)
        score = _similarity(cur, ref)
        self.assertLess(score, 0.5)

    def test_score_in_zero_one_range(self):
        for d in [1.0, 5.0, 20.0]:
            score = _similarity(_box(decline=d), _box(decline=d * 2))
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_missing_fields_neutral(self):
        """값이 없으면 0.5 중립점 적용."""
        score = _similarity({}, {})
        self.assertAlmostEqual(score, 0.5, places=5)

    def test_symmetry(self):
        """유사도는 교환 법칙 성립."""
        a = _box(decline=3.0, rise=1.5, duration=40)
        b = _box(decline=6.0, rise=3.0, duration=80)
        self.assertAlmostEqual(_similarity(a, b), _similarity(b, a), places=10)


class TestMatchBearPattern(unittest.TestCase):
    """Iter 78-80: match_bear_pattern 통합 테스트."""

    def test_empty_current_returns_fallback(self):
        ref = [_box(), _box(decline=8.0)]
        offset, score = match_bear_pattern([], ref)
        self.assertEqual(offset, 0)
        self.assertEqual(score, 0.0)

    def test_empty_ref_returns_fallback(self):
        cur = [_box()]
        offset, score = match_bear_pattern(cur, [])
        self.assertEqual(offset, len(cur))
        self.assertEqual(score, 0.0)

    def test_both_empty_returns_zero(self):
        offset, score = match_bear_pattern([], [])
        self.assertEqual(offset, 0)
        self.assertEqual(score, 0.0)

    def test_match_returns_tuple(self):
        cur = [_box()]
        ref = [_box(), _box(decline=8.0), _box(decline=12.0)]
        result = match_bear_pattern(cur, ref)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_score_in_range(self):
        cur = [_box(decline=5.0)]
        ref = [_box(decline=5.0), _box(decline=10.0)]
        _, score = match_bear_pattern(cur, ref)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_perfect_match_high_score(self):
        """동일한 박스끼리 매칭하면 유사도 높아야 한다."""
        box = _box(decline=7.0, rise=3.0, duration=60)
        cur = [box]
        ref = [box, _box(decline=20.0)]
        _, score = match_bear_pattern(cur, ref)
        self.assertGreaterEqual(score, 0.8)

    def test_offset_points_after_best_match(self):
        """매핑된 ref 인덱스+1이 offset이어야 한다."""
        cur = [_box(decline=5.0)]
        ref = [_box(decline=50.0), _box(decline=5.0), _box(decline=30.0)]
        offset, score = match_bear_pattern(cur, ref)
        # ref[1]이 가장 유사 → offset=2
        self.assertEqual(offset, 2)


if __name__ == "__main__":
    unittest.main()
