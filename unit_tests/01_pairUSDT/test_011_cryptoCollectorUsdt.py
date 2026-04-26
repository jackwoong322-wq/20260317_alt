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
