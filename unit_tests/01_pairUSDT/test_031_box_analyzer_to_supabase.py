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
