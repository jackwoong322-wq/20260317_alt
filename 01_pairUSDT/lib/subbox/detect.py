"""Heuristic sub-box detector for active macro boxes.

Sub-boxes are an internal interpretation layer. They must not be mixed into
the macro `coin_analysis_results` box sequence.
"""

from __future__ import annotations

from typing import Any


SUB_BOX_LAYER = "sub_box"
SUB_BOX_SCOPE = "active_internal"
SUB_BOX_ROLES = {
    "range_continuation",
    "upper_test",
    "lower_test",
    "compression",
    "breakout_watch",
    "breakdown_watch",
}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def sub_box_label(index: int) -> str:
    """Return A, B, ..., Z, AA, AB style labels for internal boxes."""
    if index < 0:
        raise ValueError("index must be >= 0")
    label = ""
    n = index
    while True:
        label = chr(ord("A") + (n % 26)) + label
        n = n // 26 - 1
        if n < 0:
            return label


def _range_pct(upper: float, lower: float) -> float:
    if lower <= 0:
        return 0.0
    return abs(upper - lower) / lower * 100.0


def slice_parent_box_data(data: list[dict], parent_box: dict) -> list[dict]:
    """Return points inside the observed parent macro-box day range."""
    start_x = _as_int(parent_box.get("start_x"))
    end_x = _as_int(parent_box.get("end_x"), 10**9)
    sliced = [
        {
            **point,
            "x": _as_int(point.get("x")),
            "high": _as_float(point.get("high")),
            "low": _as_float(point.get("low")),
            "close": _as_float(point.get("close")),
        }
        for point in data
        if start_x <= _as_int(point.get("x")) <= end_x
    ]
    return sorted(sliced, key=lambda point: point["x"])


def _make_sub_box(
    points: list[dict],
    parent_box: dict,
    sub_index: int,
    is_completed: bool,
    breakout_buffer_pct: float,
) -> dict:
    upper_point = max(points, key=lambda p: p["high"])
    lower_point = min(points, key=lambda p: p["low"])
    upper = float(upper_point["high"])
    lower = float(lower_point["low"])
    start_x = int(points[0]["x"])
    end_x = int(points[-1]["x"])
    return {
        "layer": SUB_BOX_LAYER,
        "scope": SUB_BOX_SCOPE,
        "parent_box_index": _as_int(parent_box.get("box_index")),
        "parent_phase": parent_box.get("phase"),
        "parent_result": parent_box.get("result"),
        "sub_box_index": sub_index,
        "sub_box_label": sub_box_label(sub_index),
        "start_x": start_x,
        "end_x": end_x,
        "upper": upper,
        "lower": lower,
        "pivot_high_day": int(upper_point["x"]),
        "pivot_low_day": int(lower_point["x"]),
        "breakout_up_level": upper * (1.0 + breakout_buffer_pct / 100.0),
        "breakdown_level": lower * (1.0 - breakout_buffer_pct / 100.0),
        "duration": end_x - start_x + 1,
        "range_pct": _range_pct(upper, lower),
        "is_completed": 1 if is_completed else 0,
        "is_prediction": 0,
        "source": "observed",
        "visibility": "default",
        "scenario_role": "range_continuation",
    }


def _append_box_if_valid(boxes: list[dict], box: dict, min_range_pct: float) -> bool:
    if box["range_pct"] < min_range_pct:
        return False
    boxes.append(box)
    return True


def detect_sub_boxes(
    data: list[dict],
    parent_box: dict,
    *,
    min_duration: int = 5,
    breakout_buffer_pct: float = 0.5,
    min_range_pct: float = 0.0,
) -> list[dict]:
    """Detect internal ranges inside one parent active macro box.

    The detector is intentionally conservative:
    - it only operates inside the parent box range;
    - it creates completed sub-boxes when close breaks the initial range;
    - the final sub-box is active (`is_completed=0`).
    """
    if parent_box.get("result") != "ACTIVE":
        return []
    points = slice_parent_box_data(data, parent_box)
    if min_duration <= 1:
        raise ValueError("min_duration must be > 1")
    if min_range_pct < 0:
        raise ValueError("min_range_pct must be >= 0")
    if len(points) < min_duration:
        return []

    boxes: list[dict] = []
    start = 0
    sub_index = 0
    while start + min_duration <= len(points):
        seed = points[start : start + min_duration]
        seed_upper = max(p["high"] for p in seed)
        seed_lower = min(p["low"] for p in seed)
        upper_break = seed_upper * (1.0 + breakout_buffer_pct / 100.0)
        lower_break = seed_lower * (1.0 - breakout_buffer_pct / 100.0)

        break_idx = None
        for idx in range(start + min_duration, len(points)):
            close = points[idx]["close"]
            if close > upper_break or close < lower_break:
                break_idx = idx
                break

        if break_idx is None:
            _append_box_if_valid(
                boxes,
                _make_sub_box(
                    points[start:],
                    parent_box,
                    sub_index,
                    is_completed=False,
                    breakout_buffer_pct=breakout_buffer_pct,
                ),
                min_range_pct,
            )
            break

        end = break_idx - 1
        if end - start + 1 >= min_duration:
            added = _append_box_if_valid(
                boxes,
                _make_sub_box(
                    points[start : end + 1],
                    parent_box,
                    sub_index,
                    is_completed=True,
                    breakout_buffer_pct=breakout_buffer_pct,
                ),
                min_range_pct,
            )
            if added:
                sub_index += 1
        start = break_idx

    if boxes and boxes[-1]["is_completed"] == 1 and start < len(points):
        tail = points[start:]
        if len(tail) >= min_duration:
            _append_box_if_valid(
                boxes,
                _make_sub_box(
                    tail,
                    parent_box,
                    sub_index,
                    is_completed=False,
                    breakout_buffer_pct=breakout_buffer_pct,
                ),
                min_range_pct,
            )

    return boxes
