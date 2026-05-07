import importlib.util
import sys
import uuid
from pathlib import Path


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


def make_kline(date_ms: int, close: str = "11") -> list:
    return [
        date_ms,
        "10",
        "12",
        "9",
        close,
        "100",
        date_ms + 86_399_999,
        "1100",
        7,
    ]


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
    fetch_calls = []
    saved = []

    monkeypatch.setattr(module, "today_utc", lambda: "2026-04-03")
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(
        module,
        "get_coins_from_supabase",
        lambda _sb: [{"id": "zcash", "symbol": "ZEC", "name": "Zcash", "rank": 999}],
    )
    monkeypatch.setattr(module, "get_last_date_supabase", lambda *_args: None)
    def fake_fetch(symbol, from_date=None):
        fetch_calls.append((symbol, from_date))
        return [
            make_kline(1775001600000),
            make_kline(1775174400000, close="12"),
        ]

    monkeypatch.setattr(module, "binance_fetch_klines", fake_fetch)

    def fake_save(_supabase, coin_id, rows):
        saved.append((coin_id, rows))
        return len(rows)

    monkeypatch.setattr(module, "save_rows_supabase", fake_save)

    module.main()

    assert fetch_calls == [("ZEC", None)]
    assert len(saved) == 1
    assert saved[0][0] == "zcash"
    assert [row["date"] for row in saved[0][1]] == ["2026-04-01"]


def test_012_main_backfills_multiple_empty_ohlcv_coins(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")
    fetch_calls = []
    saved = []

    monkeypatch.setattr(module, "today_utc", lambda: "2026-04-03")
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(
        module,
        "get_coins_from_supabase",
        lambda _sb: [
            {"id": "zcash", "symbol": "ZEC", "name": "Zcash", "rank": 999},
            {"id": "litecoin", "symbol": "LTC", "name": "Litecoin", "rank": 20},
        ],
    )
    monkeypatch.setattr(module, "get_last_date_supabase", lambda *_args: None)

    def fake_fetch(symbol, from_date=None):
        fetch_calls.append((symbol, from_date))
        return [make_kline(1775001600000)]

    def fake_save(_supabase, coin_id, rows):
        saved.append((coin_id, rows))
        return len(rows)

    monkeypatch.setattr(module, "binance_fetch_klines", fake_fetch)
    monkeypatch.setattr(module, "save_rows_supabase", fake_save)

    module.main()

    assert fetch_calls == [("ZEC", None), ("LTC", None)]
    assert [coin_id for coin_id, _rows in saved] == ["zcash", "litecoin"]


def test_012_fetch_binance_rows_returns_empty_without_fallback(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")
    calls = []

    assert not hasattr(module, "coingecko_fetch_daily_range")

    def fake_fetch(symbol, from_date=None):
        calls.append((symbol, from_date))
        return []

    monkeypatch.setattr(module, "binance_fetch_klines", fake_fetch)

    assert module.fetch_binance_ohlcv_rows("ZEC", "2026-04-01") == []
    assert calls == [("ZEC", "2026-04-01")]


def test_012_fetch_binance_rows_sets_source_to_binance(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")

    monkeypatch.setattr(
        module,
        "binance_fetch_klines",
        lambda symbol, from_date=None: [make_kline(1775001600000)],
    )

    rows = module.fetch_binance_ohlcv_rows("ZEC", None)

    assert rows[0]["source"] == "binance"


def test_012_main_does_not_save_when_only_today_candle_is_returned(monkeypatch):
    module = load_script_module("012_cryptoCollectorUsdt_Update.py")
    save_calls = []

    monkeypatch.setattr(module, "today_utc", lambda: "2026-04-03")
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(
        module,
        "get_coins_from_supabase",
        lambda _sb: [{"id": "zcash", "symbol": "ZEC", "name": "Zcash", "rank": 999}],
    )
    monkeypatch.setattr(module, "get_last_date_supabase", lambda *_args: "2026-04-02")
    monkeypatch.setattr(
        module,
        "binance_fetch_klines",
        lambda symbol, from_date=None: [make_kline(1775174400000)],
    )

    def fake_save(*_args):
        save_calls.append(_args)
        raise AssertionError("should not save today's unfinished candle")

    monkeypatch.setattr(module, "save_rows_supabase", fake_save)

    module.main()

    assert save_calls == []
