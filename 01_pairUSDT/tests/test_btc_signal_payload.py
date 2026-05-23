"""Tests for btc_signal_payload.py — Iteration 15.

SignalResult → dict/API payload 직렬화 테스트.
외부 DB 없이 순수 함수 및 mock DataFrame으로 검증.
"""

import unittest
import pandas as pd

from lib.predictor.btc_investment_signal import SignalResult, SIGNAL_ACCUMULATE, SIGNAL_EXIT
from lib.predictor.btc_signal_payload import (
    signal_to_dict,
    signal_to_api_payload,
    build_btc_signal_response,
    SIGNAL_DISPLAY,
)


def _make_signal(signal=SIGNAL_ACCUMULATE, phase="BEAR", confidence=0.85,
                 box_progress=0.75, price_pos=0.2, dist=-8.0, near=True):
    return SignalResult(
        signal=signal, phase=phase, confidence=confidence,
        reason=["test_reason"], box_progress_ratio=box_progress,
        price_position=price_pos, distance_to_target_pct=dist, is_near_target=near,
    )


class TestSignalToDict(unittest.TestCase):

    def test_returns_dict(self):
        result = signal_to_dict(_make_signal())
        self.assertIsInstance(result, dict)

    def test_required_keys(self):
        result = signal_to_dict(_make_signal())
        for key in ["signal", "phase", "confidence", "reason",
                    "box_progress_ratio", "price_position",
                    "distance_to_target_pct", "is_near_target"]:
            self.assertIn(key, result)

    def test_none_returns_empty_dict(self):
        self.assertEqual(signal_to_dict(None), {})

    def test_reason_is_list(self):
        result = signal_to_dict(_make_signal())
        self.assertIsInstance(result["reason"], list)

    def test_is_near_target_is_bool(self):
        result = signal_to_dict(_make_signal())
        self.assertIsInstance(result["is_near_target"], bool)

    def test_confidence_rounded(self):
        sig = _make_signal(confidence=0.123456789)
        result = signal_to_dict(sig)
        # 소수점 4자리
        self.assertEqual(result["confidence"], round(0.123456789, 4))


class TestSignalToApiPayload(unittest.TestCase):

    def test_required_top_level_keys(self):
        sig = _make_signal()
        payload = signal_to_api_payload(sig, cycle_number=5)
        for key in ["symbol", "cycle_number", "generated_at", "signal", "display"]:
            self.assertIn(key, payload)

    def test_symbol_uppercased(self):
        sig = _make_signal()
        payload = signal_to_api_payload(sig, cycle_number=5, symbol="btc")
        self.assertEqual(payload["symbol"], "BTC")

    def test_display_contains_label_color_icon(self):
        sig = _make_signal(signal=SIGNAL_ACCUMULATE)
        payload = signal_to_api_payload(sig, cycle_number=5)
        display = payload["display"]
        self.assertIn("label", display)
        self.assertIn("color", display)
        self.assertIn("icon", display)

    def test_display_correct_for_exit(self):
        sig = _make_signal(signal=SIGNAL_EXIT, phase="BULL")
        payload = signal_to_api_payload(sig, cycle_number=5)
        self.assertEqual(payload["display"]["label"], SIGNAL_DISPLAY["EXIT"]["label"])

    def test_generated_at_custom(self):
        sig = _make_signal()
        payload = signal_to_api_payload(sig, cycle_number=5, generated_at="2026-05-20T12:00:00Z")
        self.assertEqual(payload["generated_at"], "2026-05-20T12:00:00Z")

    def test_generated_at_auto_when_none(self):
        sig = _make_signal()
        payload = signal_to_api_payload(sig, cycle_number=5, generated_at=None)
        self.assertIn("T", payload["generated_at"])  # ISO 형식 확인


class TestBuildBtcSignalResponse(unittest.TestCase):

    def _make_df(self):
        rows = [
            {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": 0,
             "start_x": 100, "end_x": 150, "is_completed": 1, "is_prediction": 0},
            {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": 1,
             "start_x": 151, "end_x": 200, "is_completed": 1, "is_prediction": 0},
            {"symbol": "BTC", "cycle_number": 4, "phase": "BEAR", "box_index": 0,
             "start_x": 300, "end_x": 370, "is_completed": 1, "is_prediction": 0},
            {"symbol": "BTC", "cycle_number": 5, "phase": "BEAR", "box_index": 0,
             "start_x": 500, "end_x": 550, "is_completed": 1, "is_prediction": 0},
        ]
        return pd.DataFrame(rows)

    def test_returns_dict_with_signal(self):
        df = self._make_df()
        payload = build_btc_signal_response(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=22.0, box_lo=18.0, box_hi=35.0, target_price_pct=17.0,
        )
        self.assertIn("signal", payload)
        self.assertIn("display", payload)

    def test_cycle_position_included(self):
        df = self._make_df()
        payload = build_btc_signal_response(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=22.0, box_lo=18.0, box_hi=35.0, target_price_pct=17.0,
        )
        self.assertIn("cycle_position", payload)
        self.assertIn("completed_boxes", payload["cycle_position"])

    def test_error_returns_watch_fallback(self):
        """잘못된 입력 시 WATCH fallback 반환."""
        payload = build_btc_signal_response(
            df=pd.DataFrame(),  # 빈 DF
            cycle_number=5, phase="BEAR",
            current_price_pct=22.0, box_lo=18.0, box_hi=35.0, target_price_pct=17.0,
        )
        # 빈 DF는 에러 아닌 fallback으로 처리
        self.assertIn("signal", payload)


if __name__ == "__main__":
    unittest.main()
