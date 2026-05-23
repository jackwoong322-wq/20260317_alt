"""Iter 35+36: CyclePosition.to_dict() 및 get_signal_summary 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_signal_api import btc_investment_pipeline, get_signal_summary


def _make_pos(**kw):
    defaults = dict(
        phase="BEAR", cycle_number=5, completed_boxes=7,
        avg_boxes_historical=10.0, box_progress_ratio=0.7,
        day_progress_ratio=0.7, price_position=0.25,
        distance_to_target_pct=5.0, is_near_target=True,
    )
    defaults.update(kw)
    return CyclePosition(**defaults)


def _make_df(cy=5):
    rows = [
        {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": i,
         "start_x": 100+i*50, "end_x": 150+i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(3)
    ] + [
        {"symbol": "BTC", "cycle_number": cy, "phase": "BEAR", "box_index": i,
         "start_x": 500+i*60, "end_x": 560+i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(2)
    ]
    return pd.DataFrame(rows)


class TestCyclePositionToDict(unittest.TestCase):

    def test_to_dict_returns_dict(self):
        pos = _make_pos()
        self.assertIsInstance(pos.to_dict(), dict)

    def test_to_dict_required_keys(self):
        pos = _make_pos()
        d = pos.to_dict()
        for k in ["phase", "cycle_number", "completed_boxes", "avg_boxes_historical",
                  "box_progress_ratio", "day_progress_ratio", "price_position",
                  "distance_to_target_pct", "is_near_target"]:
            self.assertIn(k, d)

    def test_to_dict_phase_value(self):
        pos = _make_pos(phase="BULL")
        self.assertEqual(pos.to_dict()["phase"], "BULL")

    def test_to_dict_rounded_values(self):
        pos = _make_pos(box_progress_ratio=0.71234567)
        d = pos.to_dict()
        # 소수점 4자리 반올림
        self.assertEqual(d["box_progress_ratio"], round(0.71234567, 4))

    def test_to_dict_is_near_target_bool(self):
        pos = _make_pos(is_near_target=True)
        self.assertIsInstance(pos.to_dict()["is_near_target"], bool)


class TestGetSignalSummary(unittest.TestCase):

    def setUp(self):
        self.df = _make_df()

    def _pipeline(self):
        return btc_investment_pipeline(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )

    def test_returns_string(self):
        r = self._pipeline()
        summary = get_signal_summary(r)
        self.assertIsInstance(summary, str)

    def test_contains_phase(self):
        r = self._pipeline()
        summary = get_signal_summary(r)
        self.assertIn("BEAR", summary)

    def test_contains_cycle_number(self):
        r = self._pipeline()
        summary = get_signal_summary(r)
        self.assertIn("cy=5", summary)

    def test_contains_signal(self):
        r = self._pipeline()
        summary = get_signal_summary(r)
        valid = {"ACCUMULATE", "WATCH", "CAUTION", "EXIT"}
        self.assertTrue(any(s in summary for s in valid))

    def test_error_dict_returns_error_string(self):
        summary = get_signal_summary({"phase": "BEAR", "cycle_number": 1,
                                       "signal": {}, "description": {}})
        self.assertIsInstance(summary, str)

    def test_empty_dict_no_crash(self):
        summary = get_signal_summary({})
        self.assertIsInstance(summary, str)


if __name__ == "__main__":
    unittest.main()
