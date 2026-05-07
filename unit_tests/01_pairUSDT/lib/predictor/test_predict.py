"""Tests for predictor modules with mock-based DB access."""

from unittest.mock import patch

import pandas as pd

from lib.predictor.predict_schema import CREATE_PATHS_SQL, CREATE_PEAKS_SQL
from lib.predictor.predict_btc_anchor import calc_btc_anchor
from lib.predictor.predict_features import build_feature_vector
from lib.predictor.predict_box_bull import build_bull_path_rows
from lib.predictor.predict_box_bear import build_bear_scenario
from lib.predictor.predict_judge import judge_bull_bear
from lib.predictor.data import build_training_pairs
from lib.predictor.predict_model import get_model_predictions
from lib.predictor.predict_box_bear_chain import run_bear_chain
from lib.common.config import (
    FEATURE_COLS,
    FEATURE_COLS_BTC_REG,
    TARGET_DUR,
    TARGET_HI,
    TARGET_LO,
    TARGET_PHASE,
)
from lib.predictor.predict import (
    _predict_one_coin_phase2,
    _resolve_prediction_anchor,
    predict_and_insert,
    predict_outputs,
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


class _RecordingRegressor:
    def __init__(self, value, feature_names_in_=None):
        self.value = value
        self.feature_names_in_ = feature_names_in_
        self.seen_columns = None

    def predict(self, X):
        self.seen_columns = list(X.columns)
        return [self.value]


class _RecordingClassifier:
    def __init__(self):
        self.seen_columns = None

    def predict_proba(self, X):
        self.seen_columns = list(X.columns)
        return [[0.4, 0.6]]


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

    def test_get_model_predictions_uses_model_feature_names_for_fallback_models(self):
        X_pred = pd.DataFrame([{col: 1.0 for col in FEATURE_COLS}])
        hi_model = _RecordingRegressor(0.1, feature_names_in_=FEATURE_COLS)
        group_models = {
            TARGET_HI: hi_model,
            TARGET_LO: _RecordingRegressor(-0.1, feature_names_in_=FEATURE_COLS),
            TARGET_DUR: _RecordingRegressor(1.0, feature_names_in_=FEATURE_COLS),
            TARGET_PHASE: _RecordingClassifier(),
        }

        get_model_predictions(
            group_models,
            X_pred,
            pd.Series({"hi": 120.0, "lo": 90.0}),
            reg_key="BTC_BEAR",
        )

        assert hi_model.seen_columns == FEATURE_COLS

    def test_get_model_predictions_keeps_btc_reg_columns_without_model_metadata(self):
        X_pred = pd.DataFrame([{col: 1.0 for col in FEATURE_COLS}])
        hi_model = _RecordingRegressor(0.1)
        del hi_model.feature_names_in_
        lo_model = _RecordingRegressor(-0.1)
        del lo_model.feature_names_in_
        dur_model = _RecordingRegressor(1.0)
        del dur_model.feature_names_in_
        group_models = {
            TARGET_HI: hi_model,
            TARGET_LO: lo_model,
            TARGET_DUR: dur_model,
            TARGET_PHASE: _RecordingClassifier(),
        }

        get_model_predictions(
            group_models,
            X_pred,
            pd.Series({"hi": 120.0, "lo": 90.0}),
            reg_key="BTC_BEAR",
        )

        assert hi_model.seen_columns == FEATURE_COLS_BTC_REG


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

    def test_predict_outputs_uses_named_current_cycle_not_numeric_max(self):
        conn = _FakeConn()
        df_all = pd.DataFrame(
            [
                {
                    "coin_id": "btc-1",
                    "cycle_number": 3,
                    "cycle_name": "Current Cycle (2025)",
                    "box_index": 0,
                    "is_completed": 0,
                    "is_prediction": 0,
                    "phase": "BULL",
                    "symbol": "BTC",
                    "end_x": 50,
                    "hi": 120.0,
                    "lo": 90.0,
                    "coin_rank": 1,
                },
                {
                    "coin_id": "btc-1",
                    "cycle_number": 9,
                    "cycle_name": "Cycle 2099",
                    "box_index": 0,
                    "is_completed": 1,
                    "is_prediction": 0,
                    "phase": "BEAR",
                    "symbol": "BTC",
                    "end_x": 60,
                    "hi": 100.0,
                    "lo": 80.0,
                    "coin_rank": 1,
                },
            ]
        )
        seen_cycles = []

        def _fake_predict_one_coin(_conn, _coin_id, max_cyc, *_args, **_kwargs):
            seen_cycles.append(max_cyc)
            return [], [], [], True

        with patch(
            "lib.predictor.predict.build_cycle_and_coin_stats",
            return_value=({}, {}, {}, {}),
        ), patch("lib.predictor.predict.calc_btc_anchor", return_value=None), patch(
            "lib.predictor.predict.compute_cross_coin_peak_ratio", return_value=None
        ), patch("lib.predictor.predict._predict_one_coin", _fake_predict_one_coin):
            predict_outputs(conn, df_all, pd.DataFrame(), {}, {}, {})

        assert seen_cycles == [3]

    def test_predict_outputs_uses_active_box_as_last(self):
        conn = _FakeConn()
        df_all = pd.DataFrame(
            [
                {
                    "coin_id": "btc-1",
                    "cycle_number": 5,
                    "cycle_name": "Current Cycle (2025)",
                    "box_index": 0,
                    "is_completed": 1,
                    "is_prediction": 0,
                    "phase": "BEAR",
                    "symbol": "BTC",
                    "end_x": 40,
                    "hi": 120.0,
                    "lo": 80.0,
                    "coin_rank": 1,
                },
                {
                    "coin_id": "btc-1",
                    "cycle_number": 5,
                    "cycle_name": "Current Cycle (2025)",
                    "box_index": 1,
                    "is_completed": 0,
                    "is_prediction": 0,
                    "phase": "BEAR",
                    "symbol": "BTC",
                    "start_x": 41,
                    "end_x": 80,
                    "hi": 100.0,
                    "lo": 70.0,
                    "coin_rank": 1,
                },
            ]
        )
        seen_last_box = []

        def _fake_predict_one_coin(_conn, _coin_id, _max_cyc, _grp, last, *_args, **_kwargs):
            seen_last_box.append(int(last["box_index"]))
            return [], [], [], True

        with patch(
            "lib.predictor.predict.build_cycle_and_coin_stats",
            return_value=({}, {}, {}, {}),
        ), patch("lib.predictor.predict.calc_btc_anchor", return_value=None), patch(
            "lib.predictor.predict.compute_cross_coin_peak_ratio", return_value=None
        ), patch("lib.predictor.predict._predict_one_coin", _fake_predict_one_coin):
            predict_outputs(conn, df_all, pd.DataFrame(), {}, {}, {})

        assert seen_last_box == [1]

    def test_prediction_anchor_uses_active_box_index_and_start(self):
        grp = pd.DataFrame(
            [
                {"box_index": 0, "is_prediction": 0, "is_completed": 1, "end_x": 40},
                {
                    "box_index": 3,
                    "is_prediction": 0,
                    "is_completed": 0,
                    "start_x": 120,
                    "end_x": 150,
                },
            ]
        )
        anchor = _resolve_prediction_anchor(grp, grp.iloc[-1])

        assert anchor["has_active_box"] is True
        assert anchor["prediction_box_idx"] == 3
        assert anchor["prediction_start_x"] == 120

    def test_prediction_anchor_completed_box_uses_next_index_and_day(self):
        grp = pd.DataFrame(
            [
                {"box_index": 2, "is_prediction": 0, "is_completed": 1, "end_x": 80},
                {"box_index": 3, "is_prediction": 0, "is_completed": 1, "end_x": 150},
            ]
        )
        anchor = _resolve_prediction_anchor(grp, grp.iloc[-1])

        assert anchor["has_active_box"] is False
        assert anchor["prediction_box_idx"] == 4
        assert anchor["prediction_start_x"] == 151

    def test_phase2_does_not_update_observed_active_row(self):
        conn = _FakeConn()
        active = pd.Series(
            {
                "coin_id": "btc-1",
                "symbol": "BTC",
                "coin_rank": 1,
                "cycle_name": "Current Cycle (2025)",
                "cycle_number": 5,
                "box_index": 1,
                "phase": "BULL",
                "is_completed": 0,
                "start_x": 41,
                "end_x": 80,
                "hi": 120.0,
                "lo": 90.0,
                "hi_day": 60,
                "lo_day": 75,
            }
        )
        bundle = {
            "last": active,
            "coin_id": "btc-1",
            "max_cyc": 5,
            "feat": {},
            "pred_hi_bull": 150.0,
            "pred_lo_bull": 95.0,
            "pred_dur_bull": 30,
            "pred_is_bull": True,
            "bottom_lo": None,
            "bottom_day": None,
            "start_x": 41,
            "next_box_idx": 1,
            "ref_lo": 90.0,
            "cycle_lo": 70.0,
            "btc_anchor": None,
            "has_active_box": True,
            "grp": pd.DataFrame([active.to_dict()]),
            "train_df": pd.DataFrame(),
            "X_pred": pd.DataFrame(),
        }
        bull_row = (
            "btc-1", "BTC", 1, 5, "Current Cycle (2025)", 1, "BULL",
            "PRED_BULL_CHAIN", 41, 100, 150.0, 95.0, 50, 80, 60,
            57.8, 66.7, -36.7, 50.0, 0, 0, 0, 0, 0, 0, 0, 0, 1, None, None
        )

        with patch("lib.predictor.predict.build_bull_scenario", return_value=(bull_row, [], {})), patch(
            "lib.predictor.predict.find_most_similar_pattern",
            return_value=("-", 0, 0, 0.0),
        ):
            _predict_one_coin_phase2(conn, bundle)

        update_sql = [sql for sql, _params in conn.executed if "UPDATE coin_analysis_results" in sql]
        assert update_sql == []
        assert bundle["pred_rows"][0][5] == 1
        assert bundle["pred_rows"][0][7] == "PRED_BULL_ACTIVE"
        assert bundle["pred_rows"][0][8] == 41
        assert bundle["pred_rows"][0][9] >= 80
        assert min(row[6] for row in bundle["path_rows"]) == 41
        assert max(row[6] for row in bundle["path_rows"]) >= 80

    def test_phase2_active_bear_prediction_replaces_placeholder_bull_row(self):
        conn = _FakeConn()
        active = pd.Series(
            {
                "coin_id": "btc-1",
                "symbol": "BTC",
                "coin_rank": 1,
                "cycle_name": "Current Cycle (2025)",
                "cycle_number": 5,
                "box_index": 1,
                "phase": "BEAR",
                "is_completed": 0,
                "start_x": 41,
                "end_x": 80,
                "hi": 120.0,
                "lo": 90.0,
                "hi_day": 60,
                "lo_day": 75,
            }
        )
        bundle = {
            "last": active,
            "coin_id": "btc-1",
            "max_cyc": 5,
            "feat": {},
            "pred_hi_bull": 150.0,
            "pred_lo_bull": 95.0,
            "pred_dur_bull": 30,
            "pred_is_bull": False,
            "bottom_lo": 80.0,
            "bottom_day": 110,
            "start_x": 41,
            "next_box_idx": 1,
            "ref_lo": 90.0,
            "cycle_lo": 70.0,
            "btc_anchor": None,
            "has_active_box": True,
            "grp": pd.DataFrame([active.to_dict()]),
            "df_all": pd.DataFrame(
                columns=[
                    "symbol",
                    "cycle_name",
                    "phase",
                    "is_completed",
                    "box_index",
                    "range_pct",
                    "hi",
                    "lo",
                ]
            ),
            "train_df": pd.DataFrame(),
            "X_pred": pd.DataFrame(),
            "avg_cycle_days": 120,
            "models": {},
            "group_key": "BTC",
            "cycle_prediction": None,
            "peak_hi": 180.0,
            "peak_day_pred": 150,
        }
        bull_placeholder = (
            "btc-1", "BTC", 1, 5, "Current Cycle (2025)", 1, "BULL",
            "PRED_BULL_CHAIN", 41, 100, 150.0, 95.0, 50, 80, 60,
            57.8, 66.7, -36.7, 50.0, 0, 0, 0, 0, 0, 0, 0, 0, 1, None, None
        )
        bear_row = (
            "btc-1", "BTC", 1, 5, "Current Cycle (2025)", 1, "BEAR",
            "PRED_BEAR_CHAIN", 41, 110, 120.0, 80.0, 60, 110, 70,
            50.0, 33.3, 0.0, -33.3, 0, 0, 0, 0, 0, 0, 0, 0, 1, None, None
        )
        bear_path = [
            ("btc-1", "BTC", 5, "bear", 41, 110, 110, 80.0),
        ]

        with patch(
            "lib.predictor.predict.build_bull_scenario",
            return_value=(bull_placeholder, [], {}),
        ), patch(
            "lib.predictor.predict.build_bear_chain",
            return_value=([bear_row], bear_path),
        ), patch(
            "lib.predictor.predict.build_bull_chain",
            return_value=([], []),
        ), patch(
            "lib.predictor.predict.find_most_similar_pattern",
            return_value=("-", 0, 0, 0.0),
        ):
            _predict_one_coin_phase2(conn, bundle)

        assert [row[7] for row in bundle["pred_rows"]] == ["PRED_BEAR_ACTIVE"]
        assert bundle["pred_rows"][0][5] == 1
        assert bundle["pred_rows"][0][8] == 41

    def test_phase2_active_bear_chain_uses_active_end_as_floor(self):
        conn = _FakeConn()
        active = pd.Series(
            {
                "coin_id": "btc-1",
                "symbol": "BTC",
                "coin_rank": 1,
                "cycle_name": "Current Cycle (2025)",
                "cycle_number": 5,
                "box_index": 1,
                "phase": "BEAR",
                "is_completed": 0,
                "start_x": 41,
                "end_x": 80,
                "hi": 120.0,
                "lo": 90.0,
                "hi_day": 60,
                "lo_day": 75,
            }
        )
        bundle = {
            "last": active,
            "coin_id": "btc-1",
            "max_cyc": 5,
            "feat": {},
            "pred_hi_bull": 150.0,
            "pred_lo_bull": 95.0,
            "pred_dur_bull": 30,
            "pred_is_bull": False,
            "bottom_lo": 80.0,
            "bottom_day": 70,
            "start_x": 41,
            "next_box_idx": 1,
            "ref_lo": 90.0,
            "cycle_lo": 70.0,
            "btc_anchor": None,
            "has_active_box": True,
            "grp": pd.DataFrame([active.to_dict()]),
            "df_all": pd.DataFrame(
                columns=[
                    "symbol",
                    "cycle_name",
                    "phase",
                    "is_completed",
                    "box_index",
                    "range_pct",
                    "hi",
                    "lo",
                ]
            ),
            "train_df": pd.DataFrame(),
            "X_pred": pd.DataFrame(),
            "avg_cycle_days": 120,
            "models": {},
            "group_key": "BTC",
            "cycle_prediction": None,
            "peak_hi": None,
            "peak_day_pred": None,
        }
        bull_placeholder = (
            "btc-1", "BTC", 1, 5, "Current Cycle (2025)", 1, "BULL",
            "PRED_BULL_CHAIN", 41, 100, 150.0, 95.0, 50, 80, 60,
            57.8, 66.7, -36.7, 50.0, 0, 0, 0, 0, 0, 0, 0, 0, 1, None, None
        )
        bear_row = (
            "btc-1", "BTC", 1, 5, "Current Cycle (2025)", 1, "BEAR",
            "PRED_BEAR_CHAIN", 41, 80, 120.0, 80.0, 80, 80, 40,
            50.0, 33.3, 0.0, -33.3, 0, 0, 0, 0, 0, 0, 0, 0, 1, None, None
        )
        seen_kwargs = {}

        def _fake_build_bear_chain(**kwargs):
            seen_kwargs.update(kwargs)
            return [bear_row], [("btc-1", "BTC", 5, "bear", 41, 80, 80, 80.0)]

        with patch(
            "lib.predictor.predict.build_bull_scenario",
            return_value=(bull_placeholder, [], {}),
        ), patch(
            "lib.predictor.predict.build_bear_chain",
            side_effect=_fake_build_bear_chain,
        ), patch(
            "lib.predictor.predict.find_most_similar_pattern",
            return_value=("-", 0, 0, 0.0),
        ):
            _predict_one_coin_phase2(conn, bundle)

        assert seen_kwargs["box_start_x"] == 41
        assert seen_kwargs["cur_day"] == 75
        assert seen_kwargs["bottom_day"] == 80
        assert seen_kwargs["today_day"] == 80

    def test_run_bear_chain_keeps_active_completion_and_next_start_after_today(self):
        last = pd.Series(
            {
                "symbol": "BTC",
                "coin_rank": 1,
                "cycle_name": "Current Cycle (2025)",
                "hi": 120.0,
                "lo": 90.0,
            }
        )

        rows, path_rows = run_bear_chain(
            coin_id="btc-1",
            last=last,
            max_cyc=5,
            next_box_idx=1,
            bear_chain_day=80,
            bear_chain_val=90.0,
            bear_feat={},
            prev_box_hi=120.0,
            prev_box_lo=90.0,
            bottom_day=140,
            bottom_lo=70.0,
            group_models={},
            avg_cycle_days=120,
            override_start_x=41,
            override_start_x_value=90.0,
            max_bear_chain=3,
            today_day=100,
        )

        assert rows[0][8] == 41
        assert rows[0][9] == 100
        assert rows[1][8] == 101
        first_box_points = [row for row in path_rows if row[4] == rows[0][8] and row[5] == rows[0][9]]
        future_points = [row for row in path_rows if row[4] > rows[0][9]]
        assert min(row[6] for row in first_box_points) == 41
        assert max(row[6] for row in first_box_points) == 100
        assert min(row[6] for row in future_points) == 101

    def test_build_training_pairs_excludes_active_target_labels(self):
        df = pd.DataFrame(
            [
                {
                    "coin_id": "btc-1",
                    "cycle_number": 5,
                    "box_index": 0,
                    "is_completed": 1,
                    "is_bull": 0,
                    "symbol": "BTC",
                    "phase": "BEAR",
                    "hi": 120.0,
                    "lo": 80.0,
                    "end_x": 40,
                    "norm_range_pct": 1.0,
                    "norm_hi_change_pct": 1.0,
                    "norm_lo_change_pct": -1.0,
                    "norm_gain_pct": -1.0,
                    "norm_duration": 1.0,
                    "coin_rank": 1,
                    "cycle_name": "Current Cycle (2025)",
                },
                {
                    "coin_id": "btc-1",
                    "cycle_number": 5,
                    "box_index": 1,
                    "is_completed": 0,
                    "is_bull": 0,
                    "symbol": "BTC",
                    "phase": "BEAR",
                    "hi": 100.0,
                    "lo": 70.0,
                    "end_x": 80,
                    "norm_range_pct": 1.0,
                    "norm_hi_change_pct": 1.0,
                    "norm_lo_change_pct": -1.0,
                    "norm_gain_pct": -1.0,
                    "norm_duration": 1.0,
                    "coin_rank": 1,
                    "cycle_name": "Current Cycle (2025)",
                },
            ]
        )
        with patch(
            "lib.predictor.data.build_cycle_and_coin_stats",
            return_value=(
                {("btc-1", 5): {"total_days": 80, "low_x": 75, "min_lo": 70.0}},
                {"btc-1": {"avg_cycle_days": 80, "mean_lo": 75.0, "min_lo": 70.0}},
                {("btc-1", "BEAR"): 2.0},
                {5: 120.0},
            ),
        ):
            result = build_training_pairs(df)

        assert result.empty

    def test_build_bear_scenario_uses_provided_box_index(self):
        last = pd.Series(
            {
                "symbol": "BTC",
                "coin_rank": 1,
                "cycle_name": "Current Cycle (2025)",
            }
        )
        row, _meta, _bottom_lo, _bottom_day = build_bear_scenario(
            "btc-1",
            last,
            max_cyc=5,
            next_box_idx=7,
            start_x=100,
            ref_hi=120.0,
            bottom_lo=80.0,
            bottom_day=130,
        )

        assert row[5] == 7

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
