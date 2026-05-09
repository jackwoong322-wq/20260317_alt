import importlib.util
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


PAIRUSDT_ROOT = Path(__file__).resolve().parents[2] / "01_pairUSDT"


def load_script_module(script_name: str):
    module_name = f"test_{script_name.replace('.', '_')}_{uuid.uuid4().hex}"
    script_path = PAIRUSDT_ROOT / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def test_032_normalize_rows_replaces_non_finite_values():
    module = load_script_module("032_train_and_predict_box.py")

    rows = module._normalize_rows(
        [
            {"a": 1.0, "b": float("inf"), "c": float("nan")},
        ]
    )

    assert rows == [{"a": 1.0, "b": None, "c": None}]


def test_032_main_skips_publish_when_no_training_data(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    reset_calls = []
    sync_calls = []
    refresh_calls = []
    fake_conn = SimpleNamespace(close=lambda: None)

    monkeypatch.setitem(
        sys.modules, "duckdb", SimpleNamespace(connect=lambda database: fake_conn)
    )
    monkeypatch.setattr(
        module, "reset_predictions_supabase", lambda: reset_calls.append(True)
    )
    monkeypatch.setattr(module, "setup_stage_db_for_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "hydrate_stage_db_from_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "load_box_df", lambda _conn: pd.DataFrame())
    monkeypatch.setattr(
        module,
        "sync_predictions_to_supabase_and_refresh",
        lambda _conn: (sync_calls.append(True), refresh_calls.append(True)),
    )

    module.main()

    assert reset_calls == []
    assert sync_calls == []
    assert refresh_calls == []


def test_032_sync_refresh_helper_does_not_refresh_when_save_fails(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    refresh_calls = []

    def fail_sync(*_args, **_kwargs):
        raise RuntimeError("save failed")

    monkeypatch.setattr(module, "sync_predictions_to_supabase", fail_sync)
    monkeypatch.setattr(
        module, "refresh_dashboard_cache_after_save", lambda: refresh_calls.append(True)
    )

    try:
        module.sync_predictions_to_supabase_and_refresh([], [], [])
    except RuntimeError as exc:
        assert str(exc) == "save failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert refresh_calls == []


def _valid_prediction_tuple():
    return (
        "bitcoin",
        "BTC",
        1,
        5,
        "Current Cycle (2025)",
        2,
        "BEAR",
        "PRED_BEAR_ACTIVE",
        100,
        120,
        75.0,
        60.0,
        105,
        120,
        21,
        25.0,
        5.0,
        -10.0,
        0.0,
        75.0,
        60.0,
        25.0,
        21.0,
        5.0,
        -10.0,
        0.0,
        0,
        1,
        5,
        15,
    )


def _valid_path_tuple():
    return ("bitcoin", "BTC", 5, "bear", 100, 120, 110, 65.0)


def _valid_peak_tuple():
    return ("bitcoin", "BTC", 1, 5, "Current Cycle (2025)", "BOTTOM", 60.0, 120)


def _observed_active_df():
    return pd.DataFrame(
        [
            {
                "coin_id": "bitcoin",
                "symbol": "BTC",
                "cycle_number": 5,
                "box_index": 2,
                "start_x": 100,
                "end_x": 115,
                "hi": 72.0,
                "lo": 61.0,
                "is_completed": 0,
                "is_prediction": 0,
            }
        ]
    )


def test_032_sync_validates_before_reset_insert_and_refresh(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    calls = []

    monkeypatch.setattr(module, "reset_predictions_supabase", lambda: calls.append("reset"))
    monkeypatch.setattr(
        module,
        "_post_rows_supabase",
        lambda table, rows: calls.append(("post", table, len(rows))),
    )
    monkeypatch.setattr(
        module,
        "refresh_dashboard_cache_after_save",
        lambda: calls.append("refresh"),
    )

    result = module.sync_predictions_to_supabase_and_refresh(
        [_valid_prediction_tuple()],
        [_valid_path_tuple()],
        [_valid_peak_tuple()],
        _observed_active_df(),
    )

    assert result[0]["result"] == "PRED_BEAR_ACTIVE"
    assert calls == [
        "reset",
        ("post", "coin_analysis_results", 1),
        ("post", "coin_prediction_paths", 1),
        ("post", "coin_prediction_peaks", 1),
        "refresh",
    ]


def test_032_validation_failure_blocks_reset_insert_and_refresh(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    calls = []
    bad = list(_valid_prediction_tuple())
    bad[10] = 50.0
    bad[11] = 60.0

    monkeypatch.setattr(module, "reset_predictions_supabase", lambda: calls.append("reset"))
    monkeypatch.setattr(module, "_post_rows_supabase", lambda *args, **kwargs: calls.append("post"))
    monkeypatch.setattr(
        module,
        "refresh_dashboard_cache_after_save",
        lambda: calls.append("refresh"),
    )

    try:
        module.sync_predictions_to_supabase_and_refresh(
            [tuple(bad)],
            [_valid_path_tuple()],
            [_valid_peak_tuple()],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "hi must be >= lo" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")

    assert calls == []


def test_032_sync_skips_publish_when_prediction_rows_empty(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    calls = []

    monkeypatch.setattr(module, "reset_predictions_supabase", lambda: calls.append("reset"))
    monkeypatch.setattr(module, "_post_rows_supabase", lambda *args, **kwargs: calls.append("post"))
    monkeypatch.setattr(
        module,
        "refresh_dashboard_cache_after_save",
        lambda: calls.append("refresh"),
    )

    result = module.sync_predictions_to_supabase_and_refresh(
        [],
        [_valid_path_tuple()],
        [_valid_peak_tuple()],
        _observed_active_df(),
    )

    assert result == []
    assert calls == []


def test_032_active_prediction_must_match_observed_active_box():
    module = load_script_module("032_train_and_predict_box.py")
    bad = list(_valid_prediction_tuple())
    bad[8] = 101

    try:
        module.sync_predictions_to_supabase(
            [tuple(bad)],
            [_valid_path_tuple()],
            [_valid_peak_tuple()],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "active prediction start_x" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_missing_active_completion_prediction():
    module = load_script_module("032_train_and_predict_box.py")
    future = list(_valid_prediction_tuple())
    future[5] = 3
    future[7] = "PRED_BEAR_CHAIN"
    future[8] = 121
    future[9] = 140
    future[12] = 125
    future[13] = 140
    future[14] = 20
    future_path = ("bitcoin", "BTC", 5, "bear", 121, 140, 130, 58.0)
    future_peak = ("bitcoin", "BTC", 1, 5, "Current Cycle (2025)", "BOTTOM", 55.0, 140)

    try:
        module.sync_predictions_to_supabase(
            [tuple(future)],
            [future_path],
            [future_peak],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "missing active completion prediction" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_active_box_with_chain_result():
    module = load_script_module("032_train_and_predict_box.py")
    bad = list(_valid_prediction_tuple())
    bad[7] = "PRED_BEAR_CHAIN"

    try:
        module.sync_predictions_to_supabase(
            [tuple(bad)],
            [_valid_path_tuple()],
            [_valid_peak_tuple()],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "must use PRED_BEAR_ACTIVE/PRED_BULL_ACTIVE" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_non_finite_values():
    module = load_script_module("032_train_and_predict_box.py")
    bad_pred = list(_valid_prediction_tuple())
    bad_pred[10] = float("inf")

    try:
        module.sync_predictions_to_supabase(
            [tuple(bad_pred)],
            [_valid_path_tuple()],
            [_valid_peak_tuple()],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "hi must be >= lo" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_invalid_path_range():
    module = load_script_module("032_train_and_predict_box.py")
    bad_path = ("bitcoin", "BTC", 5, "bear", 130, 120, 125, 65.0)

    try:
        module.sync_predictions_to_supabase(
            [_valid_prediction_tuple()],
            [bad_path],
            [_valid_peak_tuple()],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "invalid start_x/end_x" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_unmatched_path_scenario():
    module = load_script_module("032_train_and_predict_box.py")
    bad_path = ("bitcoin", "BTC", 5, "bull", 100, 120, 110, 65.0)

    try:
        module.sync_predictions_to_supabase(
            [_valid_prediction_tuple()],
            [bad_path],
            [_valid_peak_tuple()],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "no matching prediction scenario" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_missing_peak_day():
    module = load_script_module("032_train_and_predict_box.py")
    bad_peak = list(_valid_peak_tuple())
    bad_peak[7] = None

    try:
        module.sync_predictions_to_supabase(
            [_valid_prediction_tuple()],
            [_valid_path_tuple()],
            [tuple(bad_peak)],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "predicted_day is required" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_validation_rejects_invalid_peak_type():
    module = load_script_module("032_train_and_predict_box.py")
    bad_peak = list(_valid_peak_tuple())
    bad_peak[5] = "TOP"

    try:
        module.sync_predictions_to_supabase(
            [_valid_prediction_tuple()],
            [_valid_path_tuple()],
            [tuple(bad_peak)],
            _observed_active_df(),
        )
    except module.PredictionValidationError as exc:
        assert "invalid peak_type" in str(exc)
    else:
        raise AssertionError("expected PredictionValidationError")


def test_032_main_builds_training_pairs_from_completed_observed_rows(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    fake_conn = SimpleNamespace(
        close=lambda: None,
        execute=lambda *_args, **_kwargs: fake_conn,
        commit=lambda: None,
    )
    received = []
    events = []
    df = pd.DataFrame(
        [
            {"coin_id": "bitcoin", "symbol": "BTC", "cycle_number": 4, "box_index": 0, "is_prediction": 0, "is_completed": 1},
            {"coin_id": "bitcoin", "symbol": "BTC", "cycle_number": 5, "box_index": 1, "is_prediction": 0, "is_completed": 0},
        ]
    )
    train_df = pd.DataFrame(
        [
            {
                "meta_symbol": "BTC",
                "meta_cycle_name": "Cycle 2021",
                module.TARGET_PHASE: 0,
            }
        ]
    )

    monkeypatch.setitem(
        sys.modules, "duckdb", SimpleNamespace(connect=lambda database: fake_conn)
    )
    monkeypatch.setattr(module, "setup_stage_db_for_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "hydrate_stage_db_from_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "load_box_df", lambda _conn: df)

    def fake_build_training_pairs(input_df):
        received.append(input_df.copy())
        return train_df

    monkeypatch.setattr(module, "build_training_pairs", fake_build_training_pairs)
    monkeypatch.setattr(module, "build_bottom_dataset", lambda _df: pd.DataFrame())
    monkeypatch.setattr(module, "train_box_models", lambda _df: ({}, {}))
    monkeypatch.setattr(module, "train_box_reg_group", lambda *_args, **_kwargs: (None, None))
    monkeypatch.setattr(module, "train_bottom_models", lambda _df: {})
    monkeypatch.setattr(module, "print_feature_importance", lambda _models: None)
    monkeypatch.setattr(module, "predict_outputs", lambda *_args: ([], [], [], 0, 0))
    monkeypatch.setattr(
        module,
        "sync_predictions_to_supabase_and_refresh",
        lambda *args, **kwargs: events.append("sync"),
    )

    module.main()

    assert len(received) == 1
    assert received[0]["is_completed"].tolist() == [1]
    assert received[0]["is_prediction"].tolist() == [0]
    assert events == []


def test_032_main_skips_publish_when_predict_outputs_empty(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    fake_conn = SimpleNamespace(
        close=lambda: None,
        execute=lambda *_args, **_kwargs: fake_conn,
        commit=lambda: None,
    )
    events = []
    df = pd.DataFrame(
        [
            {
                "coin_id": "bitcoin",
                "symbol": "BTC",
                "cycle_number": 4,
                "box_index": 0,
                "is_prediction": 0,
                "is_completed": 1,
            }
        ]
    )
    train_df = pd.DataFrame(
        [
            {
                "meta_symbol": "BTC",
                "meta_cycle_name": "Cycle 2021",
                module.TARGET_PHASE: 0,
            }
        ]
    )

    monkeypatch.setitem(
        sys.modules, "duckdb", SimpleNamespace(connect=lambda database: fake_conn)
    )
    monkeypatch.setattr(module, "setup_stage_db_for_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "hydrate_stage_db_from_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "load_box_df", lambda _conn: df)
    monkeypatch.setattr(module, "build_training_pairs", lambda _df: train_df)
    monkeypatch.setattr(module, "build_bottom_dataset", lambda _df: pd.DataFrame())
    monkeypatch.setattr(module, "train_box_models", lambda _df: ({}, {}))
    monkeypatch.setattr(module, "train_box_reg_group", lambda *_args, **_kwargs: (None, None))
    monkeypatch.setattr(module, "train_bottom_models", lambda _df: {})
    monkeypatch.setattr(module, "print_feature_importance", lambda _models: None)
    monkeypatch.setattr(module, "predict_outputs", lambda *_args: ([], [], [], 0, 0))
    monkeypatch.setattr(
        module,
        "sync_predictions_to_supabase_and_refresh",
        lambda *args, **kwargs: events.append("sync"),
    )

    module.main()

    assert events == []


def test_032_refresh_dashboard_cache_skips_when_env_missing(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    post_calls = []

    monkeypatch.delenv(module.DASHBOARD_CACHE_REFRESH_URL_ENV, raising=False)
    monkeypatch.delenv(module.DASHBOARD_CACHE_REFRESH_SECRET_ENV, raising=False)
    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: post_calls.append((args, kwargs)))

    assert module.refresh_dashboard_cache_after_save() is False
    assert post_calls == []


def test_032_refresh_dashboard_cache_posts_internal_secret(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    calls = []

    class FakePostResponse:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {
                "ok": True,
                "data_version": "snapshot-test",
                "cache_status": "refreshed",
            }

    def fake_post(url, headers, timeout):
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        return FakePostResponse()

    monkeypatch.setenv(
        module.DASHBOARD_CACHE_REFRESH_URL_ENV,
        "https://example.test/api/internal/dashboard-cache/refresh",
    )
    monkeypatch.setenv(module.DASHBOARD_CACHE_REFRESH_SECRET_ENV, "secret")
    monkeypatch.setattr(module.requests, "post", fake_post)

    assert module.refresh_dashboard_cache_after_save() is True
    assert calls == [
        {
            "url": "https://example.test/api/internal/dashboard-cache/refresh",
            "headers": {"X-Internal-Secret": "secret"},
            "timeout": 60,
        }
    ]


def test_032_refresh_dashboard_cache_returns_false_for_http_failure(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")

    class FakePostResponse:
        ok = False
        status_code = 500
        text = "server error"

    monkeypatch.setenv(
        module.DASHBOARD_CACHE_REFRESH_URL_ENV,
        "https://example.test/api/internal/dashboard-cache/refresh",
    )
    monkeypatch.setenv(module.DASHBOARD_CACHE_REFRESH_SECRET_ENV, "secret")
    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: FakePostResponse())

    assert module.refresh_dashboard_cache_after_save() is False


def test_032_refresh_dashboard_cache_returns_false_for_backend_failure(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")

    class FakePostResponse:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"ok": False, "error": "refresh failed"}

    monkeypatch.setenv(
        module.DASHBOARD_CACHE_REFRESH_URL_ENV,
        "https://example.test/api/internal/dashboard-cache/refresh",
    )
    monkeypatch.setenv(module.DASHBOARD_CACHE_REFRESH_SECRET_ENV, "secret")
    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: FakePostResponse())

    assert module.refresh_dashboard_cache_after_save() is False


def test_032_refresh_dashboard_cache_returns_false_for_request_exception(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")

    def fail_post(*_args, **_kwargs):
        raise RuntimeError("network failed")

    monkeypatch.setenv(
        module.DASHBOARD_CACHE_REFRESH_URL_ENV,
        "https://example.test/api/internal/dashboard-cache/refresh",
    )
    monkeypatch.setenv(module.DASHBOARD_CACHE_REFRESH_SECRET_ENV, "secret")
    monkeypatch.setattr(module.requests, "post", fail_post)

    assert module.refresh_dashboard_cache_after_save() is False
