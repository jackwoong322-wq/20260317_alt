"""Tests for lib.predictor.predict module and submodules.

Run: python -m pytest tests/test_predict.py -v
"""

import sqlite3
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Before refactor: import from predict
# After refactor: import from submodules
try:
    from lib.predictor.predict_schema import CREATE_PATHS_SQL, CREATE_PEAKS_SQL
except ImportError:
    from lib.predictor.predict import CREATE_PATHS_SQL, CREATE_PEAKS_SQL

try:
    from lib.predictor.predict_btc_anchor import calc_btc_anchor
except ImportError:
    from lib.predictor.predict import _calc_btc_anchor as calc_btc_anchor

try:
    from lib.predictor.predict_features import build_feature_vector
except ImportError:
    from lib.predictor.predict import _build_feature_vector as build_feature_vector

try:
    from lib.predictor.predict_box_bull import build_bull_path_rows
except ImportError:
    from lib.predictor.predict import _build_bull_path_rows as build_bull_path_rows

try:
    from lib.predictor.predict_judge import judge_bull_bear
except ImportError:
    from lib.predictor.predict import _judge_bull_bear as judge_bull_bear

from lib.predictor.predict import (
    predict_and_insert,
    print_prediction_summary,
    rebuild_prediction_paths,
)
from lib.predictor.data import build_cycle_and_coin_stats, load_box_df


# --- Schema constants ---
class TestSchemaConstants:
    def test_create_paths_sql_contains_required_columns(self):
        assert "coin_prediction_paths" in CREATE_PATHS_SQL
        assert "coin_id" in CREATE_PATHS_SQL
        assert "symbol" in CREATE_PATHS_SQL
        assert "cycle_number" in CREATE_PATHS_SQL
        assert "scenario" in CREATE_PATHS_SQL
        assert "start_x" in CREATE_PATHS_SQL
        assert "end_x" in CREATE_PATHS_SQL
        assert "day_x" in CREATE_PATHS_SQL
        assert "value" in CREATE_PATHS_SQL

    def test_create_peaks_sql_contains_required_columns(self):
        assert "coin_prediction_peaks" in CREATE_PEAKS_SQL
        assert "coin_id" in CREATE_PEAKS_SQL
        assert "symbol" in CREATE_PEAKS_SQL
        assert "peak_type" in CREATE_PEAKS_SQL
        assert "predicted_value" in CREATE_PEAKS_SQL
        assert "predicted_day" in CREATE_PEAKS_SQL


# --- calc_btc_anchor ---
class TestCalcBtcAnchor:
    def test_returns_none_when_no_btc(self):
        df = pd.DataFrame({
            "coin_id": ["eth-1"],
            "symbol": ["ETH"],
            "cycle_number": [1],
            "box_index": [0],
            "end_x": [100],
            "is_completed": [1],
            "lo": [50.0],
            "gain_pct": [0.0],
            "lo_change_pct": [0.0],
        })
        cycle_stats = {("eth-1", 1): {"total_days": 100, "low_x": 50}}
        coin_stats = {"eth-1": {"avg_cycle_days": 100}}
        result = calc_btc_anchor(df, cycle_stats, coin_stats)
        assert result is None

    def test_returns_anchor_when_btc_present(self):
        df = pd.DataFrame({
            "coin_id": ["btc-1", "btc-1"],
            "symbol": ["BTC", "BTC"],
            "cycle_number": [1, 1],
            "box_index": [0, 1],
            "end_x": [50, 100],
            "is_completed": [1, 0],
            "lo": [80.0, 75.0],
            "gain_pct": [5.0, -2.0],
            "lo_change_pct": [0.0, -3.0],
        })
        cycle_stats = {("btc-1", 1): {"total_days": 100, "low_x": 50}}
        coin_stats = {"btc-1": {"avg_cycle_days": 100}}
        result = calc_btc_anchor(df, cycle_stats, coin_stats)
        assert result is not None
        assert "coin_id" in result
        assert "cycle_number" in result
        assert "cycle_progress_ratio" in result
        assert "lower_low" in result
        assert "slope_down" in result


# --- build_feature_vector ---
class TestBuildFeatureVector:
    def test_returns_feat_and_avg_cycle_days(self):
        last = pd.Series({
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
        })
        cycle_stats = {("btc-1", 1): {"total_days": 100, "low_x": 50, "min_lo": 80.0}}
        coin_stats = {"btc-1": {"avg_cycle_days": 100, "mean_lo": 85.0, "min_lo": 80.0}}
        phase_box_stats = {("btc-1", "BULL"): 5.0}
        feat, avg_days = build_feature_vector(
            last, "btc-1", 1, cycle_stats, coin_stats, phase_box_stats
        )
        assert isinstance(feat, dict)
        assert "norm_range_pct" in feat
        assert "is_bull" in feat
        assert "box_index" in feat
        assert avg_days == 100.0


