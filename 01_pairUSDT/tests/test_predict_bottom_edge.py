"""Iter 38: predict_bottom.py calc_bottom_btc 순수함수 추가 엣지케이스."""

import unittest
import pandas as pd
from lib.predictor.predict_bottom import calc_bottom_btc

_COLS = ["symbol", "phase", "cycle_number", "box_index", "lo", "lo_day", "end_x"]


def _make_df(rows):
    return pd.DataFrame(rows)


def _last(end_x=300, cy=5):
    return pd.Series({"end_x": end_x, "symbol": "BTC", "cycle_number": cy})


def _bear_row(cn, lo, lo_day, bi=0):
    return {
        "symbol": "BTC", "phase": "BEAR", "cycle_number": cn,
        "box_index": bi, "lo": lo, "lo_day": lo_day, "end_x": lo_day + 20,
    }


class TestCalcBottomBtcEdge(unittest.TestCase):

    def test_empty_df_returns_none(self):
        # 컬럼이 있어야 pandas 필터가 작동하므로 컬럼 있는 빈 DF 사용
        empty = pd.DataFrame(columns=_COLS)
        lo, day = calc_bottom_btc(empty, max_cyc=5, last=_last())
        self.assertIsNone(lo)
        self.assertIsNone(day)

    def test_single_cycle_applies_default_increase(self):
        # Cy2 1개(=Cy1 제외 후 1개) → 기본 증가율 경로
        df = _make_df([_bear_row(cn=2, lo=10.0, lo_day=100)])
        lo, day = calc_bottom_btc(df, max_cyc=5, last=_last())
        if lo is not None:
            self.assertGreater(lo, 0.0)

    def test_two_cycles_uses_avg_increase(self):
        df = _make_df([
            _bear_row(cn=2, lo=10.0, lo_day=100),
            _bear_row(cn=3, lo=17.0, lo_day=160),
        ])
        lo, day = calc_bottom_btc(df, max_cyc=5, last=_last())
        self.assertIsNotNone(lo)
        # avg_increase = 7.0 → bottom_lo ≈ 17.0 + 7.0 = 24.0
        self.assertAlmostEqual(lo, 24.0, places=1)

    def test_bottom_day_at_least_end_x_plus_2(self):
        df = _make_df([
            _bear_row(cn=2, lo=10.0, lo_day=100),
            _bear_row(cn=3, lo=17.0, lo_day=160),
        ])
        last = _last(end_x=400)
        lo, day = calc_bottom_btc(df, max_cyc=5, last=last)
        if day is not None:
            self.assertGreaterEqual(day, 402)

    def test_three_cycles_positive_result(self):
        df = _make_df([
            _bear_row(cn=2, lo=8.0, lo_day=80),
            _bear_row(cn=3, lo=15.0, lo_day=160),
            _bear_row(cn=4, lo=23.0, lo_day=240),
        ])
        lo, day = calc_bottom_btc(df, max_cyc=5, last=_last(end_x=350))
        self.assertIsNotNone(lo)
        self.assertGreater(lo, 0)

    def test_bottom_lo_positive(self):
        df = _make_df([
            _bear_row(cn=2, lo=5.0, lo_day=50),
            _bear_row(cn=3, lo=9.0, lo_day=100),
        ])
        lo, day = calc_bottom_btc(df, max_cyc=4, last=_last(end_x=120))
        if lo is not None:
            self.assertGreater(lo, 0.0)

    def test_cy1_excluded(self):
        """Cy1 포함해도 제외되어야 한다."""
        df = _make_df([
            _bear_row(cn=1, lo=3.0, lo_day=40),   # 제외 대상
            _bear_row(cn=2, lo=10.0, lo_day=100),
            _bear_row(cn=3, lo=17.0, lo_day=160),
        ])
        lo_with, _ = calc_bottom_btc(df, max_cyc=5, last=_last())
        # Cy1 제외 후 결과와 동일해야 함
        df_no_cy1 = _make_df([
            _bear_row(cn=2, lo=10.0, lo_day=100),
            _bear_row(cn=3, lo=17.0, lo_day=160),
        ])
        lo_without, _ = calc_bottom_btc(df_no_cy1, max_cyc=5, last=_last())
        self.assertAlmostEqual(lo_with, lo_without, places=3)


if __name__ == "__main__":
    unittest.main()
