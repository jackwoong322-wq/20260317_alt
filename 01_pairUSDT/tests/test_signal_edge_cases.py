"""Tests for Iteration 13 강화 로직 — over-average progress cases.

box_progress > 1.0 (역사 평균 초과) 케이스와
day_progress 복합 조건 검증.
"""

import unittest

from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_investment_signal import (
    SIGNAL_ACCUMULATE, SIGNAL_EXIT, SIGNAL_WATCH,
    classify_bear_signal, classify_bull_signal,
)


def _make_pos(phase="BEAR", box_progress=0.5, day_progress=0.5,
              price_position=0.3, is_near_target=False, cycle_number=5):
    return CyclePosition(
        phase=phase, cycle_number=cycle_number,
        completed_boxes=3, avg_boxes_historical=4.0,
        box_progress_ratio=box_progress,
        day_progress_ratio=day_progress,
        price_position=price_position,
        distance_to_target_pct=-10.0,
        is_near_target=is_near_target,
    )


class TestBearOverAverageProgress(unittest.TestCase):

    def test_accumulate_when_progress_over_100_and_day_high(self):
        """Bear: box_progress > 1.0 + day_progress >= 0.7 → ACCUMULATE."""
        pos = _make_pos(phase="BEAR", box_progress=1.2, day_progress=0.75)
        result = classify_bear_signal(pos)
        self.assertEqual(result.signal, SIGNAL_ACCUMULATE)

    def test_confidence_increases_with_excess_progress(self):
        """초과 진행률이 클수록 confidence 높아짐."""
        pos1 = _make_pos(phase="BEAR", box_progress=1.1, day_progress=0.75)
        pos2 = _make_pos(phase="BEAR", box_progress=1.5, day_progress=0.75)
        r1 = classify_bear_signal(pos1)
        r2 = classify_bear_signal(pos2)
        # 둘 다 ACCUMULATE
        self.assertEqual(r1.signal, SIGNAL_ACCUMULATE)
        self.assertEqual(r2.signal, SIGNAL_ACCUMULATE)
        self.assertGreater(r2.confidence, r1.confidence)

    def test_watch_when_progress_over_100_but_day_low(self):
        """Bear: box_progress > 1.0이지만 day_progress < 0.7 → 초과 케이스 미해당."""
        pos = _make_pos(phase="BEAR", box_progress=1.3, day_progress=0.5,
                        price_position=0.7)  # 가격도 상단 → WATCH
        result = classify_bear_signal(pos)
        # 초과 케이스 미해당 + 다른 ACCUMULATE 조건도 미충족 → WATCH
        self.assertEqual(result.signal, SIGNAL_WATCH)

    def test_confidence_clamped_to_one(self):
        """confidence는 1.0을 초과할 수 없음."""
        pos = _make_pos(phase="BEAR", box_progress=5.0, day_progress=1.0)
        result = classify_bear_signal(pos)
        self.assertLessEqual(result.confidence, 1.0)

    def test_reason_mentions_over_average(self):
        """이유 리스트에 평균 초과 내용 포함."""
        pos = _make_pos(phase="BEAR", box_progress=1.1, day_progress=0.8)
        result = classify_bear_signal(pos)
        reasons_text = " ".join(result.reason)
        self.assertIn("100%", reasons_text)


class TestBullOverAverageProgress(unittest.TestCase):

    def test_exit_when_progress_over_100_and_day_high(self):
        """Bull: box_progress > 1.0 + day_progress >= 0.8 → EXIT."""
        pos = _make_pos(phase="BULL", box_progress=1.1, day_progress=0.85)
        result = classify_bull_signal(pos)
        self.assertEqual(result.signal, SIGNAL_EXIT)

    def test_confidence_high_for_bull_over_average(self):
        """Bull 초과 케이스의 confidence는 0.85 이상."""
        pos = _make_pos(phase="BULL", box_progress=1.2, day_progress=0.9)
        result = classify_bull_signal(pos)
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_not_exit_when_day_progress_low(self):
        """Bull: box_progress > 1.0이지만 day_progress < 0.8 → 초과 케이스 미해당."""
        pos = _make_pos(phase="BULL", box_progress=1.2, day_progress=0.7,
                        price_position=0.3)  # 가격 하단 → WATCH
        result = classify_bull_signal(pos)
        self.assertNotEqual(result.signal, SIGNAL_EXIT)

    def test_confidence_clamped_to_one_bull(self):
        """Bull confidence는 1.0 초과 없음."""
        pos = _make_pos(phase="BULL", box_progress=10.0, day_progress=1.5)
        result = classify_bull_signal(pos)
        self.assertLessEqual(result.confidence, 1.0)


class TestDayProgressComposite(unittest.TestCase):

    def test_bear_accumulate_requires_both_conditions(self):
        """Bear 초과 케이스: box_progress > 1.0 AND day_progress >= 0.7 둘 다 필요."""
        # box만 초과, day 낮음
        pos_only_box = _make_pos(phase="BEAR", box_progress=1.2, day_progress=0.5,
                                  price_position=0.7)
        r = classify_bear_signal(pos_only_box)
        self.assertNotIn("100%", " ".join(r.reason))

    def test_bull_exit_requires_both_conditions(self):
        """Bull 초과 케이스: box_progress > 1.0 AND day_progress >= 0.8 둘 다 필요."""
        pos_only_day = _make_pos(phase="BULL", box_progress=0.5, day_progress=0.9,
                                  price_position=0.3, is_near_target=False)
        r = classify_bull_signal(pos_only_day)
        self.assertNotEqual(r.signal, SIGNAL_EXIT)


if __name__ == "__main__":
    unittest.main()
