"""Iters 86-90: to_dict() + get_scorer_params + to_position_summary 통합 루프 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_signal_history import SignalHistory, SignalHistoryEntry
from lib.predictor.btc_signal_api import btc_investment_pipeline
from lib.predictor.btc_signal_adapter import build_cycle_position_from_df, to_position_summary
from lib.predictor.btc_cycle_position import CyclePosition


def _df(cy=5, phase="BEAR", n=2):
    rows = [
        {"symbol": "BTC", "cycle_number": 3, "phase": phase, "box_index": i,
         "start_x": 100+i*50, "end_x": 150+i*50, "is_completed": 1, "is_prediction": 0}
        for i in range(3)
    ] + [
        {"symbol": "BTC", "cycle_number": cy, "phase": phase, "box_index": i,
         "start_x": 500+i*60, "end_x": 560+i*60, "is_completed": 1, "is_prediction": 0}
        for i in range(n)
    ]
    return pd.DataFrame(rows)


class TestSignalHistoryPipelineLoop(unittest.TestCase):
    """Iter 86-88: SignalHistory + pipeline 연속 루프 시뮬레이션."""

    def test_three_round_loop(self):
        """3회 연속 파이프라인 실행 후 히스토리 scorer 파라미터 반영."""
        history = SignalHistory(max_size=10)
        df = _df()
        signals = []
        for _ in range(3):
            params = history.get_scorer_params()
            r = btc_investment_pipeline(
                df=df, cycle_number=5, phase="BEAR",
                current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
                target_price_pct=18.0,
                **params,
            )
            sig = r["signal"]["signal"]
            conf = r["signal"]["confidence"]
            signals.append(sig)
            history.append(SignalHistoryEntry(
                signal=sig, phase="BEAR", confidence=conf,
                stage=3, cycle_number=5, box_progress_ratio=0.7,
            ))
        self.assertEqual(len(history), 3)
        self.assertEqual(len(signals), 3)

    def test_consecutive_same_signal_increases_confidence(self):
        """연속 같은 신호일수록 confidence 증가 추세."""
        history = SignalHistory(max_size=10)
        df = _df()
        confs = []
        for _ in range(5):
            params = history.get_scorer_params()
            r = btc_investment_pipeline(
                df=df, cycle_number=5, phase="BEAR",
                current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
                target_price_pct=18.0, **params,
            )
            sig = r["signal"]["signal"]
            conf = r["signal"]["confidence"]
            confs.append(conf)
            history.append(SignalHistoryEntry(
                signal=sig, phase="BEAR", confidence=conf,
                stage=3, cycle_number=5, box_progress_ratio=0.7,
            ))
        # 5번째 confidence >= 1번째 (연속 보너스)
        self.assertGreaterEqual(confs[-1], confs[0])

    def test_history_scorer_params_types(self):
        history = SignalHistory()
        history.append(SignalHistoryEntry(
            signal="ACCUMULATE", phase="BEAR", confidence=0.8,
            stage=3, cycle_number=5, box_progress_ratio=0.7,
        ))
        p = history.get_scorer_params()
        self.assertIsInstance(p["consecutive_count"], int)
        self.assertIsInstance(p["is_signal_changed"], bool)


class TestCyclePositionToDict(unittest.TestCase):
    """Iter 89-90: to_dict() 심화 + 어댑터 통합."""

    def test_to_dict_from_df(self):
        """build_cycle_position_from_df → to_dict() 체인."""
        df = _df(cy=5, phase="BEAR", n=2)
        pos = build_cycle_position_from_df(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        d = pos.to_dict()
        self.assertEqual(d["phase"], "BEAR")
        self.assertEqual(d["cycle_number"], 5)
        self.assertIsInstance(d["box_progress_ratio"], float)

    def test_to_position_summary_from_df(self):
        df = _df(cy=5, phase="BEAR", n=2)
        pos = build_cycle_position_from_df(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        s = to_position_summary(pos)
        self.assertIn("BEAR", s)
        self.assertIn("cy=5", s)

    def test_to_dict_roundtrip_values(self):
        pos = CyclePosition(
            phase="BULL", cycle_number=4,
            completed_boxes=6, avg_boxes_historical=8.0,
            box_progress_ratio=0.75, day_progress_ratio=0.68,
            price_position=0.55, distance_to_target_pct=10.0,
            is_near_target=False,
        )
        d = pos.to_dict()
        self.assertEqual(d["phase"], "BULL")
        self.assertEqual(d["cycle_number"], 4)
        self.assertAlmostEqual(d["box_progress_ratio"], 0.75)
        self.assertFalse(d["is_near_target"])

    def test_to_dict_no_extra_keys(self):
        pos = CyclePosition(
            phase="BEAR", cycle_number=5,
            completed_boxes=7, avg_boxes_historical=10.0,
            box_progress_ratio=0.7, day_progress_ratio=0.65,
            price_position=0.25, distance_to_target_pct=5.0,
            is_near_target=True,
        )
        d = pos.to_dict()
        expected_keys = {
            "phase", "cycle_number", "completed_boxes", "avg_boxes_historical",
            "box_progress_ratio", "day_progress_ratio", "price_position",
            "distance_to_target_pct", "is_near_target",
        }
        self.assertEqual(set(d.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
