"""Tests for predictor modules with mock-based DB access."""

from unittest.mock import patch

import pandas as pd

from lib.predictor.predict_schema import CREATE_PATHS_SQL, CREATE_PEAKS_SQL
from lib.predictor.predict_btc_anchor import calc_btc_anchor
from lib.predictor.predict_features import build_feature_vector
from lib.predictor.predict_box_bull import build_bull_path_rows
from lib.predictor.predict_judge import judge_bull_bear
from lib.predictor.predict import (
    predict_and_insert,
    print_prediction_summary,
    rebuild_prediction_paths,
)


class _FakeExecResult:
    def __init__(self, rows=None, rowcount=0):
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self):
        self.executed = []
        self.executemany_calls = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "DELETE FROM coin_analysis_results" in sql:
            return _FakeExecResult(rowcount=0)
        return _FakeExecResult()

    def executemany(self, sql, rows):
        self.executemany_calls.append((sql, rows))

    def commit(self):
        return None

    def cursor(self):
        return self


class TestSchemaConstants:
    def test_create_paths_sql_contains_required_columns(self):
        assert "coin_prediction_paths" in CREATE_PATHS_SQL
        assert "coin_id" in CREATE_PATHS_SQL
        assert "scenario" in CREATE_PATHS_SQL

    def test_create_peaks_sql_contains_required_columns(self):
        assert "coin_prediction_peaks" in CREATE_PEAKS_SQL
        assert "peak_type" in CREATE_PEAKS_SQL
        assert "predicted_day" in CREATE_PEAKS_SQL


class TestCoreHelpers:
    def test_calc_btc_anchor_returns_none_when_no_btc(self):
        df = pd.DataFrame(
            {
                "coin_id": ["eth-1"],
                "symbol": ["ETH"],
                "cycle_number": [1],
                "box_index": [0],
                "end_x": [100],
                "is_completed": [1],
                "lo": [50.0],
                "gain_pct": [0.0],
                "lo_change_pct": [0.0],
            }
        )
        cycle_stats = {("eth-1", 1): {"total_days": 100, "low_x": 50}}
        coin_stats = {"eth-1": {"avg_cycle_days": 100}}
        assert calc_btc_anchor(df, cycle_stats, coin_stats) is None

    def test_build_feature_vector_returns_dict(self):
        last = pd.Series(
            {
                "norm_range_pct": 10.0,
                "norm_hi_change_pct": 5.0,
                "norm_lo_change_pct": -2.0,
                "norm_gain_pct": 3.0,
                "norm_duration": 2.0,
                "phase": "BULL",
                "box_index": 2,
                "end_x": 80,
                "hi": 120.0,
                "lo": 90.0,
                "coin_rank": 1,
                "symbol": "BTC",
            }
        )
        cycle_stats = {("btc-1", 1): {"total_days": 100, "low_x": 50, "min_lo": 80.0}}
        coin_stats = {"btc-1": {"avg_cycle_days": 100, "mean_lo": 85.0, "min_lo": 80.0}}
        phase_box_stats = {("btc-1", "BULL"): 5.0}
        feat, avg_days = build_feature_vector(
            last, "btc-1", 1, cycle_stats, coin_stats, phase_box_stats
        )
        assert isinstance(feat, dict)
        assert avg_days == 100.0

    def test_build_bull_path_rows_starts_from_current_point(self):
        last = pd.Series({"symbol": "BTC", "phase": "BULL"})
        rows = build_bull_path_rows(
            "btc-1",
            last,
            1,
            cur_day=100,
            cur_val=90.0,
            bull_start=101,
            bull_end=150,
            bull_hi=150.0,
            bull_lo=95.0,
            peak_day=125,
        )
        assert isinstance(rows, list)
        assert rows and rows[0][0] == "btc-1"

    def test_judge_bull_bear_returns_tuple(self):
        last = pd.Series(
            {
                "lo": 95.0,
                "gain_pct": 5.0,
                "lo_change_pct": 2.0,
                "symbol": "BTC",
                "end_x": 100,
            }
        )
        grp = pd.DataFrame({"lo": [90.0, 95.0], "end_x": [50, 100]})
        result = judge_bull_bear(
            last,
            grp,
            1,
            prob_bull=0.7,
            prob_bear=0.3,
            bottom_day=None,
            btc_anchor=None,
            bottom_lo=None,
        )
        assert isinstance(result, tuple)
        assert len(result) >= 5


class TestPredictFlow:
    def test_predict_and_insert_returns_int_with_mocked_dependencies(self):
        conn = _FakeConn()
        df_all = pd.DataFrame(
            [
                {
                    "coin_id": "btc-1",
                    "cycle_number": 1,
                    "box_index": 0,
                    "is_completed": 1,
                    "is_prediction": 0,
                    "phase": "BULL",
                    "symbol": "BTC",
                    "end_x": 50,
                    "hi": 120.0,
                    "lo": 90.0,
                    "coin_rank": 1,
                }
            ]
        )

        with patch(
            "lib.predictor.predict.build_cycle_and_coin_stats",
            return_value=({}, {}, {}, {}),
        ), patch("lib.predictor.predict.calc_btc_anchor", return_value=None), patch(
            "lib.predictor.predict.compute_cross_coin_peak_ratio", return_value=None
        ), patch(
            "lib.predictor.predict._predict_one_coin", return_value=([], [], [], True)
        ), patch(
            "lib.predictor.predict._insert_predictions_to_db", return_value=None
        ):
            count = predict_and_insert(conn, df_all, pd.DataFrame(), {}, {}, {})

        assert isinstance(count, int)
        assert count == 0

    def test_rebuild_prediction_paths_no_crash_with_mock_conn(self):
        conn = _FakeConn()
        conn._rows_for_select = []

        def _execute(sql, params=None):
            if "FROM coin_prediction_peaks" in sql:
                return _FakeExecResult([])
            if "FROM coin_analysis_results" in sql:
                return _FakeExecResult([])
            return _FakeExecResult()

        conn.execute = _execute
        rebuild_prediction_paths(conn)

    def test_print_prediction_summary_handles_empty(self):
        conn = _FakeConn()
        with patch(
            "lib.predictor.predict.ensure_analysis_result_columns", return_value=None
        ), patch(
            "lib.predictor.predict.pd.read_sql_query", return_value=pd.DataFrame()
        ):
            print_prediction_summary(conn)
