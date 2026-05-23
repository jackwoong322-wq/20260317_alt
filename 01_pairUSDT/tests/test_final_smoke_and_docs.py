"""Iters 96-100: 최종 마무리 — 전체 시스템 smoke test + 문서화 검증."""

import unittest
import pandas as pd
import inspect
from lib.predictor.btc_signal_api import btc_investment_pipeline, get_signal_summary
from lib.predictor.btc_signal_history import SignalHistory, SignalHistoryEntry
from lib.predictor.btc_signal_validator import validate_signal_result
from lib.predictor.btc_cycle_position import CyclePosition, calc_btc_cycle_position
from lib.predictor.btc_signal_adapter import (
    build_cycle_position_from_df, to_position_summary,
    extract_completed_boxes, calc_avg_boxes_historical,
)
from lib.predictor.bear_stage_descriptor import format_stage_label as bear_label
from lib.predictor.bull_stage_descriptor import format_stage_label as bull_label
from lib.predictor.btc_signal_confidence_scorer import compute_final_confidence


def _df(cy=5, phase="BEAR", n_hist=3, n_curr=3):
    rows = [
        {"symbol": "BTC", "cycle_number": cy - 2, "phase": phase, "box_index": i,
         "start_x": 100+i*50, "end_x": 150+i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(n_hist)
    ] + [
        {"symbol": "BTC", "cycle_number": cy, "phase": phase, "box_index": i,
         "start_x": 500+i*60, "end_x": 560+i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(n_curr)
    ]
    return pd.DataFrame(rows)


class TestSystemSmokeTests(unittest.TestCase):
    """Iter 96-98: 전체 시스템 smoke test."""

    def test_pipeline_bear_smoke(self):
        r = btc_investment_pipeline(
            df=_df(), cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0, consecutive_count=2,
        )
        self.assertIn("signal", r)
        self.assertIn("validation", r)
        self.assertTrue(r["validation"]["is_valid"])

    def test_pipeline_bull_smoke(self):
        r = btc_investment_pipeline(
            df=_df(phase="BULL"), cycle_number=5, phase="BULL",
            current_price_pct=42.0, box_lo=30.0, box_hi=55.0,
            target_price_pct=60.0, consecutive_count=1,
        )
        self.assertIn("signal", r)
        self.assertIn(r["signal"]["phase"], ["BULL"])

    def test_pipeline_error_fallback_smoke(self):
        r = btc_investment_pipeline(
            df=None, cycle_number=99, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertEqual(r["signal"]["signal"], "WATCH")
        self.assertFalse(r["validation"]["is_valid"])

    def test_history_loop_smoke(self):
        h = SignalHistory(max_size=5)
        df = _df()
        for i in range(5):
            p = h.get_scorer_params()
            r = btc_investment_pipeline(
                df=df, cycle_number=5, phase="BEAR",
                current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
                target_price_pct=18.0, **p,
            )
            h.append(SignalHistoryEntry(
                signal=r["signal"]["signal"], phase="BEAR",
                confidence=r["signal"]["confidence"],
                stage=r["description"]["stage"],
                cycle_number=5, box_progress_ratio=0.7,
            ))
        self.assertEqual(len(h), 5)
        self.assertGreater(h.consecutive_count(), 0)

    def test_scorer_all_phases(self):
        for phase in ["BEAR", "BULL"]:
            result = compute_final_confidence(
                0.65, 3, False, 0.6, 0.6, True, phase
            )
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.0)


class TestModuleDocstrings(unittest.TestCase):
    """Iter 99-100: 공개 함수 docstring 완결성 검증."""

    def test_pipeline_has_docstring(self):
        self.assertTrue(
            btc_investment_pipeline.__doc__ is not None
            and len(btc_investment_pipeline.__doc__) > 10
        )

    def test_get_signal_summary_has_docstring(self):
        self.assertTrue(
            get_signal_summary.__doc__ is not None
            and len(get_signal_summary.__doc__) > 10
        )

    def test_compute_final_confidence_has_docstring(self):
        self.assertTrue(
            compute_final_confidence.__doc__ is not None
            and len(compute_final_confidence.__doc__) > 10
        )

    def test_bear_label_has_docstring(self):
        self.assertTrue(
            bear_label.__doc__ is not None
            and len(bear_label.__doc__) > 10
        )

    def test_bull_label_has_docstring(self):
        self.assertTrue(
            bull_label.__doc__ is not None
            and len(bull_label.__doc__) > 10
        )

    def test_to_position_summary_has_docstring(self):
        self.assertTrue(
            to_position_summary.__doc__ is not None
            and len(to_position_summary.__doc__) > 10
        )

    def test_cycle_position_to_dict_docstring(self):
        self.assertTrue(
            CyclePosition.to_dict.__doc__ is not None
            and len(CyclePosition.to_dict.__doc__) > 10
        )


if __name__ == "__main__":
    unittest.main()
