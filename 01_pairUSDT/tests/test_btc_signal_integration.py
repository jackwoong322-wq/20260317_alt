"""Integration smoke test — Iteration 19.

BTC 투자 타이밍 신호 생성 파이프라인 전체 통합 검증.
DataFrame → CyclePosition → SignalResult → API payload 전 과정.
외부 DB 없이 mock DataFrame으로 완전 검증.
"""

import unittest
import pandas as pd

from lib.predictor.btc_signal_adapter import build_cycle_position_from_df
from lib.predictor.btc_investment_signal import generate_btc_signal, SIGNAL_ACCUMULATE, SIGNAL_EXIT
from lib.predictor.btc_signal_payload import build_btc_signal_response, SIGNAL_DISPLAY


def _make_full_df():
    """과거 2사이클 + 현재 사이클 Bear 데이터."""
    rows = [
        # cy3 BEAR: 3박스 완료
        {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": 0,
         "start_x": 100, "end_x": 150, "is_completed": 1, "is_prediction": 0},
        {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": 1,
         "start_x": 151, "end_x": 200, "is_completed": 1, "is_prediction": 0},
        {"symbol": "BTC", "cycle_number": 3, "phase": "BEAR", "box_index": 2,
         "start_x": 201, "end_x": 260, "is_completed": 1, "is_prediction": 0},
        # cy4 BEAR: 2박스 완료 + 1박스 미완료
        {"symbol": "BTC", "cycle_number": 4, "phase": "BEAR", "box_index": 0,
         "start_x": 300, "end_x": 360, "is_completed": 1, "is_prediction": 0},
        {"symbol": "BTC", "cycle_number": 4, "phase": "BEAR", "box_index": 1,
         "start_x": 361, "end_x": 420, "is_completed": 1, "is_prediction": 0},
        # cy5 BEAR 현재: 2박스 완료 (진행률 ≈ 80% → ACCUMULATE 근접)
        {"symbol": "BTC", "cycle_number": 5, "phase": "BEAR", "box_index": 0,
         "start_x": 500, "end_x": 560, "is_completed": 1, "is_prediction": 0},
        {"symbol": "BTC", "cycle_number": 5, "phase": "BEAR", "box_index": 1,
         "start_x": 561, "end_x": 620, "is_completed": 1, "is_prediction": 0},
    ]
    return pd.DataFrame(rows)


class TestFullPipeline(unittest.TestCase):

    def setUp(self):
        self.df = _make_full_df()

    def test_adapter_extracts_position(self):
        """DataFrame → CyclePosition 변환 성공."""
        pos = build_cycle_position_from_df(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=22.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertEqual(pos.completed_boxes, 2)
        # avg: (3+2)/2 = 2.5 → progress=2/2.5=0.8
        self.assertAlmostEqual(pos.box_progress_ratio, 0.8, places=4)

    def test_signal_generated_from_position(self):
        """CyclePosition → SignalResult 생성 성공."""
        pos = build_cycle_position_from_df(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.5,  # 현재가 20, 목표 18.5 → near (7.5%)
        )
        signal = generate_btc_signal(pos)
        self.assertIn(signal.signal, ["ACCUMULATE", "WATCH"])

    def test_api_payload_structure(self):
        """전체 파이프라인 → API payload 구조 검증."""
        payload = build_btc_signal_response(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.5,
        )
        self.assertIn("signal", payload)
        self.assertIn("display", payload)
        self.assertIn("cycle_position", payload)
        self.assertEqual(payload["symbol"], "BTC")

    def test_display_valid_signal_key(self):
        """display의 신호 키는 SIGNAL_DISPLAY에 존재."""
        payload = build_btc_signal_response(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=18.5,
        )
        signal_key = payload["signal"].get("signal", "WATCH")
        self.assertIn(signal_key, SIGNAL_DISPLAY)

    def test_accumulate_for_late_bear_low_price(self):
        """Bear 후반 + 저가격 → ACCUMULATE 기대."""
        pos = build_cycle_position_from_df(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=19.0,   # 박스 하단 근처
            box_lo=18.0, box_hi=35.0,
            target_price_pct=18.5,    # 목표가 근접 (7.9%)
        )
        signal = generate_btc_signal(pos)
        # box_progress=0.8 >= 0.6, price_pos=(19-18)/(35-18)=0.059 <= 0.35
        self.assertEqual(signal.signal, SIGNAL_ACCUMULATE)

    def test_empty_df_fallback(self):
        """빈 DF → fallback 사용, 에러 없음."""
        payload = build_btc_signal_response(
            df=pd.DataFrame(), cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertIn("signal", payload)

    def test_completed_boxes_in_cycle_position(self):
        """API payload의 cycle_position.completed_boxes 정확성."""
        payload = build_btc_signal_response(
            df=self.df, cycle_number=5, phase="BEAR",
            current_price_pct=20.0, box_lo=18.0, box_hi=35.0,
            target_price_pct=17.0,
        )
        self.assertEqual(payload["cycle_position"]["completed_boxes"], 2)


if __name__ == "__main__":
    unittest.main()
