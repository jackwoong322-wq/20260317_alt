"""btc_investment_pipeline consecutive_count/is_signal_changed 통합 테스트.

Iteration 32 — pipeline에 scorer 파라미터 전달 검증.
"""

import unittest
import pandas as pd

from lib.predictor.btc_signal_api import btc_investment_pipeline


def _make_df(cycle=5):
    rows = [
        {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": i,
         "start_x": 100 + i*50, "end_x": 150 + i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(3)
    ] + [
        {"symbol": "BTC", "cycle_number": 4, "phase": "BEAR", "box_index": i,
         "start_x": 300 + i*60, "end_x": 360 + i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(2)
    ] + [
        {"symbol": "BTC", "cycle_number": cycle, "phase": "BEAR", "box_index": 0,
         "start_x": 500, "end_x": 560, "is_completed": 1, "is_prediction": 0},
        {"symbol": "BTC", "cycle_number": cycle, "phase": "BEAR", "box_index": 1,
         "start_x": 561, "end_x": 620, "is_completed": 1, "is_prediction": 0},
    ]
    return pd.DataFrame(rows)


class TestPipelineWithScorer(unittest.TestCase):
    """btc_investment_pipeline이 scorer 파라미터를 올바르게 전달하는지 검증."""

    def setUp(self):
        self.df = _make_df()

    def _call(self, consecutive_count=1, is_signal_changed=False):
        return btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
            consecutive_count=consecutive_count,
            is_signal_changed=is_signal_changed,
        )

    def test_default_call_backward_compatible(self):
        """기존 호출 방식이 여전히 작동해야 한다."""
        result = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertIn("signal", result)
        self.assertIn("confidence", result["signal"])

    def test_consecutive_count_reflected_in_confidence(self):
        """consecutive_count=5가 반영된 confidence가 돌아와야 한다."""
        r_base = self._call(consecutive_count=1)
        r_consec = self._call(consecutive_count=5)
        # confidence 타입 확인
        self.assertIsInstance(r_base["signal"]["confidence"], float)
        self.assertIsInstance(r_consec["signal"]["confidence"], float)
        # 연속 보너스로 더 높아야 함
        self.assertGreaterEqual(r_consec["signal"]["confidence"], r_base["signal"]["confidence"])

    def test_signal_changed_reduces_confidence(self):
        """is_signal_changed=True가 confidence를 낮춰야 한다."""
        r_stable = self._call(is_signal_changed=False)
        r_changed = self._call(is_signal_changed=True)
        self.assertLessEqual(r_changed["signal"]["confidence"], r_stable["signal"]["confidence"])

    def test_confidence_in_valid_range(self):
        """보정 후 confidence는 0~1 범위여야 한다."""
        r = self._call(consecutive_count=10, is_signal_changed=False)
        c = r["signal"]["confidence"]
        self.assertGreaterEqual(c, 0.0)
        self.assertLessEqual(c, 1.0)

    def test_validation_still_passes_with_scorer_params(self):
        """scorer 파라미터 사용 시 검증도 통과해야 한다."""
        r = self._call(consecutive_count=3)
        self.assertTrue(r["validation"]["is_valid"])

    def test_signal_changed_with_consecutive_count(self):
        """신호 변경 + 연속 카운트 조합도 오류 없이 작동해야 한다."""
        r = self._call(consecutive_count=3, is_signal_changed=True)
        self.assertIn(r["signal"]["signal"], ["ACCUMULATE", "WATCH", "CAUTION", "EXIT"])

    def test_bull_pipeline_with_scorer(self):
        """Bull 파이프라인도 scorer 파라미터가 작동해야 한다."""
        bull_df_rows = [
            {"symbol": "BTC", "cycle_number": 3, "phase": "BULL", "box_index": i,
             "start_x": 100 + i*50, "end_x": 150 + i*50, "is_completed": 1, "is_prediction": 0}
            for i in range(4)
        ] + [
            {"symbol": "BTC", "cycle_number": 5, "phase": "BULL", "box_index": 0,
             "start_x": 600, "end_x": 680, "is_completed": 1, "is_prediction": 0},
        ]
        df_bull = pd.DataFrame(bull_df_rows)
        r = btc_investment_pipeline(
            df=df_bull, cycle_number=5, phase="BULL",
            current_price_pct=42.0, box_lo=30.0, box_hi=50.0,
            target_price_pct=55.0,
            consecutive_count=3,
        )
        self.assertIn("signal", r)
        self.assertIn(r["signal"]["signal"], ["ACCUMULATE", "WATCH", "CAUTION", "EXIT"])

    def test_error_fallback_has_watch(self):
        """오류 시 WATCH fallback이 반환되어야 한다."""
        r = btc_investment_pipeline(
            df=None, cycle_number=99, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertEqual(r["signal"]["signal"], "WATCH")
        self.assertFalse(r["validation"]["is_valid"])


if __name__ == "__main__":
    unittest.main()
