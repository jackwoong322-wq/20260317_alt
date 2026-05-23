"""Tests for btc_investment_signal.py — Iteration 10.

투자 타이밍 신호 생성기의 핵심 로직을 검증한다.
Bear 사이클: ACCUMULATE vs WATCH
Bull 사이클: EXIT vs CAUTION vs WATCH
경계 조건 및 신뢰도(confidence) 범위 검증 포함.
"""

import unittest

from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_investment_signal import (
    SIGNAL_ACCUMULATE,
    SIGNAL_CAUTION,
    SIGNAL_EXIT,
    SIGNAL_WATCH,
    classify_bear_signal,
    classify_bull_signal,
    generate_btc_signal,
    SignalResult,
)


def _make_pos(
    phase="BEAR",
    cycle_number=5,
    completed_boxes=2,
    avg_boxes=4.0,
    box_progress=0.5,
    day_progress=0.5,
    price_position=0.3,
    distance=-10.0,
    is_near_target=False,
) -> CyclePosition:
    return CyclePosition(
        phase=phase,
        cycle_number=cycle_number,
        completed_boxes=completed_boxes,
        avg_boxes_historical=avg_boxes,
        box_progress_ratio=box_progress,
        day_progress_ratio=day_progress,
        price_position=price_position,
        distance_to_target_pct=distance,
        is_near_target=is_near_target,
    )


class TestClassifyBearSignal(unittest.TestCase):

    def test_accumulate_when_all_conditions_met(self):
        """Bear 후반 + 하단 근처 + near_target → ACCUMULATE."""
        pos = _make_pos(phase="BEAR", box_progress=0.75, price_position=0.2, is_near_target=True)
        result = classify_bear_signal(pos)
        self.assertEqual(result.signal, SIGNAL_ACCUMULATE)

    def test_accumulate_without_near_target_lower_confidence(self):
        """Bear 후반 + 하단이지만 near_target=False → ACCUMULATE (낮은 confidence)."""
        pos = _make_pos(phase="BEAR", box_progress=0.7, price_position=0.25, is_near_target=False)
        result = classify_bear_signal(pos)
        self.assertEqual(result.signal, SIGNAL_ACCUMULATE)
        self.assertLess(result.confidence, 0.7)

    def test_watch_when_progress_low(self):
        """Bear 초반(진행률 20%) → WATCH."""
        pos = _make_pos(phase="BEAR", box_progress=0.2, price_position=0.5, is_near_target=False)
        result = classify_bear_signal(pos)
        self.assertEqual(result.signal, SIGNAL_WATCH)

    def test_watch_when_price_too_high(self):
        """Bear 후반이지만 가격이 상단 → WATCH (하단 조건 미달)."""
        pos = _make_pos(phase="BEAR", box_progress=0.8, price_position=0.7, is_near_target=True)
        result = classify_bear_signal(pos)
        self.assertEqual(result.signal, SIGNAL_WATCH)

    def test_confidence_in_valid_range(self):
        """confidence는 항상 0.0~1.0."""
        for progress in [0.0, 0.3, 0.6, 0.8, 1.0, 1.2]:
            for price_pos in [0.1, 0.3, 0.6, 0.9]:
                pos = _make_pos(phase="BEAR", box_progress=progress, price_position=price_pos)
                result = classify_bear_signal(pos)
                self.assertGreaterEqual(result.confidence, 0.0, f"progress={progress}, price={price_pos}")
                self.assertLessEqual(result.confidence, 1.0, f"progress={progress}, price={price_pos}")

    def test_reason_is_list(self):
        """reason은 항상 리스트."""
        pos = _make_pos(phase="BEAR", box_progress=0.7, price_position=0.2, is_near_target=True)
        result = classify_bear_signal(pos)
        self.assertIsInstance(result.reason, list)
        self.assertGreater(len(result.reason), 0)

    def test_phase_preserved_in_result(self):
        """결과의 phase는 BEAR."""
        pos = _make_pos(phase="BEAR")
        result = classify_bear_signal(pos)
        self.assertEqual(result.phase, "BEAR")


