import sys
from pathlib import Path


PAIRUSDT_ROOT = Path(__file__).resolve().parents[4] / "01_pairUSDT"
if str(PAIRUSDT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAIRUSDT_ROOT))

from lib.subbox.detect import detect_sub_boxes, slice_parent_box_data, sub_box_label


def _parent():
    return {
        "box_index": 3,
        "phase": "BEAR",
        "result": "ACTIVE",
        "start_x": 100,
        "end_x": 120,
        "hi": 70.0,
        "lo": 50.0,
    }


def _point(x, high, low, close):
    return {"x": x, "high": high, "low": low, "close": close}


def test_sub_box_label_rolls_over_after_z():
    assert sub_box_label(0) == "A"
    assert sub_box_label(25) == "Z"
    assert sub_box_label(26) == "AA"


def test_slice_parent_box_data_respects_parent_boundary():
    data = [
        _point(99, 1, 1, 1),
        _point(100, 10, 9, 9.5),
        _point(101, 11, 9, 10),
        _point(121, 12, 10, 11),
    ]

    sliced = slice_parent_box_data(data, _parent())

    assert [p["x"] for p in sliced] == [100, 101]


def test_detect_sub_boxes_returns_empty_for_short_data():
    boxes = detect_sub_boxes([_point(100, 10, 9, 9.5)], _parent(), min_duration=3)

    assert boxes == []


def test_detect_sub_boxes_returns_empty_for_non_active_parent():
    parent = {**_parent(), "result": "COMPLETED"}
    data = [
        _point(100, 64, 60, 62),
        _point(101, 65, 59, 63),
        _point(102, 64, 60, 61),
    ]

    boxes = detect_sub_boxes(data, parent, min_duration=3)

    assert boxes == []


def test_detect_sub_boxes_filters_tiny_noise_ranges():
    data = [
        _point(100, 60.2, 60.0, 60.1),
        _point(101, 60.2, 60.0, 60.1),
        _point(102, 60.2, 60.0, 60.1),
        _point(103, 60.2, 60.0, 60.1),
        _point(104, 60.2, 60.0, 60.1),
    ]

    boxes = detect_sub_boxes(data, _parent(), min_duration=5, min_range_pct=1.0)

    assert boxes == []


def test_detect_sub_boxes_detects_one_active_clean_range():
    data = [
        _point(100, 64, 60, 62),
        _point(101, 65, 59, 63),
        _point(102, 64, 60, 61),
        _point(103, 65, 60, 64),
        _point(104, 64, 59, 62),
    ]

    boxes = detect_sub_boxes(data, _parent(), min_duration=5)

    assert len(boxes) == 1
    box = boxes[0]
    assert box["layer"] == "sub_box"
    assert box["scope"] == "active_internal"
    assert box["parent_box_index"] == 3
    assert box["sub_box_label"] == "A"
    assert box["start_x"] == 100
    assert box["end_x"] == 104
    assert box["upper"] == 65.0
    assert box["lower"] == 59.0
    assert box["is_completed"] == 0
    assert box["is_prediction"] == 0


def test_detect_sub_boxes_completes_range_on_breakout_and_marks_tail_active():
    data = [
        _point(100, 64, 60, 62),
        _point(101, 65, 59, 63),
        _point(102, 64, 60, 61),
        _point(103, 65, 60, 64),
        _point(104, 64, 59, 62),
        _point(105, 68, 63, 67),
        _point(106, 69, 64, 68),
        _point(107, 68, 64, 66),
        _point(108, 69, 65, 67),
        _point(109, 68, 64, 66),
    ]

    boxes = detect_sub_boxes(data, _parent(), min_duration=5, breakout_buffer_pct=1.0)

    assert len(boxes) == 2
    assert boxes[0]["is_completed"] == 1
    assert boxes[0]["end_x"] == 104
    assert boxes[1]["is_completed"] == 0
    assert boxes[1]["start_x"] == 105
    assert boxes[1]["sub_box_label"] == "B"
