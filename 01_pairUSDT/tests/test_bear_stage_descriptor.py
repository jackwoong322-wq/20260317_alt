"""Tests for bear_stage_descriptor.py — Iteration 20.

Bear 사이클 4단계 분류 및 투자 메시지 생성 테스트.
"""

import unittest

from lib.predictor.bear_stage_descriptor import (
    classify_bear_stage,
    get_bear_stage_info,
    describe_bear_signal,
    BearStageInfo,
    STAGE_INFO,
)
from lib.predictor.btc_investment_signal import SignalResult, SIGNAL_ACCUMULATE, SIGNAL_WATCH


def _make_signal(signal=SIGNAL_ACCUMULATE, confidence=0.85, box_progress=0.7):
    return SignalResult(
        signal=signal, phase="BEAR", confidence=confidence,
        reason=["test"], box_progress_ratio=box_progress,
        price_position=0.2, distance_to_target_pct=-8.0, is_near_target=True,
    )


class TestClassifyBearStage(unittest.TestCase):

    def test_stage_1_early(self):
        """0% → Stage 1."""
        self.assertEqual(classify_bear_stage(0.0), 1)

    def test_stage_1_boundary(self):
        """29% → Stage 1."""
        self.assertEqual(classify_bear_stage(0.29), 1)

    def test_stage_2_start(self):
        """30% → Stage 2."""
        self.assertEqual(classify_bear_stage(0.30), 2)

    def test_stage_2_mid(self):
        """50% → Stage 2."""
        self.assertEqual(classify_bear_stage(0.50), 2)

    def test_stage_3_start(self):
        """60% → Stage 3."""
        self.assertEqual(classify_bear_stage(0.60), 3)

    def test_stage_3_mid(self):
        """75% → Stage 3."""
        self.assertEqual(classify_bear_stage(0.75), 3)

    def test_stage_4_start(self):
        """85% → Stage 4."""
        self.assertEqual(classify_bear_stage(0.85), 4)

    def test_stage_4_over_average(self):
        """100% 초과 → Stage 4."""
        self.assertEqual(classify_bear_stage(1.2), 4)

    def test_negative_progress_returns_stage_1(self):
        """음수 입력 → Stage 1 (클리핑)."""
        self.assertEqual(classify_bear_stage(-0.5), 1)


class TestGetBearStageInfo(unittest.TestCase):

    def test_returns_bear_stage_info(self):
        info = get_bear_stage_info(0.7)
        self.assertIsInstance(info, BearStageInfo)

    def test_stage_3_has_green_color(self):
        """Stage 3 (Bear 후반) → 녹색 계열."""
        info = get_bear_stage_info(0.72)
        self.assertEqual(info.stage, 3)
        self.assertIn("#", info.color)

    def test_box_progress_preserved(self):
        """box_progress_ratio 값이 그대로 전달됨."""
        info = get_bear_stage_info(0.65)
        self.assertAlmostEqual(info.box_progress_ratio, 0.65)

    def test_all_stages_have_messages(self):
        """모든 Stage에 한글/영문 메시지 존재."""
        for progress in [0.1, 0.4, 0.7, 0.9]:
            info = get_bear_stage_info(progress)
            self.assertTrue(len(info.message_ko) > 0)
            self.assertTrue(len(info.message_en) > 0)


class TestDescribeBearSignal(unittest.TestCase):

    def test_returns_dict(self):
        sig = _make_signal()
        result = describe_bear_signal(sig, 0.7)
        self.assertIsInstance(result, dict)

    def test_required_keys(self):
        """필수 키 존재."""
        sig = _make_signal()
        result = describe_bear_signal(sig, 0.7)
        for key in ["stage", "stage_name", "signal", "action",
                    "message_ko", "message_en", "confidence", "color", "emoji", "reason"]:
            self.assertIn(key, result)

    def test_signal_preserved(self):
        sig = _make_signal(signal=SIGNAL_ACCUMULATE)
        result = describe_bear_signal(sig, 0.7)
        self.assertEqual(result["signal"], SIGNAL_ACCUMULATE)

    def test_confidence_preserved(self):
        sig = _make_signal(confidence=0.876)
        result = describe_bear_signal(sig, 0.7)
        self.assertAlmostEqual(result["confidence"], 0.876, places=3)

    def test_none_signal_fallback(self):
        """signal_result=None → WATCH fallback."""
        result = describe_bear_signal(None, 0.5)
        self.assertEqual(result["signal"], "WATCH")

    def test_stage_3_action_includes_매수(self):
        """Stage 3 action에 '매수' 포함."""
        sig = _make_signal()
        result = describe_bear_signal(sig, 0.72)  # Stage 3
        self.assertIn("매수", result["action"])


if __name__ == "__main__":
    unittest.main()