# --- build_bull_path_rows ---
class TestBuildBullPathRows:
    def test_returns_list_of_tuples(self):
        last = pd.Series({"symbol": "BTC", "phase": "BULL"})
        rows = build_bull_path_rows(
            "btc-1", last, 1,
            cur_day=100, cur_val=90.0,
            bull_start=101, bull_end=150,
            bull_hi=150.0, bull_lo=95.0,
            peak_day=125,
        )
        assert isinstance(rows, list)
        assert len(rows) >= 1
        for r in rows:
            assert len(r) == 8
            assert r[0] == "btc-1"
            assert r[2] == 1
            assert r[3] == "bull"

    def test_includes_start_point(self):
        last = pd.Series({"symbol": "ETH", "phase": "BEAR"})
        rows = build_bull_path_rows(
            "eth-1", last, 2,
            cur_day=200, cur_val=80.0,
            bull_start=201, bull_end=250,
            bull_hi=120.0, bull_lo=85.0,
            peak_day=225,
        )
        assert any(r[6] == 200 and r[7] == 80.0 for r in rows)


# --- judge_bull_bear ---
class TestJudgeBullBear:
    def test_returns_bull_when_prob_bull_higher_and_no_force_bear(self):
        # last.lo must be >= prev.lo to avoid lower_low (force_bear)
        last = pd.Series({
            "lo": 95.0, "gain_pct": 5.0, "lo_change_pct": 2.0,
            "symbol": "BTC", "end_x": 100,
        })
        grp = pd.DataFrame({"lo": [90.0, 95.0], "end_x": [50, 100]})
        pred_is_bull, *rest = judge_bull_bear(
            last, grp, 1, prob_bull=0.7, prob_bear=0.3,
            bottom_day=None, btc_anchor=None, bottom_lo=None,
        )
        assert pred_is_bull == 1

    def test_returns_bear_when_force_bear_before_bottom(self):
        last = pd.Series({
            "lo": 90.0, "gain_pct": 5.0, "lo_change_pct": 2.0,
            "symbol": "BTC", "end_x": 100,
        })
        grp = pd.DataFrame({"lo": [95.0, 90.0], "end_x": [50, 100]})
        pred_is_bull, *rest = judge_bull_bear(
            last, grp, 1, prob_bull=0.7, prob_bear=0.3,
            bottom_day=150, btc_anchor=None, bottom_lo=80.0,
        )
        # end_x=100 < bottom_day=150 -> force_bear
        assert pred_is_bull == 0

    def test_returns_tuple_with_expected_length(self):
        last = pd.Series({
            "lo": 95.0, "gain_pct": 10.0, "lo_change_pct": 5.0,
            "symbol": "ETH", "end_x": 200,
        })
        grp = pd.DataFrame({"lo": [100.0, 95.0], "end_x": [150, 200]})
        result = judge_bull_bear(
            last, grp, 1, prob_bull=0.6, prob_bear=0.4,
            bottom_day=180, btc_anchor=None, bottom_lo=85.0,
        )
        assert len(result) >= 5


