"""Chart payload helpers for sub-box analysis.

Sub-boxes are generated from the current active macro box only. The output is a
separate chart layer and must not be merged into macro box results.
"""

from __future__ import annotations

from typing import Any

from lib.subbox.detect import detect_sub_boxes
from lib.subbox.predict import generate_sub_box_candidate


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _latest_day(cycle_data: list[dict]) -> int | None:
    days = [_as_int(point.get("x")) for point in cycle_data if point.get("x") is not None]
    return max(days) if days else None


def _find_active_macro_box(cycle_zones: list[dict], latest_day: int) -> dict | None:
    active_zones = []
    for zone in cycle_zones or []:
        if _as_int(zone.get("is_prediction")) != 0:
            continue
        if _as_int(zone.get("is_completed")) != 0:
            continue
        result = str(zone.get("result") or "").upper()
        if result and "ACTIVE" not in result:
            continue
        start_x = _as_int(zone.get("startX", zone.get("start_x")))
        if start_x > latest_day:
            continue
        active_zones.append((start_x, zone))
    if not active_zones:
        return None
    return sorted(active_zones, key=lambda item: item[0])[-1][1]


def _to_detector_parent(zone: dict, latest_day: int) -> dict:
    start_x = _as_int(zone.get("startX", zone.get("start_x")))
    raw_end_x = _as_int(zone.get("endX", zone.get("end_x")), latest_day)
    return {
        "box_index": _as_int(zone.get("boxIndex", zone.get("box_index"))),
        "phase": zone.get("phase"),
        "result": "ACTIVE",
        "start_x": start_x,
        "end_x": min(raw_end_x, latest_day) if raw_end_x > 0 else latest_day,
    }


def _to_chart_sub_box(box: dict) -> dict:
    return {
        "layer": box.get("layer"),
        "scope": box.get("scope"),
        "parentBoxIndex": box.get("parent_box_index"),
        "parentPhase": box.get("parent_phase"),
        "parentResult": box.get("parent_result"),
        "subBoxIndex": box.get("sub_box_index"),
        "subBoxLabel": box.get("sub_box_label"),
        "startX": box.get("start_x"),
        "endX": box.get("end_x"),
        "upper": box.get("upper"),
        "lower": box.get("lower"),
        "pivotHighDay": box.get("pivot_high_day"),
        "pivotLowDay": box.get("pivot_low_day"),
        "breakoutUpLevel": box.get("breakout_up_level"),
        "breakdownLevel": box.get("breakdown_level"),
        "duration": box.get("duration"),
        "rangePct": f"{_as_float(box.get('range_pct')):.1f}",
        "is_completed": box.get("is_completed"),
        "is_prediction": box.get("is_prediction"),
        "source": box.get("source"),
        "visibility": box.get("visibility"),
        "scenarioRole": box.get("scenario_role"),
    }


def build_sub_box_payload(
    cycle_data: list[dict],
    cycle_zones: list[dict],
    *,
    min_duration: int = 5,
    min_range_pct: float = 0.75,
    watch_days: int = 7,
) -> tuple[list[dict], list[dict]]:
    latest_day = _latest_day(cycle_data)
    if latest_day is None:
        return [], []

    active_zone = _find_active_macro_box(cycle_zones, latest_day)
    if active_zone is None:
        return [], []

    parent = _to_detector_parent(active_zone, latest_day)
    observed = detect_sub_boxes(
        cycle_data,
        parent,
        min_duration=min_duration,
        min_range_pct=min_range_pct,
    )
    candidate = generate_sub_box_candidate(
        observed,
        parent,
        cycle_data,
        watch_days=watch_days,
    )

    sub_boxes = [_to_chart_sub_box(box) for box in observed]
    sub_box_candidates = [_to_chart_sub_box(candidate)] if candidate else []
    return sub_boxes, sub_box_candidates
