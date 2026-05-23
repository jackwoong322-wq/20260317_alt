"""Iters 44-46: payload_to_supabase_row + 시나리오 통합 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_signal_payload import signal_to_dict, signal_to_api_payload
from lib.predictor.btc_investment_signal import SignalResult
from lib.predictor.btc_signal_api import btc_investment_pipeline, get_signal_summary


def _make_result(signal="ACCUMULATE", phase="BEAR", confidence=0.82):
    return SignalResult(
        signal=signal, phase=phase, confidence=confidence,
        reason=["test"],
        box_progress_ratio=0.72, price_position=0.22,
        distance_to_target_pct=4.5, is_near_target=True,
    )


def _make_df(cy=5, phase="BEAR"):
    rows = [
        {"symbol": "BTC", "cycle_number": 3, "phase": phase, "box_index": i,
         "start_x": 100+i*50, "end_x": 150+i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(3)
    ] + [
        {"symbol": "BTC", "cycle_number": cy, "phase": phase, "box_index": i,
         "start_x": 500+i*60, "end_x": 560+i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(2)
    ]
    return pd.DataFrame(rows)


class TestSignalToDictPayload(unittest.TestCase):
    """Iter 44: signal_to_dict/signal_to_api_payload 추가 검증."""

    def test_signal_to_dict_confidence_rounded(self):
        r = _make_result(confidence=0.823456)
        d = signal_to_dict(r)
        self.assertEqual(d["confidence"], round(0.823456, 4))

    def test_signal_to_dict_reason_is_list(self):
        r = _make_result()
        d = signal_to_dict(r)
        self.assertIsInstance(d["reason"], list)

    def test_signal_to_api_payload_has_generated_at(self):
        r = _make_result()
        payload = signal_to_api_payload(r, cycle_number=5, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(payload["generated_at"], "2026-01-01T00:00:00Z")

    def test_signal_to_api_auto_timestamp(self):
        r = _make_result()
        payload = signal_to_api_payload(r, cycle_number=5)
        self.assertIn("generated_at", payload)
        self.assertIn("2026", payload["generated_at"])

    def test_display_color_present(self):
        r = _make_result(signal="WATCH")
        payload = signal_to_api_payload(r, cycle_number=5)
        self.assertIn("color", payload["display"])

    def test_symbol_uppercase(self):
        r = _make_result()
        payload = signal_to_api_payload(r, cycle_number=5, symbol="btc")
        self.assertEqual(payload["symbol"], "BTC")


class TestScenarioBearAccumulate(unittest.TestCase):
    """Iter 45: Bear 후반 ACCUMULATE 전체 시나리오."""

    def setUp(self):
        self.df = _make_df(cy=5, phase="BEAR")

    def test_full_pipeline_structure(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0, consecutive_count=3,
        )
        self.assertIn("signal", r)
        self.assertIn("description", r)
        self.assertIn("validation", r)

    def test_confidence_increases_with_consecutive(self):
        base = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0, consecutive_count=1,
        )
        high = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0, consecutive_count=5,
        )
        self.assertGreaterEqual(
            high["signal"]["confidence"],
            base["signal"]["confidence"]
        )

    def test_summary_string_contains_signal(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        s = get_signal_summary(r)
        self.assertIsInstance(s, str)
        self.assertIn("cy=5", s)


class TestScenarioBullExit(unittest.TestCase):
    """Iter 46: Bull 후반 EXIT 전체 시나리오."""

    def setUp(self):
        rows = [
            {"symbol": "BTC", "cycle_number": 3, "phase": "BULL", "box_index": i,
             "start_x": 100+i*50, "end_x": 150+i*50, "is_completed": 1, "is_prediction": 0}
            for i in range(5)
        ] + [
            {"symbol": "BTC", "cycle_number": 5, "phase": "BULL", "box_index": i,
             "start_x": 600+i*60, "end_x": 660+i*60, "is_completed": 1, "is_prediction": 0}
            for i in range(4)
        ]
        self.df = pd.DataFrame(rows)

    def test_bull_pipeline_structure(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BULL",
            current_price_pct=45.0, box_lo=30.0, box_hi=55.0,
            target_price_pct=60.0,
        )
        self.assertIn("signal", r)
        self.assertIn(r["signal"]["phase"], ["BULL"])

    def test_bull_high_progress_caution_or_exit(self):
        r = btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BULL",
            current_price_pct=52.0, box_lo=30.0, box_hi=55.0,
            target_price_pct=60.0,
        )
        self.assertIn(r["signal"]["signal"], ["CAUTION", "EXIT", "WATCH"])


if __name__ == "__main__":
    unittest.main()