# --- predict_and_insert (mock) ---
class TestPredictAndInsert:
    def test_deletes_existing_predictions_and_inserts(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE coin_analysis_results (
                coin_id TEXT, symbol TEXT, coin_rank INT, cycle_number INT,
                cycle_name TEXT, box_index INT, phase TEXT, result TEXT,
                start_x INT, end_x INT, hi REAL, lo REAL, hi_day INT, lo_day INT,
                duration INT, range_pct REAL, hi_change_pct REAL, lo_change_pct REAL,
                gain_pct REAL, norm_hi REAL, norm_lo REAL, norm_range_pct REAL,
                norm_duration REAL, norm_hi_change_pct REAL, norm_lo_change_pct REAL,
                norm_gain_pct REAL, is_completed INT, is_prediction INT
            );
            CREATE TABLE IF NOT EXISTS coin_prediction_paths (
                id INTEGER PRIMARY KEY, coin_id TEXT, symbol TEXT,
                cycle_number INT, scenario TEXT, start_x INT, end_x INT,
                day_x INT, value REAL
            );
            INSERT INTO coin_analysis_results VALUES
            ('btc-1','BTC',1,1,'Cy1',0,'BULL','DONE',1,50,120,90,25,45,50,33,0,0,33,0,0,0,0,0,0,0,1,0);
        """)
        conn.commit()

        df_all = pd.read_sql_query(
            "SELECT * FROM coin_analysis_results WHERE is_prediction=0", conn
        )
        df_all["is_bull"] = (df_all["phase"] == "BULL").astype(int)
        df_all["coin_rank"] = df_all["coin_rank"].fillna(999).astype(int)

        train_df = pd.DataFrame()
        models = {}
        bottom_models = {}
        peak_models = {}

        count = predict_and_insert(conn, df_all, train_df, models, bottom_models, peak_models)
        conn.close()
        assert isinstance(count, int)

    def test_returns_int(self, tmp_path):
        db_path = str(tmp_path / "test2.db")
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE coin_analysis_results (
                coin_id TEXT, symbol TEXT, coin_rank INT, cycle_number INT,
                cycle_name TEXT, box_index INT, phase TEXT, result TEXT,
                start_x INT, end_x INT, hi REAL, lo REAL, hi_day INT, lo_day INT,
                duration INT, range_pct REAL, hi_change_pct REAL, lo_change_pct REAL,
                gain_pct REAL, norm_hi REAL, norm_lo REAL, norm_range_pct REAL,
                norm_duration REAL, norm_hi_change_pct REAL, norm_lo_change_pct REAL,
                norm_gain_pct REAL, is_completed INT, is_prediction INT
            );
            CREATE TABLE IF NOT EXISTS coin_prediction_paths (
                id INTEGER PRIMARY KEY, coin_id TEXT, symbol TEXT,
                cycle_number INT, scenario TEXT, start_x INT, end_x INT,
                day_x INT, value REAL
            );
            INSERT INTO coin_analysis_results VALUES
            ('btc-1','BTC',1,1,'Cy1',0,'BULL','DONE',1,50,120,90,25,45,50,33,0,0,33,
             4.5,4.0,4.2,2.1,0.5,-0.3,0.2,1,0);
        """)
        conn.commit()
        df_all = load_box_df(conn)
        count = predict_and_insert(conn, df_all, pd.DataFrame(), {}, {}, {})
        conn.close()
        assert isinstance(count, int)
        assert count == 0  # no models => all skipped


# --- rebuild_prediction_paths ---
class TestRebuildPredictionPaths:
    def test_rebuild_on_empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_prediction_paths (
                id INTEGER PRIMARY KEY, coin_id TEXT, symbol TEXT,
                cycle_number INT, scenario TEXT, start_x INT, end_x INT,
                day_x INT, value REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_analysis_results (
                coin_id TEXT, symbol TEXT, cycle_number INT, phase TEXT,
                start_x INT, end_x INT, hi REAL, lo REAL, hi_day INT, lo_day INT,
                is_prediction INT
            )
        """)
        conn.commit()
        rebuild_prediction_paths(conn)
        rows = conn.execute("SELECT COUNT(*) FROM coin_prediction_paths").fetchone()[0]
        conn.close()
        assert rows == 0

    def test_rebuild_with_prediction_boxes(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_prediction_paths (
                id INTEGER PRIMARY KEY, coin_id TEXT, symbol TEXT,
                cycle_number INT, scenario TEXT, start_x INT, end_x INT,
                day_x INT, value REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_analysis_results (
                coin_id TEXT, symbol TEXT, cycle_number INT, phase TEXT,
                start_x INT, end_x INT, hi REAL, lo REAL, hi_day INT, lo_day INT,
                is_prediction INT
            )
        """)
        conn.execute("""
            INSERT INTO coin_analysis_results VALUES
            ('btc-1','BTC',1,'BULL',101,150,130,95,115,135,1)
        """)
        conn.commit()
        rebuild_prediction_paths(conn)
        rows = conn.execute("SELECT COUNT(*) FROM coin_prediction_paths").fetchone()[0]
        conn.close()
        assert rows >= 1


# --- print_prediction_summary (no crash) ---
class TestPrintPredictionSummary:
    def test_handles_empty_predictions(self, caplog):
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_analysis_results (
                symbol TEXT, coin_rank INT, cycle_name TEXT, phase TEXT,
                start_x INT, end_x INT, duration INT, hi REAL, lo REAL, range_pct REAL,
                is_prediction INT
            )
        """)
        conn.commit()
        print_prediction_summary(conn)
        conn.close()
        # Should not raise; may log warning
