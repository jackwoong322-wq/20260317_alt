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

def test_021_make_cycle_name_marks_current_cycle():
    module = load_script_module("021_altCycleAnalysisUsdt.py")

    assert (
        module.make_cycle_name(1735689600000, is_current=True) == "Current Cycle (2025)"
    )


def test_021_main_skips_short_history_without_saving(monkeypatch):
    module = load_script_module("021_altCycleAnalysisUsdt.py")

    short_df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "timestamp": [1, 2],
            "high": [10.0, 11.0],
            "low": [9.0, 10.0],
            "close": [9.5, 10.5],
        }
    )

    monkeypatch.setattr(module, "get_coins_supabase", lambda: [("bitcoin", "BTC")])
    monkeypatch.setattr(module, "process_incremental", lambda _coin_id: False)
    monkeypatch.setattr(module, "load_ohlcv_supabase", lambda _coin_id: short_df)
    monkeypatch.setattr(
        module,
        "save_cycle_data_supabase",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not save cycles")
        ),
    )
    monkeypatch.setattr(
        module,
        "save_summary_supabase",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not save summary")
        ),
    )
    monkeypatch.setattr(module, "print_summary_supabase", lambda: None)

    module.main()


class MockResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_021_upsert_rows_uses_coin_cycle_conflict_target(monkeypatch):
    module = load_script_module("021_altCycleAnalysisUsdt.py")
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return MockResponse({})

    monkeypatch.setattr(module.requests, "post", fake_post)
    module.upsert_rows_supabase(
        "alt_cycle_summary",
        [{"coin_id": "bitcoin", "cycle_number": 5}],
    )

    assert calls[0][1]["params"] == {"on_conflict": "coin_id,cycle_number"}


def test_021_process_incremental_uses_current_summary_without_peak_confirmation(
    monkeypatch,
):
    module = load_script_module("021_altCycleAnalysisUsdt.py")
    assert not hasattr(module, "check_if_peak_confirmed")

    summary = {
        "cycle_number": 5,
        "peak_date": "2025-10-06",
        "peak_price": 126200.0,
        "peak_pct_from_low": 250.0,
        "prev_peak_date": "2021-11-10",
        "prev_peak_price": 69000.0,
        "prev_low_date": "2022-11-21",
        "prev_low_price": 15500.0,
    }
    ohlcv = pd.DataFrame(
        [
            {
                "date": "2025-10-06",
                "timestamp": module.date_to_ms("2025-10-06"),
                "high": 126200.0,
                "low": 120000.0,
                "close": 123000.0,
            },
            {
                "date": "2025-10-07",
                "timestamp": module.date_to_ms("2025-10-07"),
                "high": 125000.0,
                "low": 119000.0,
                "close": 121000.0,
            },
        ]
    )
    saved = SimpleNamespace(data=False, summary=False)

    monkeypatch.setattr(module, "fetch_current_cycle_summary", lambda _coin_id: summary)
    monkeypatch.setattr(
        module, "load_ohlcv_supabase", lambda _coin_id, from_date=None: ohlcv
    )
    monkeypatch.setattr(
        module,
        "save_current_cycle_data",
        lambda *_args, **_kwargs: setattr(saved, "data", True),
    )
    monkeypatch.setattr(
        module,
        "save_current_cycle_summary",
        lambda *_args, **_kwargs: setattr(saved, "summary", True),
    )

    assert module.process_incremental("bitcoin") is True
    assert saved.data is True
    assert saved.summary is True
