"""BTC 사이클 Bear/Bull 박스 수 예측 로직 테스트 (명세 T01~T10+)."""
import sqlite3
import pytest

from lib.predictor.predict_cycle_box_count import (
    get_btc_completed_cycle_box_counts,
    predict_cycle_box_counts,
    _linear_regression_predict,
    _apply_guards,
    CyclePrediction,
    METHOD_LINEAR_REGRESSION,
)
from lib.common.config import MIN_BOX_COUNT, BEAR_GUARD_DELTA, MAX_BEAR_CHAIN, MAX_BULL_CHAIN


def _make_conn_with_btc_boxes(cycle_counts: list[tuple[int, int, int]]) -> sqlite3.Connection:
    """cycle_counts = [(cycle_number, bear_count, bull_count), ...]. 각 박스당 1행 삽입."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE coin_analysis_results (
            coin_id TEXT, symbol TEXT, coin_rank INT, cycle_number INT,
            cycle_name TEXT, box_index INT, phase TEXT, result TEXT,
            start_x INT, end_x INT, hi REAL, lo REAL, hi_day INT, lo_day INT,
            duration INT, range_pct REAL, hi_change_pct REAL, lo_change_pct REAL,
            gain_pct REAL, norm_hi REAL, norm_lo REAL, norm_range_pct REAL,
            norm_duration REAL, norm_hi_change_pct REAL, norm_lo_change_pct REAL,
            norm_gain_pct REAL, is_completed INT, is_prediction INT
        )
    """)
    for (cyc, bear_cnt, bull_cnt) in cycle_counts:
        for i in range(bear_cnt):
            conn.execute(
                """INSERT INTO coin_analysis_results (
                    coin_id, symbol, coin_rank, cycle_number, cycle_name, box_index,
                    phase, result, start_x, end_x, hi, lo, hi_day, lo_day,
                    duration, range_pct, hi_change_pct, lo_change_pct, gain_pct,
                    norm_hi, norm_lo, norm_range_pct, norm_duration,
                    norm_hi_change_pct, norm_lo_change_pct, norm_gain_pct,
                    is_completed, is_prediction
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("btc-1", "BTC", 1, cyc, f"Cy{cyc}", i, "BEAR", "DONE",
                 1, 50, 80.0, 60.0, 10, 40, 50, 30.0, 0, 0, -40.0,
                 4.5, 4.0, 4.2, 2.1, 0.5, -0.3, 0.2, 1, 0),
            )
        for i in range(bull_cnt):
            conn.execute(
                """INSERT INTO coin_analysis_results (
                    coin_id, symbol, coin_rank, cycle_number, cycle_name, box_index,
                    phase, result, start_x, end_x, hi, lo, hi_day, lo_day,
                    duration, range_pct, hi_change_pct, lo_change_pct, gain_pct,
                    norm_hi, norm_lo, norm_range_pct, norm_duration,
                    norm_hi_change_pct, norm_lo_change_pct, norm_gain_pct,
                    is_completed, is_prediction
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("btc-1", "BTC", 1, cyc, f"Cy{cyc}", bear_cnt + i, "BULL", "DONE",
                 51, 100, 120.0, 90.0, 70, 95, 50, 33.0, 0, 0, 20.0,
                 4.5, 4.0, 4.2, 2.1, 0.5, -0.3, 0.2, 1, 0),
            )
    conn.commit()
    return conn


# 명세: Cycle 1 (2011): Bear=4, Bull=3; Cycle 2 (2013): Bear=3, Bull=5; Cycle 3 (2017): Bear=4, Bull=6; Cycle 4 (2021): Bear=7, Bull=7
SPEC_COUNTS = [(1, 4, 3), (2, 3, 5), (3, 4, 6), (4, 7, 7)]


class TestGetBtcCompletedCycleBoxCounts:
    """T01, T02: bear_count / bull_count 집계."""

    def test_t01_bear_count_aggregation(self):
        conn = _make_conn_with_btc_boxes(SPEC_COUNTS)
        counts = get_btc_completed_cycle_box_counts(conn)
        conn.close()
        bear_counts = [c[1] for c in counts]
        assert bear_counts == [4, 3, 4, 7]

    def test_t02_bull_count_aggregation(self):
        conn = _make_conn_with_btc_boxes(SPEC_COUNTS)
        counts = get_btc_completed_cycle_box_counts(conn)
        conn.close()
        bull_counts = [c[2] for c in counts]
        assert bull_counts == [3, 5, 6, 7]


class TestLinearRegression:
    """T03, T04: 회귀 예측값 방향/크기."""

    def test_t03_bear_prediction_positive(self):
        points = [(1, 4), (2, 3), (3, 4), (4, 7)]
        pred = _linear_regression_predict(points, 5)
        assert pred > 0

    def test_t04_bull_prediction_ge_7(self):
        points = [(1, 3), (2, 5), (3, 6), (4, 7)]
        pred = _linear_regression_predict(points, 5)
        assert pred >= 7 or round(pred) >= 7


class TestGuards:
    """T05, T06: Guard 적용."""

    def test_t05_bear_guard_prev_minus_one(self):
        # cycle6 bear >= cycle5 bear - 1
        prev_bear, prev_bull = 7, 6
        raw_bear, raw_bull = 5.0, 8.0
        bear_count, bull_count, g_bear, g_bull = _apply_guards(
            raw_bear, raw_bull, prev_bear, prev_bull
        )
        assert bear_count >= prev_bear - BEAR_GUARD_DELTA

    def test_t06_bull_guard_prev_or_higher(self):
        prev_bear, prev_bull = 7, 6
        raw_bear, raw_bull = 7.5, 4.0
        bear_count, bull_count, g_bear, g_bull = _apply_guards(
            raw_bear, raw_bull, prev_bear, prev_bull
        )
        assert bull_count >= prev_bull


class TestEarlyReturnAndFallback:
    """T07, T08: 빈 배열 / 사이클 1개."""

    def test_t07_empty_db_returns_none(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE coin_analysis_results (
                coin_id TEXT, symbol TEXT, cycle_number INT, phase TEXT, is_completed INT
            )
        """)
        conn.commit()
        result = predict_cycle_box_counts(conn, 5)
        conn.close()
        assert result is None

    def test_t08_single_cycle_returns_none(self):
        conn = _make_conn_with_btc_boxes([(1, 4, 3)])
        result = predict_cycle_box_counts(conn, 2)
        conn.close()
        assert result is None


class TestIntegerAndGuardFlags:
    """T09, T10: 정수 반환, guardApplied 플래그."""

    def test_t09_prediction_values_are_integers(self):
        conn = _make_conn_with_btc_boxes(SPEC_COUNTS)
        result = predict_cycle_box_counts(conn, 5)
        conn.close()
        assert result is not None
        assert isinstance(result.bear_count, int)
        assert isinstance(result.bull_count, int)
        assert result.total_count == result.bear_count + result.bull_count

    def test_t10_guard_applied_flags(self):
        conn = _make_conn_with_btc_boxes(SPEC_COUNTS)
        result = predict_cycle_box_counts(conn, 5)
        conn.close()
        assert result is not None
        assert "bear" in result.guard_applied
        assert "bull" in result.guard_applied
        assert isinstance(result.guard_applied["bear"], bool)
        assert isinstance(result.guard_applied["bull"], bool)


class TestIntegration:
    """추가: Cycle 5/6 예측, method 필드, MIN_BOX_COUNT."""

    def test_cycle5_prediction_structure(self):
        conn = _make_conn_with_btc_boxes(SPEC_COUNTS)
        result = predict_cycle_box_counts(conn, 5)
        conn.close()
        assert result is not None
        assert result.cycle_number == 5
        assert result.method == METHOD_LINEAR_REGRESSION
        assert result.bear_count >= MIN_BOX_COUNT
        assert result.bull_count >= MIN_BOX_COUNT

    def test_cycle6_prediction_uses_cycle5_as_prev(self):
        conn = _make_conn_with_btc_boxes(SPEC_COUNTS)
        result5 = predict_cycle_box_counts(conn, 5)
        result6 = predict_cycle_box_counts(conn, 6)
        conn.close()
        assert result5 is not None and result6 is not None
        assert result6.cycle_number == 6
        assert result6.bear_count >= result5.bear_count - BEAR_GUARD_DELTA
        assert result6.bull_count >= result5.bull_count

    def test_linear_regression_two_points(self):
        pred = _linear_regression_predict([(1, 2), (2, 4)], 3)
        assert pred == pytest.approx(6.0)

    def test_linear_regression_one_point_returns_zero(self):
        pred = _linear_regression_predict([(1, 5)], 2)
        assert pred == 0.0
