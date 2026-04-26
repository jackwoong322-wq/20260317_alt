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
