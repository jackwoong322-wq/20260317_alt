"""Iters 61-65: btc_signal_descriptor 추가 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_signal_descriptor import build_full_signal_description


def _make_df(cy=5, phase="BEAR", n_hist=3, n_curr=2):
    rows = [
        {"symbol": "BTC", "cycle_number": 3, "phase": phase, "box_index": i,
         "start_x": 100+i*50, "end_x": 150+i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(n_hist)
    ] + [
        {"symbol": "BTC", "cycle_number": cy, "phase": phase, "box_index": i,
         "start_x": 500+i*60, "end_x": 560+i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(n_curr)
    ]
    return pd.DataFrame(rows)


class TestBuildFullSignalDescription(unittest.TestCase):

    def _call(self, phase="BEAR", cy=5, price=18.5, lo=18.0, hi=35.0, target=18.0):
        return build_full_signal_description(
            df=_make_df(cy=cy, phase=phase), cycle_number=cy, phase=phase,
            current_price_pct=price, box_lo=lo, box_hi=hi,
            target_price_pct=target,
        )

    def test_returns_dict(self):
        self.assertIsInstance(self._call(), dict)

    def test_has_signal_key(self):
        r = self._call()
        self.assertIn("signal", r)

    def test_has_description_key(self):
        r = self._call()
        self.assertIn("description", r)

    def test_has_cycle_position_key(self):
        r = self._call()
        self.assertIn("cycle_position", r)

    def test_display_has_icon(self):
        r = self._call()
        self.assertIn("display", r)
        self.assertIn("icon", r["display"])


    def test_bear_message_ko_nonempty(self):
        r = self._call(phase="BEAR")
        self.assertTrue(len(r["description"]["message_ko"]) > 0)

    def test_bull_phase(self):
        df = _make_df(cy=5, phase="BULL", n_hist=4, n_curr=3)
        r = build_full_signal_description(
            df=df, cycle_number=5, phase="BULL",
            current_price_pct=42.0, box_lo=30.0, box_hi=55.0,
            target_price_pct=60.0,
        )
        self.assertIn("signal", r)
        self.assertEqual(r["phase"], "BULL")

    def test_stage_is_int(self):
        r = self._call()
        self.assertIsInstance(r["description"]["stage"], int)

    def test_confidence_is_float(self):
        r = self._call()
        self.assertIsInstance(r["signal"]["confidence"], float)

    def test_symbol_is_btc(self):
        r = self._call()
        self.assertEqual(r["symbol"], "BTC")


if __name__ == "__main__":
    unittest.main()
