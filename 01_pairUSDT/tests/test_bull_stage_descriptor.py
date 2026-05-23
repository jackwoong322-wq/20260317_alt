"""Tests for bull_stage_descriptor.py — Iteration 21."""

import unittest

from lib.predictor.bull_stage_descriptor import (
    classify_bull_stage, get_bull_stage_info, describe_bull_signal, BullStageInfo,
)
from lib.predictor.btc_investment_signal import SignalResult, SIGNAL_EXIT, SIGNAL_CAUTION


def _make_signal(signal=SIGNAL_EXIT, confidence=0.9, phase="BULL"):
    return SignalResult(
        signal=signal, phase=phase, confidence=confidence,
        reason=["test"], box_progress_ratio=0.85,
        price_position=0.8, distance_to_target_pct=5.0, is_near_target=True,
    )


class TestClassifyBullStage(unittest.TestCase):
    def test_stage_1(self): self.assertEqual(classify_bull_stage(0.0), 1)
    def test_stage_1_bound(self): self.assertEqual(classify_bull_stage(0.24), 1)
    def test_stage_2(self): self.assertEqual(classify_bull_stage(0.25), 2)
    def test_stage_2_mid(self): self.assertEqual(classify_bull_stage(0.45), 2)
    def test_stage_3(self): self.assertEqual(classify_bull_stage(0.55), 3)
    def test_stage_3_mid(self): self.assertEqual(classify_bull_stage(0.70), 3)
    def test_stage_4(self): self.assertEqual(classify_bull_stage(0.80), 4)
    def test_stage_4_over(self): self.assertEqual(classify_bull_stage(1.5), 4)
    def test_negative_returns_1(self): self.assertEqual(classify_bull_stage(-0.1), 1)


class TestGetBullStageInfo(unittest.TestCase):
    def test_returns_bull_stage_info(self):
        info = get_bull_stage_info(0.6)
        self.assertIsInstance(info, BullStageInfo)

    def test_stage_4_red_color(self):
        info = get_bull_stage_info(0.9)
        self.assertEqual(info.stage, 4)
        self.assertIn("#", info.color)

    def test_all_stages_have_messages(self):
        for p in [0.1, 0.35, 0.65, 0.9]:
            info = get_bull_stage_info(p)
            self.assertTrue(len(info.message_ko) > 0)


class TestDescribeBullSignal(unittest.TestCase):
    def test_required_keys(self):
        result = describe_bull_signal(_make_signal(), 0.85)
        for key in ["stage", "stage_name", "signal", "action",
                    "message_ko", "message_en", "confidence", "color", "emoji"]:
            self.assertIn(key, result)

    def test_signal_preserved(self):
        result = describe_bull_signal(_make_signal(signal=SIGNAL_EXIT), 0.85)
        self.assertEqual(result["signal"], SIGNAL_EXIT)

    def test_none_fallback(self):
        result = describe_bull_signal(None, 0.5)
        self.assertEqual(result["signal"], "WATCH")

    def test_stage_4_action_includes_매도(self):
        result = describe_bull_signal(_make_signal(), 0.88)
        self.assertIn("매도", result["action"])


if __name__ == "__main__":
    unittest.main()
