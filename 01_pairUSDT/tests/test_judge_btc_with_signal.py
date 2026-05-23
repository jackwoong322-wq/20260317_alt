"""Tests for judge_btc_with_signal — Iteration 12.

judge_bull_bear의 기존 9-tuple 반환값을 유지하면서
BTC 한정으로 10번째 요소(SignalResult)를 추가하는
judge_btc_with_signal 함수 테스트.
"""

import unittest
import pandas as pd

from lib.predictor.predict_judge import judge_btc_with_signal
from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_investment_signal import (
    SIGNAL_ACCUMULATE, SIGNAL_WATCH, SIGNAL_CAUTION, SIGNAL_EXIT, SignalResult
)


def _make_last(symbol="BTC", lo=20.0, hi=50.0, end_x=100,
               gain_pct=-5.0, lo_change_pct=-2.0, coin_rank=1, cycle_name="Cy5"):
    return pd.Series({
        "symbol": symbol, "lo": lo, "hi": hi, "end_x": end_x,
        "gain_pct": gain_pct, "lo_change_pct": lo_change_pct,
        "coin_rank": coin_rank, "cycle_name": cycle_name,
    })


def _make_grp(last):
    return pd.DataFrame([last.to_dict()])


def _make_pos(phase="BEAR", box_progress=0.7, price_position=0.2, is_near_target=True):
    return CyclePosition(
        phase=phase, cycle_number=5, completed_boxes=3, avg_boxes_historical=4.0,
        box_progress_ratio=box_progress, day_progress_ratio=0.6,
        price_position=price_position, distance_to_target_pct=-8.0,
        is_near_target=is_near_target,
    )


class TestJudgeBtcWithSignal(unittest.TestCase):

    def test_returns_10_tuple(self):
        """반환값은 10-tuple (기존 9 + signal_result)."""
        last = _make_last()
        grp = _make_grp(last)
        result = judge_btc_with_signal(
            last, grp, max_cyc=5, prob_bull=0.3, prob_bear=0.7,
            bottom_day=200, btc_anchor=None, bottom_lo=18.0,
            cycle_position=_make_pos(),
        )
        self.assertEqual(len(result), 10)

    def test_first_nine_match_base_judge(self):
        """처음 9개 값은 judge_bull_bear와 동일해야 함."""
        from lib.predictor.predict_judge import judge_bull_bear
        last = _make_last()
        grp = _make_grp(last)
        base = judge_bull_bear(
            last, grp, max_cyc=5, prob_bull=0.4, prob_bear=0.6,
            bottom_day=200, btc_anchor=None, bottom_lo=18.0,
        )
        full = judge_btc_with_signal(
            last, grp, max_cyc=5, prob_bull=0.4, prob_bear=0.6,
            bottom_day=200, btc_anchor=None, bottom_lo=18.0,
            cycle_position=_make_pos(),
        )
        self.assertEqual(full[:9], base)

    def test_signal_result_is_signal_result_instance(self):
        """10번째 요소는 SignalResult 인스턴스."""
        last = _make_last()
        grp = _make_grp(last)
        result = judge_btc_with_signal(
            last, grp, 5, 0.3, 0.7, 200, None, 18.0,
            cycle_position=_make_pos(phase="BEAR", box_progress=0.8, price_position=0.2, is_near_target=True),
        )
        self.assertIsInstance(result[9], SignalResult)

    def test_signal_accumulate_for_bear_late_stage(self):
        """Bear 후반 + 하단 → ACCUMULATE."""
        last = _make_last()
        grp = _make_grp(last)
        pos = _make_pos(phase="BEAR", box_progress=0.8, price_position=0.2, is_near_target=True)
        result = judge_btc_with_signal(
            last, grp, 5, 0.3, 0.7, 200, None, 18.0, cycle_position=pos
        )
        self.assertEqual(result[9].signal, SIGNAL_ACCUMULATE)

    def test_signal_none_when_no_position(self):
        """cycle_position=None이면 signal_result=None."""
        last = _make_last()
        grp = _make_grp(last)
        result = judge_btc_with_signal(
            last, grp, 5, 0.3, 0.7, 200, None, 18.0, cycle_position=None
        )
        self.assertIsNone(result[9])

    def test_signal_none_for_non_btc(self):
        """BTC가 아닌 코인은 signal_result=None."""
        last = _make_last(symbol="ETH")
        grp = _make_grp(last)
        pos = _make_pos()
        result = judge_btc_with_signal(
            last, grp, 5, 0.3, 0.7, 200, None, 18.0, cycle_position=pos
        )
        self.assertIsNone(result[9])

    def test_bull_signal_exit_for_late_bull(self):
        """Bull 후반 + 상단 → EXIT."""
        last = _make_last(symbol="BTC")
        grp = _make_grp(last)
        pos = _make_pos(phase="BULL", box_progress=0.9, price_position=0.85, is_near_target=True)
        result = judge_btc_with_signal(
            last, grp, 5, 0.7, 0.3, None, None, cycle_position=pos
        )
        self.assertEqual(result[9].signal, SIGNAL_EXIT)

    def test_pred_is_bull_zero_when_force_bear(self):
        """force_bear 조건 → pred_is_bull=0 유지."""
        last = _make_last(end_x=50)  # end_x < bottom_day → before_bottom → force_bear
        grp = _make_grp(last)
        result = judge_btc_with_signal(
            last, grp, 5, 0.8, 0.2, 200, None, 18.0, cycle_position=_make_pos()
        )
        pred_is_bull = result[0]
        self.assertEqual(pred_is_bull, 0)


if __name__ == "__main__":
    unittest.main()
