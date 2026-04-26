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


def test_032_main_syncs_empty_predictions_without_training(monkeypatch):
    module = load_script_module("032_train_and_predict_box.py")
    sync_calls = []
    fake_conn = SimpleNamespace(close=lambda: None)

    monkeypatch.setitem(
        sys.modules, "duckdb", SimpleNamespace(connect=lambda database: fake_conn)
    )
    monkeypatch.setattr(module, "setup_stage_db_for_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "hydrate_stage_db_from_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "load_box_df", lambda _conn: pd.DataFrame())
    monkeypatch.setattr(
        module, "sync_predictions_to_supabase", lambda _conn: sync_calls.append(True)
    )

    module.main()

    assert sync_calls == [True]
