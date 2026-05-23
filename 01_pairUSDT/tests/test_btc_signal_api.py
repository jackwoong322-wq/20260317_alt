"""Tests for btc_signal_api.py — Iteration 28.

전체 파이프라인 단일 진입점 테스트.
검증 포함 완전한 payload 구조 검증.
"""

import unittest
import pandas as pd

from lib.predictor.btc_signal_api import btc_investment_pipeline


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


class TestBtcInvestmentPipeline(unittest.TestCase):

    def setUp(self):
        self.df = _make_df()

    def _call_pipeline(self, current=20.0, target=17.0):
        return btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=current, box_lo=18.0, box_hi=35.0,
            target_price_pct=target,
        )

    def test_returns_dict(self):
        result = self._call_pipeline()
        self.assertIsInstance(result, dict)

    def test_top_level_keys_present(self):
        result = self._call_pipeline()
        for key in ["symbol", "cycle_number", "phase", "signal",
                    "display", "description", "cycle_position", "validation"]:
            self.assertIn(key, result)

    def test_validation_is_valid(self):
        result = self._call_pipeline()
        self.assertTrue(result["validation"]["is_valid"])
        self.assertEqual(result["validation"]["errors"], [])

    def test_signal_has_required_fields(self):
        result = self._call_pipeline()
        sig = result["signal"]
        for k in ["signal", "phase", "confidence", "reason"]:
            self.assertIn(k, sig)

    def test_description_has_messages(self):
        result = self._call_pipeline()
        desc = result["description"]
        self.assertIn("message_ko", desc)
        self.assertIn("stage", desc)

    def test_cycle_position_has_boxes(self):
        result = self._call_pipeline()
        pos = result["cycle_position"]
        self.assertEqual(pos["completed_boxes"], 2)

    def test_accumulate_signal_near_bottom(self):
        """저점 근접 → ACCUMULATE 기대."""
        result = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,  # 2.7% 거리 → near
        )
        self.assertIn(result["signal"]["signal"], ["ACCUMULATE", "WATCH"])

    def test_empty_df_returns_valid_structure(self):
        """빈 DF도 에러 없이 구조 반환."""
        result = btc_investment_pipeline(
            df=pd.DataFrame(), cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertIn("signal", result)


if __name__ == "__main__":
    unittest.main()
