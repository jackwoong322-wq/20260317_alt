"""Iters 81-85: btc_signal_payload build_btc_signal_response 심화 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_signal_payload import (
    signal_to_dict, signal_to_api_payload, build_btc_signal_response, SIGNAL_DISPLAY,
)
from lib.predictor.btc_investment_signal import SignalResult


def _res(signal="ACCUMULATE", phase="BEAR", conf=0.8):
    return SignalResult(
        signal=signal, phase=phase, confidence=conf,
        reason=["test"],
        box_progress_ratio=0.72, price_position=0.22,
        distance_to_target_pct=4.5, is_near_target=True,
    )


def _df(cy=5, phase="BEAR"):
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


class TestSignalDisplayConstants(unittest.TestCase):
    """Iter 81: SIGNAL_DISPLAY 상수 검증."""

    def test_all_four_signals_in_display(self):
        for s in ["ACCUMULATE", "WATCH", "CAUTION", "EXIT"]:
            self.assertIn(s, SIGNAL_DISPLAY)

    def test_each_has_label_color_icon(self):
        for s, d in SIGNAL_DISPLAY.items():
            self.assertIn("label", d, f"{s} missing label")
            self.assertIn("color", d, f"{s} missing color")
            self.assertIn("icon", d, f"{s} missing icon")

    def test_color_starts_with_hash(self):
        for s, d in SIGNAL_DISPLAY.items():
            self.assertTrue(d["color"].startswith("#"), f"{s} color invalid")


class TestSignalToDict(unittest.TestCase):
    """Iter 82: signal_to_dict 추가 케이스."""

    def test_none_returns_empty_dict(self):
        self.assertEqual(signal_to_dict(None), {})

    def test_all_fields_present(self):
        d = signal_to_dict(_res())
        for k in ["signal", "phase", "confidence", "reason",
                  "box_progress_ratio", "price_position",
                  "distance_to_target_pct", "is_near_target"]:
            self.assertIn(k, d)

    def test_is_near_target_is_bool(self):
        d = signal_to_dict(_res())
        self.assertIsInstance(d["is_near_target"], bool)

    def test_confidence_4_decimal(self):
        r = _res(conf=0.12345678)
        d = signal_to_dict(r)
        self.assertEqual(d["confidence"], round(0.12345678, 4))


class TestBuildBtcSignalResponse(unittest.TestCase):
    """Iter 83-85: build_btc_signal_response 통합 테스트."""

    def test_returns_dict(self):
        r = build_btc_signal_response(
            df=_df(), cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertIsInstance(r, dict)

    def test_has_cycle_position(self):
        r = build_btc_signal_response(
            df=_df(), cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertIn("cycle_position", r)

    def test_has_display(self):
        r = build_btc_signal_response(
            df=_df(), cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertIn("display", r)

    def test_generated_at_format(self):
        r = build_btc_signal_response(
            df=_df(), cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
            generated_at="2026-05-21T00:00:00Z",
        )
        self.assertEqual(r.get("generated_at"), "2026-05-21T00:00:00Z")

    def test_error_fallback_has_watch(self):
        r = build_btc_signal_response(
            df=None, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertEqual(r["signal"]["signal"], "WATCH")

    def test_symbol_is_btc(self):
        r = build_btc_signal_response(
            df=_df(), cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertEqual(r.get("symbol"), "BTC")


if __name__ == "__main__":
    unittest.main()
