"""Heuristic candidate generation for active sub-boxes."""

from __future__ import annotations

from typing import Any

from lib.subbox.detect import SUB_BOX_LAYER, SUB_BOX_SCOPE, sub_box_label


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


def _last_point(data: list[dict]) -> dict | None:
    if not data:
        return None
    return max(data, key=lambda point: _as_int(point.get("x")))


def _candidate_role(
    sub_box: dict,
    current_close: float,
    previous_sub_box: dict | None,
    *,
    proximity_ratio: float,
    compression_ratio: float,
) -> str:
    upper = _as_float(sub_box.get("upper"))
    lower = _as_float(sub_box.get("lower"))
    breakout_up = _as_float(sub_box.get("breakout_up_level"), upper)
    breakdown = _as_float(sub_box.get("breakdown_level"), lower)
    width = max(upper - lower, 0.0)

    if current_close >= breakout_up:
        return "breakout_watch"
    if current_close <= breakdown:
        return "breakdown_watch"
    if width > 0 and current_close >= upper - width * proximity_ratio:
        return "upper_test"
    if width > 0 and current_close <= lower + width * proximity_ratio:
        return "lower_test"
    if previous_sub_box is not None:
        prev_range = _as_float(previous_sub_box.get("range_pct"))
        cur_range = _as_float(sub_box.get("range_pct"))
        if prev_range > 0 and cur_range <= prev_range * compression_ratio:
            return "compression"
    return "range_continuation"


def generate_sub_box_candidate(
    sub_boxes: list[dict],
    parent_box: dict,
    data: list[dict],
    *,
    watch_days: int = 7,
    proximity_ratio: float = 0.2,
    compression_ratio: float = 0.75,
) -> dict | None:
    """Generate one heuristic internal candidate from the latest active sub-box."""
    if parent_box.get("result") != "ACTIVE":
        return None
    active_boxes = [box for box in sub_boxes if int(box.get("is_completed", 0)) == 0]
    if not active_boxes:
        return None
    latest = max(active_boxes, key=lambda box: _as_int(box.get("end_x")))
    last = _last_point(data)
    if last is None:
        return None

    ordered = sorted(sub_boxes, key=lambda box: _as_int(box.get("sub_box_index")))
    latest_idx = ordered.index(latest) if latest in ordered else len(ordered) - 1
    previous = ordered[latest_idx - 1] if latest_idx > 0 else None
    current_close = _as_float(last.get("close"))
    role = _candidate_role(
        latest,
        current_close,
        previous,
        proximity_ratio=proximity_ratio,
        compression_ratio=compression_ratio,
    )
    candidate_index = _as_int(latest.get("sub_box_index")) + 1
    start_x = _as_int(last.get("x")) + 1
    end_x = start_x + max(int(watch_days), 1) - 1

    return {
        "layer": SUB_BOX_LAYER,
        "scope": SUB_BOX_SCOPE,
        "parent_box_index": _as_int(parent_box.get("box_index")),
        "parent_phase": parent_box.get("phase"),
        "parent_result": parent_box.get("result"),
        "sub_box_index": candidate_index,
        "sub_box_label": sub_box_label(candidate_index),
        "start_x": start_x,
        "end_x": end_x,
        "upper": _as_float(latest.get("upper")),
        "lower": _as_float(latest.get("lower")),
        "breakout_up_level": _as_float(latest.get("breakout_up_level")),
        "breakdown_level": _as_float(latest.get("breakdown_level")),
        "scenario_role": role,
        "source": "heuristic",
        "visibility": "default",
        "is_prediction": 1,
        "is_completed": 0,
        "valid_until_day": end_x,
        "invalidated_by": "upper/lower watch level break",
    }
