import sys
from pathlib import Path


PAIRUSDT_ROOT = Path(__file__).resolve().parents[4] / "01_pairUSDT"
if str(PAIRUSDT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAIRUSDT_ROOT))

from lib.subbox.predict import generate_sub_box_candidate


def _parent():
    return {
        "box_index": 3,
        "phase": "BEAR",
        "result": "ACTIVE",
        "start_x": 100,
        "end_x": 150,
    }


def _active_box(**overrides):
    box = {
        "parent_box_index": 3,
        "sub_box_index": 0,
        "sub_box_label": "A",
        "start_x": 100,
        "end_x": 110,
        "upper": 66.0,
        "lower": 60.0,
        "breakout_up_level": 66.5,
        "breakdown_level": 59.5,
        "range_pct": 10.0,
        "is_completed": 0,
    }
    box.update(overrides)
    return box


def _completed_box(**overrides):
    box = _active_box(is_completed=1)
    box.update(overrides)
    return box


def _point(x, close):
    return {"x": x, "high": close, "low": close, "close": close}


def test_generate_candidate_returns_none_without_active_sub_box():
    candidate = generate_sub_box_candidate([_completed_box()], _parent(), [_point(110, 63)])

    assert candidate is None


def test_generate_candidate_returns_none_for_non_active_parent():
    parent = {**_parent(), "result": "COMPLETED"}

    candidate = generate_sub_box_candidate([_active_box()], parent, [_point(110, 63)])

    assert candidate is None


def test_generate_candidate_upper_test_when_close_near_upper():
    candidate = generate_sub_box_candidate([_active_box()], _parent(), [_point(110, 65.4)])

    assert candidate["scenario_role"] == "upper_test"
    assert candidate["is_prediction"] == 1
    assert candidate["source"] == "heuristic"
    assert candidate["sub_box_label"] == "B"


def test_generate_candidate_lower_test_when_close_near_lower():
    candidate = generate_sub_box_candidate([_active_box()], _parent(), [_point(110, 60.4)])

    assert candidate["scenario_role"] == "lower_test"


def test_generate_candidate_breakout_watch_takes_priority():
    candidate = generate_sub_box_candidate([_active_box()], _parent(), [_point(110, 67.0)])

    assert candidate["scenario_role"] == "breakout_watch"


def test_generate_candidate_breakdown_watch_takes_priority():
    candidate = generate_sub_box_candidate([_active_box()], _parent(), [_point(110, 59.0)])

    assert candidate["scenario_role"] == "breakdown_watch"


def test_generate_candidate_compression_when_range_narrows():
    previous = _completed_box(sub_box_index=0, range_pct=20.0)
    active = _active_box(sub_box_index=1, upper=63.0, lower=60.0, range_pct=5.0)

    candidate = generate_sub_box_candidate([previous, active], _parent(), [_point(110, 61.5)])

    assert candidate["scenario_role"] == "compression"
    assert candidate["sub_box_label"] == "C"
