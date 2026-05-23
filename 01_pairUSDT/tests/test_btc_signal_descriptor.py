"""Tests for btc_signal_descriptor.py — Iteration 22.

Bear/Bull 통합 라우팅 및 전체 신호 설명 빌드 테스트.
"""

import unittest
import pandas as pd

from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_investment_signal import SignalResult, SIGNAL_ACCUMULATE, SIGNAL_EXIT
from lib.predictor.btc_signal_descriptor import (
    describe_btc_signal, build_full_signal_description
)


def _make_pos(phase="BEAR", box_progress=0.7, cycle_number=5):
    return CyclePosition(
        phase=phase, cycle_number=cycle_number, completed_boxes=3,
        avg_boxes_historical=4.0, box_progress_ratio=box_progress,
        day_progress_ratio=0.6, price_position=0.2,
        distance_to_target_pct=-8.0, is_near_target=True,
    )


def _make_signal(signal=SIGNAL_ACCUMULATE, phase="BEAR", confidence=0.85):
    return SignalResult(
        signal=signal, phase=phase, confidence=confidence,
        reason=["bear_late"], box_progress_ratio=0.7,
        price_position=0.2, distance_to_target_pct=-8.0, is_near_target=True,
    )


def _make_df():
    rows = [
        {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": i,
         "start_x": 100 + i*50, "end_x": 150 + i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(3)
    ] + [
        {"symbol": "BTC", "cycle_number": 4, "phase": "BEAR", "box_index": i,
         "start_x": 300 + i*60, "end_x": 360 + i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(2)
    ] + [
        {"symbol": "BTC", "cycle_number": 5, "phase": "BEAR", "box_index": 0,
         "start_x": 500, "end_x": 560, "is_completed": 1, "is_prediction": 0},
        {"symbol": "BTC", "cycle_number": 5, "phase": "BEAR", "box_index": 1,
         "start_x": 561, "end_x": 620, "is_completed": 1, "is_prediction": 0},
    ]
    return pd.DataFrame(rows)


class TestDescribeBtcSignal(unittest.TestCase):

    def test_bear_routes_to_bear_descriptor(self):
        """BEAR phase → bear_stage_descriptor 라우팅."""
        pos = _make_pos(phase="BEAR", box_progress=0.7)
        sig = _make_signal(signal=SIGNAL_ACCUMULATE, phase="BEAR")
        result = describe_btc_signal(sig, pos)
        self.assertIn("stage", result)
        self.assertIn("message_ko", result)

    def test_bull_routes_to_bull_descriptor(self):
        """BULL phase → bull_stage_descriptor 라우팅."""
        pos = _make_pos(phase="BULL", box_progress=0.85)
        sig = _make_signal(signal=SIGNAL_EXIT, phase="BULL")
        result = describe_btc_signal(sig, pos)
        self.assertIn("stage", result)

    def test_returns_dict(self):
        pos = _make_pos()
        sig = _make_signal()
        result = describe_btc_signal(sig, pos)
        self.assertIsInstance(result, dict)

    def test_error_fallback(self):
        """오류 시 안전한 fallback 반환."""
        result = describe_btc_signal(None, None)
        self.assertIn("signal", result)
        self.assertEqual(result["signal"], "WATCH")

    def test_stage_number_valid(self):
        """stage는 0~4 범위."""
        for progress in [0.1, 0.35, 0.65, 0.9]:
            pos = _make_pos(box_progress=progress)
            sig = _make_signal()
            result = describe_btc_signal(sig, pos)
            self.assertIn(result["stage"], [0, 1, 2, 3, 4])


class TestBuildFullSignalDescription(unittest.TestCase):

    def test_returns_dict_with_description(self):
        df = _make_df()
        result = build_full_signal_description(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=19.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertIn("description", result)
        self.assertIn("signal", result)

    def test_phase_preserved(self):
        df = _make_df()
        result = build_full_signal_description(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertEqual(result["phase"], "BEAR")

    def test_description_has_message_ko(self):
        df = _make_df()
        result = build_full_signal_description(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertIn("message_ko", result["description"])


if __name__ == "__main__":
    unittest.main()