class TestClassifyBullSignal(unittest.TestCase):

    def test_exit_when_all_conditions_met(self):
        """Bull 후반 + 상단 + near_target → EXIT."""
        pos = _make_pos(phase="BULL", box_progress=0.9, price_position=0.85, is_near_target=True)
        result = classify_bull_signal(pos)
        self.assertEqual(result.signal, SIGNAL_EXIT)

    def test_caution_when_mid_high(self):
        """Bull 60%+ 진행 + 중상단 → CAUTION."""
        pos = _make_pos(phase="BULL", box_progress=0.65, price_position=0.6, is_near_target=False)
        result = classify_bull_signal(pos)
        self.assertEqual(result.signal, SIGNAL_CAUTION)

    def test_watch_when_early_bull(self):
        """Bull 초반(진행률 30%) → WATCH."""
        pos = _make_pos(phase="BULL", box_progress=0.3, price_position=0.4, is_near_target=False)
        result = classify_bull_signal(pos)
        self.assertEqual(result.signal, SIGNAL_WATCH)

    def test_exit_requires_near_target(self):
        """near_target=False이면 EXIT 조건 불충족 → CAUTION 또는 WATCH."""
        pos = _make_pos(phase="BULL", box_progress=0.85, price_position=0.8, is_near_target=False)
        result = classify_bull_signal(pos)
        self.assertNotEqual(result.signal, SIGNAL_EXIT)

    def test_confidence_in_valid_range(self):
        """confidence는 0.0~1.0."""
        for progress in [0.0, 0.3, 0.6, 0.8, 1.0]:
            for price_pos in [0.1, 0.5, 0.8, 1.0]:
                pos = _make_pos(phase="BULL", box_progress=progress, price_position=price_pos)
                result = classify_bull_signal(pos)
                self.assertGreaterEqual(result.confidence, 0.0)
                self.assertLessEqual(result.confidence, 1.0)

    def test_phase_preserved_in_result(self):
        pos = _make_pos(phase="BULL")
        result = classify_bull_signal(pos)
        self.assertEqual(result.phase, "BULL")


class TestGenerateBtcSignal(unittest.TestCase):

    def test_returns_signal_result_instance(self):
        pos = _make_pos(phase="BEAR")
        result = generate_btc_signal(pos)
        self.assertIsInstance(result, SignalResult)

    def test_bear_phase_routes_to_bear(self):
        """phase=BEAR이면 Bear 신호 생성 루트."""
        pos = _make_pos(phase="BEAR", box_progress=0.8, price_position=0.2, is_near_target=True)
        result = generate_btc_signal(pos)
        self.assertEqual(result.phase, "BEAR")
        self.assertEqual(result.signal, SIGNAL_ACCUMULATE)

    def test_bull_phase_routes_to_bull(self):
        """phase=BULL이면 Bull 신호 생성 루트."""
        pos = _make_pos(phase="BULL", box_progress=0.9, price_position=0.85, is_near_target=True)
        result = generate_btc_signal(pos)
        self.assertEqual(result.phase, "BULL")
        self.assertEqual(result.signal, SIGNAL_EXIT)

    def test_signal_field_is_valid_string(self):
        """signal 값은 정의된 4가지 중 하나."""
        valid_signals = {SIGNAL_ACCUMULATE, SIGNAL_WATCH, SIGNAL_CAUTION, SIGNAL_EXIT}
        for phase in ["BEAR", "BULL"]:
            for progress in [0.2, 0.5, 0.75, 1.0]:
                pos = _make_pos(phase=phase, box_progress=progress)
                result = generate_btc_signal(pos)
                self.assertIn(result.signal, valid_signals)

    def test_box_progress_preserved_in_result(self):
        """결과의 box_progress_ratio는 입력값과 일치."""
        pos = _make_pos(phase="BEAR", box_progress=0.65)
        result = generate_btc_signal(pos)
        self.assertAlmostEqual(result.box_progress_ratio, 0.65)


if __name__ == "__main__":
    unittest.main()
