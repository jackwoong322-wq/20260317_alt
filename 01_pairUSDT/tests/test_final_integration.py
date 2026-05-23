"""Iters 91-95: 전체 파이프라인 최종 통합 & 신호 일관성 검증 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_signal_api import btc_investment_pipeline, get_signal_summary
from lib.predictor.btc_signal_payload import build_btc_signal_response
from lib.predictor.btc_signal_validator import validate_signal_result
from lib.predictor.btc_investment_signal import SignalResult


def _full_df(phase="BEAR"):
    """충분한 과거 + 현재 사이클 데이터."""
    rows = []
    for cy in [1, 2, 3, 4]:
        n = 2 + cy
        for i in range(n):
            rows.append({
                "symbol": "BTC", "cycle_number": cy, "phase": phase,
                "box_index": i,
                "start_x": cy * 200 + i * 50,
                "end_x": cy * 200 + i * 50 + 49,
                "is_completed": 1, "is_prediction": 0,
            })
    for i in range(6):
        rows.append({
            "symbol": "BTC", "cycle_number": 5, "phase": phase,
            "box_index": i,
            "start_x": 1000 + i * 55,
            "end_x": 1000 + i * 55 + 54,
            "is_completed": 1, "is_prediction": 0,
        })
    return pd.DataFrame(rows)


class TestFullPipelineConsistency(unittest.TestCase):
    """Iter 91-93: pipeline + payload 결과 일관성 검증."""

    def setUp(self):
        self.df = _full_df("BEAR")

    def test_pipeline_and_payload_signal_agree(self):
        """btc_investment_pipeline과 build_btc_signal_response의 신호가 같아야 한다."""
        r_pipe = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        r_payload = build_btc_signal_response(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertEqual(
            r_pipe["signal"]["signal"],
            r_payload["signal"]["signal"],
        )

    def test_pipeline_validation_passes(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertTrue(r["validation"]["is_valid"])
        self.assertEqual(r["validation"]["errors"], [])

    def test_pipeline_confidence_improves_with_history(self):
        """역사 데이터가 많을수록(consecutive 높을수록) confidence 향상."""
        base = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0, consecutive_count=1,
        )
        boosted = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0, consecutive_count=7,
        )
        self.assertGreaterEqual(
            boosted["signal"]["confidence"],
            base["signal"]["confidence"],
        )

    def test_cycle_position_keys_complete(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        pos = r["cycle_position"]
        for k in ["completed_boxes", "avg_boxes_historical",
                  "box_progress_ratio", "day_progress_ratio",
                  "price_position"]:
            self.assertIn(k, pos)

    def test_summary_format(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        s = get_signal_summary(r)
        self.assertIn("[BEAR cy=5]", s)
        self.assertIn("conf=", s)


class TestSignalResultValidation(unittest.TestCase):
    """Iter 94-95: SignalResult 완전한 유효성 검증 순환 테스트."""

    def _good(self):
        return SignalResult(
            signal="ACCUMULATE", phase="BEAR", confidence=0.75,
            reason=["good reason"],
            box_progress_ratio=0.7, price_position=0.25,
            distance_to_target_pct=5.0, is_near_target=True,
        )

    def test_all_valid_signals_pass(self):
        for sig in ["ACCUMULATE", "WATCH", "CAUTION", "EXIT"]:
            r = self._good()
            r.signal = sig
            report = validate_signal_result(r)
            self.assertTrue(report.is_valid, f"{sig} should be valid")

    def test_all_valid_phases_pass(self):
        for phase in ["BEAR", "BULL"]:
            r = self._good()
            r.phase = phase
            report = validate_signal_result(r)
            self.assertTrue(report.is_valid, f"{phase} should be valid")

    def test_confidence_boundary_0_is_valid(self):
        r = self._good()
        r.confidence = 0.0
        report = validate_signal_result(r)
        self.assertTrue(report.is_valid)

    def test_confidence_boundary_1_is_valid(self):
        r = self._good()
        r.confidence = 1.0
        report = validate_signal_result(r)
        self.assertTrue(report.is_valid)

    def test_just_above_1_is_invalid(self):
        r = self._good()
        r.confidence = 1.001
        report = validate_signal_result(r)
        self.assertFalse(report.is_valid)

    def test_just_below_0_is_invalid(self):
        r = self._good()
        r.confidence = -0.001
        report = validate_signal_result(r)
        self.assertFalse(report.is_valid)


if __name__ == "__main__":
    unittest.main()
