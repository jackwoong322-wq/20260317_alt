import importlib.util
import sys
import uuid
from pathlib import Path

import pandas as pd


PAIRUSDT_ROOT = Path(__file__).resolve().parents[1]


def load_script_module(script_name: str):
    module_name = f"test_{script_name.replace('.', '_')}_{uuid.uuid4().hex}"
    script_path = PAIRUSDT_ROOT / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_011_build_coin_list_preserves_market_cap_order():
    module = load_script_module("011_cryptoCollectorUsdt.py")

    cg_coins = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1},
        {"id": "solana", "symbol": "sol", "name": "Solana", "market_cap_rank": 5},
        {"id": "dogecoin", "symbol": "doge", "name": "Dogecoin", "market_cap_rank": 8},
    ]

    result = module.build_coin_list(cg_coins, {"DOGE", "BTC"}, top_n=2)

    assert [coin["id"] for coin in result] == ["bitcoin", "dogecoin"]
    assert [coin["rank"] for coin in result] == [1, 8]


def test_011_main_returns_cleanly_when_no_target_coins(monkeypatch):
    module = load_script_module("011_cryptoCollectorUsdt.py")

    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(module, "cg_fetch_top_coins", lambda _limit: [{"id": "btc"}])
    monkeypatch.setattr(module, "binance_fetch_usdt_symbols", lambda: {"BTC"})
    monkeypatch.setattr(module, "build_coin_list", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        module,
        "save_coin_supabase",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not save")
        ),
    )

    module.main()


def test_012_next_date_advances_by_one_day():
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")

    assert module.next_date("2026-03-31") == "2026-04-01"


def test_012_main_returns_when_coin_table_is_empty(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")

    monkeypatch.setattr(module, "today_utc", lambda: "2026-04-01")
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(module, "get_coins_from_supabase", lambda _sb: [])
    monkeypatch.setattr(
        module,
        "binance_fetch_klines",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not fetch")
        ),
    )

    module.main()


def test_012_main_skips_already_up_to_date_coin(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")

    monkeypatch.setattr(module, "today_utc", lambda: "2026-04-01")
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(
        module,
        "get_coins_from_supabase",
        lambda _sb: [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "rank": 1}],
    )
    monkeypatch.setattr(module, "get_last_date_supabase", lambda *_args: "2026-04-01")
    monkeypatch.setattr(
        module,
        "binance_fetch_klines",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not fetch")
        ),
    )

    module.main()


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


def test_031_main_returns_when_no_cycle_data(monkeypatch):
    module = load_script_module("031_box_analyzer_to_supabase.py")

    monkeypatch.setattr(module, "load_all_coins_and_cycles", lambda: ([], {}))
    monkeypatch.setattr(
        module,
        "sync_results_to_supabase",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not sync")
        ),
    )

    module.main()


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

    monkeypatch.setattr(module, "setup_stage_db_for_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "hydrate_stage_db_from_supabase", lambda _conn: None)
    monkeypatch.setattr(module, "load_box_df", lambda _conn: pd.DataFrame())
    monkeypatch.setattr(
        module, "sync_predictions_to_supabase", lambda _conn: sync_calls.append(True)
    )

    module.main()

    assert sync_calls == [True]


def test_033_apply_active_box_display_updates_only_open_actual_boxes():
    module = load_script_module("033_visualizer_html.py")

    cycle_zones = [
        {"phase": "BEAR", "result": "DONE", "is_prediction": 0, "is_completed": 1},
        {"phase": "BULL", "result": "ACTIVE", "is_prediction": 0, "is_completed": 0},
        {"phase": "BEAR", "result": "PRED", "is_prediction": 1, "is_completed": 0},
    ]

    updated = module._apply_active_box_display_from_first_pred(cycle_zones)

    assert updated[0]["phase"] == "BEAR"
    assert updated[1]["phase"] == "BEAR"
    assert updated[1]["result"] == "BEAR_ACTIVE"
    assert updated[2]["phase"] == "BEAR"


def test_033_build_frontend_assets_skips_cleanly_when_npx_missing(
    monkeypatch, tmp_path
):
    module = load_script_module("033_visualizer_html.py")

    monkeypatch.setattr(module, "TS_CONFIG", tmp_path / "tsconfig.frontend.json")
    monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    module.TS_CONFIG.write_text("{}", encoding="utf-8")
    dist_dir = tmp_path / "templates" / "dist"
    dist_dir.mkdir(parents=True)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            FileNotFoundError("npx not found")
        ),
    )

    assert module.build_frontend_assets() is True


def test_033_main_returns_before_opening_browser_when_no_data(monkeypatch):
    module = load_script_module("033_visualizer_html.py")

    monkeypatch.setattr(module, "build_frontend_assets", lambda: True)
    monkeypatch.setattr(module, "rewrite_dist_imports", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "build_json_from_supabase", lambda: {})
    monkeypatch.setattr(
        module.webbrowser,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("browser should not open")
        ),
    )
    monkeypatch.setattr(
        module,
        "HTTPServer",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("server should not start")
        ),
    )

    module.main()


def test_033_main_writes_html_and_starts_server_with_mocked_dependencies(
    monkeypatch, tmp_path
):
    module = load_script_module("033_visualizer_html.py")
    opened = []
    served = []

    class DummyServer:
        def serve_forever(self):
            served.append(True)

    monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(module, "OUT_FILE", str(tmp_path / "033_visualizer_html.html"))
    monkeypatch.setattr(module, "build_frontend_assets", lambda: False)
    monkeypatch.setattr(module, "rewrite_dist_imports", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        module, "build_json_from_supabase", lambda: {"btc": {"cycles": []}}
    )
    monkeypatch.setattr(
        module, "generate_html", lambda *_args, **_kwargs: "<html></html>"
    )
    monkeypatch.setattr(module.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(module, "HTTPServer", lambda *_args, **_kwargs: DummyServer())

    module.main()

    assert (tmp_path / "033_visualizer_html.html").read_text(
        encoding="utf-8"
    ) == "<html></html>"
    assert opened == [f"http://127.0.0.1:{module.HTTP_PORT}/033_visualizer_html.html"]
    assert served == [True]
