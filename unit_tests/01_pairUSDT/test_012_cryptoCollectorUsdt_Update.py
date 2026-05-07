import importlib.util
import sys
import uuid
from pathlib import Path

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


def test_012_main_fetches_full_binance_history_when_ohlcv_is_empty(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")
    saved = []

    monkeypatch.setattr(module, "today_utc", lambda: "2026-04-03")
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(
        module,
        "get_coins_from_supabase",
        lambda _sb: [{"id": "zcash", "symbol": "ZEC", "name": "Zcash", "rank": 999}],
    )
    monkeypatch.setattr(module, "get_last_date_supabase", lambda *_args: None)
    monkeypatch.setattr(
        module,
        "binance_fetch_klines",
        lambda symbol, from_date=None: [
            [
                1775001600000,
                "10",
                "12",
                "9",
                "11",
                "100",
                1775087999999,
                "1100",
                7,
            ],
            [
                1775174400000,
                "11",
                "13",
                "10",
                "12",
                "101",
                1775260799999,
                "1212",
                8,
            ],
        ],
    )

    def fake_save(_supabase, coin_id, rows):
        saved.append((coin_id, rows))
        return len(rows)

    monkeypatch.setattr(module, "save_rows_supabase", fake_save)

    module.main()

    assert len(saved) == 1
    assert saved[0][0] == "zcash"
    assert [row["date"] for row in saved[0][1]] == ["2026-04-01"]


def test_012_update_uses_binance_only():
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")

    assert not hasattr(module, "coingecko_fetch_daily_range")
