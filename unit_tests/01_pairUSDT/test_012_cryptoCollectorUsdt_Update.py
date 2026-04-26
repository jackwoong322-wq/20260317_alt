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
