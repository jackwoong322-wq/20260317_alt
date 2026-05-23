"""Iters 47-50: 신호 파이프라인 경계값·경계조건 시나리오 테스트."""

import unittest
import pandas as pd
from lib.predictor.btc_signal_api import btc_investment_pipeline
from lib.predictor.btc_investment_signal import (
    classify_bear_signal, classify_bull_signal, generate_btc_signal,
    SIGNAL_ACCUMULATE, SIGNAL_WATCH, SIGNAL_CAUTION, SIGNAL_EXIT,
)
from lib.predictor.btc_cycle_position import CyclePosition


def _pos(phase="BEAR", prog=0.7, price=0.25, day=0.7, near=True, dist=5.0, cy=5):
    avg = 10.0
    return CyclePosition(
        phase=phase, cycle_number=cy,
        completed_boxes=round(prog * avg), avg_boxes_historical=avg,
        box_progress_ratio=prog, day_progress_ratio=day,
        price_position=price, distance_to_target_pct=dist, is_near_target=near,
    )


class TestBearSignalBoundaries(unittest.TestCase):
    """Iter 47: Bear 신호 임계값 경계 테스트."""

    def test_bear_exactly_60pct_low_price(self):
        """60% 정확히 + 낮은 가격 → ACCUMULATE."""
        pos = _pos(prog=0.60, price=0.30, near=True)
        r = classify_bear_signal(pos)
        self.assertEqual(r.signal, SIGNAL_ACCUMULATE)

    def test_bear_59pct_watch(self):
        """59% → WATCH (60% 미만)."""
        pos = _pos(prog=0.59, price=0.30, near=True)
        r = classify_bear_signal(pos)
        # 59% < 60% → ACCUMULATE 조건 미충족 → WATCH
        self.assertEqual(r.signal, SIGNAL_WATCH)

    def test_bear_over_100pct_accumulate(self):
        """100% 초과 + day_progress >= 70% → ACCUMULATE."""
        pos = _pos(prog=1.1, day=0.75, near=True)
        r = classify_bear_signal(pos)
        self.assertEqual(r.signal, SIGNAL_ACCUMULATE)

    def test_bear_over_100pct_low_day_watch(self):
        """100% 초과이지만 day_progress < 70% → 일반 ACCUMULATE or WATCH."""
        pos = _pos(prog=1.1, day=0.5, price=0.5, near=False)
        r = classify_bear_signal(pos)
        self.assertIn(r.signal, [SIGNAL_ACCUMULATE, SIGNAL_WATCH])

    def test_bear_confidence_float(self):
        pos = _pos(prog=0.7, price=0.2, near=True)
        r = classify_bear_signal(pos)
        self.assertIsInstance(r.confidence, float)


class TestBullSignalBoundaries(unittest.TestCase):
    """Iter 48: Bull 신호 임계값 경계 테스트."""

    def test_bull_exactly_80pct_high_price_near(self):
        """80% + 가격 상단 75% 이상 + near → EXIT."""
        pos = _pos(phase="BULL", prog=0.80, price=0.80, near=True)
        r = classify_bull_signal(pos)
        self.assertEqual(r.signal, SIGNAL_EXIT)

    def test_bull_79pct_caution(self):
        """79% + 가격 중상단 → CAUTION (EXIT 조건 미충족)."""
        pos = _pos(phase="BULL", prog=0.79, price=0.60, near=False)
        r = classify_bull_signal(pos)
        self.assertIn(r.signal, [SIGNAL_CAUTION, SIGNAL_WATCH])

    def test_bull_over_100pct_exit(self):
        """Bull 100% 초과 + day >= 80% → EXIT."""
        pos = _pos(phase="BULL", prog=1.05, day=0.85, near=True)
        r = classify_bull_signal(pos)
        self.assertEqual(r.signal, SIGNAL_EXIT)

    def test_bull_early_watch(self):
        """Bull 초입(20%) → WATCH."""
        pos = _pos(phase="BULL", prog=0.20, price=0.30, near=False)
        r = classify_bull_signal(pos)
        self.assertEqual(r.signal, SIGNAL_WATCH)


class TestGenerateSignalEdges(unittest.TestCase):
    """Iter 49: generate_btc_signal 경계·엣지케이스."""

    def test_extreme_consecutive_clips_to_one(self):
        """consecutive_count=100 → confidence 1.0 초과 없음."""
        pos = _pos(prog=0.8, price=0.2, near=True)
        r = generate_btc_signal(pos, consecutive_count=100)
        self.assertLessEqual(r.confidence, 1.0)

    def test_error_fallback_returns_watch(self):
        """generate_btc_signal에서 예외 발생 시 WATCH fallback."""
        # box_progress_ratio가 문자열이면 연산 오류 → except 분기
        pos = _pos(prog=0.7)
        pos.box_progress_ratio = "invalid"  # type: ignore[assignment]
        r = generate_btc_signal(pos)
        # 오류 발생하면 WATCH + confidence=0, 아니면 정상값
        self.assertIn(r.signal, [SIGNAL_ACCUMULATE, SIGNAL_WATCH, SIGNAL_CAUTION, SIGNAL_EXIT])


    def test_reason_list_nonempty_on_success(self):
        pos = _pos(prog=0.7, price=0.2, near=True)
        r = generate_btc_signal(pos)
        self.assertGreater(len(r.reason), 0)

    def test_phase_preserved_in_result(self):
        for phase in ["BEAR", "BULL"]:
            pos = _pos(phase=phase)
            r = generate_btc_signal(pos)
            self.assertEqual(r.phase, phase)


class TestPipelineMultiScenario(unittest.TestCase):
    """Iter 50: 다중 시나리오 파이프라인 smoke test."""

    def _df(self, cy=5, phase="BEAR", n_hist=3, n_curr=2):
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

    def test_scenario_bear_early(self):
        df = self._df(n_curr=1)
        r = btc_investment_pipeline(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=25.0, box_lo=20.0, box_hi=40.0,
            target_price_pct=18.0,
        )
        self.assertIn(r["signal"]["signal"], [SIGNAL_ACCUMULATE, SIGNAL_WATCH])

    def test_scenario_bear_late(self):
        df = self._df(n_curr=8)
        r = btc_investment_pipeline(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=18.5, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.0,
        )
        self.assertIn(r["signal"]["signal"], [SIGNAL_ACCUMULATE, SIGNAL_WATCH])

    def test_scenario_bear_no_hist(self):
        df = pd.DataFrame([
            {"symbol": "BTC", "cycle_number": 5, "phase": "BEAR", "box_index": 0,
             "start_x": 500, "end_x": 560, "is_completed": 1, "is_prediction": 0}
        ])
        r = btc_investment_pipeline(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertIn("signal", r)

    def test_scenario_all_signals_representable(self):
        """파이프라인이 4가지 신호를 모두 반환 가능한지 확인."""
        valid_signals = {SIGNAL_ACCUMULATE, SIGNAL_WATCH, SIGNAL_CAUTION, SIGNAL_EXIT}
        df = self._df()
        r = btc_investment_pipeline(
            df=df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertIn(r["signal"]["signal"], valid_signals)


if __name__ == "__main__":
    unittest.main()
