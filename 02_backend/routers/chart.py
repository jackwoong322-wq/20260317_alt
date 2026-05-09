import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from db import fetch_all_rows, get_supabase

PAIRUSDT_ROOT = Path(__file__).resolve().parents[2] / "01_pairUSDT"
if str(PAIRUSDT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAIRUSDT_ROOT))

from lib.subbox.payload import build_sub_box_payload

router = APIRouter()

_DASHBOARD_CACHE_TTL_SECONDS = 600
_DASHBOARD_SNAPSHOT_CACHE: dict[str, object] = {
    "snapshot": None,
    "created_at": 0.0,
}
_DASHBOARD_REFRESH_LOCK = threading.Lock()


def _apply_active_box_display_from_first_pred(cycle_zones: list[dict]) -> list[dict]:
    if not cycle_zones:
        return cycle_zones

    first_pred = next((z for z in cycle_zones if z.get("is_prediction") == 1), None)
    if not first_pred:
        return cycle_zones

    first_phase = (first_pred.get("phase") or "").upper()
    if first_phase not in ("BEAR", "BULL"):
        return cycle_zones

    active_result = "BEAR_ACTIVE" if first_phase == "BEAR" else "BULL_ACTIVE"
    out: list[dict] = []
    for zone in cycle_zones:
        zcopy = dict(zone)
        if zone.get("is_completed") == 0 and zone.get("is_prediction") == 0:
            zcopy["phase"] = first_phase
            zcopy["result"] = active_result
        out.append(zcopy)
    return out


@router.get("/chart-data/{coin_id}")
def chart_data(coin_id: str):
    sb = get_supabase()
    ohlcv = fetch_all_rows(
        sb.table("ohlcv")
        .select("date, open, high, low, close, volume_quote")
        .eq("coin_id", coin_id)
        .order("date")
    )

    boxes = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("*")
        .eq("coin_id", coin_id)
        .order("cycle_number")
        .order("box_index")
    )

    if not ohlcv:
        raise HTTPException(status_code=404, detail=f"coin_id={coin_id} not found")

    return {"coin_id": coin_id, "ohlcv": ohlcv, "boxes": boxes}


@router.get("/dashboard-data")
def dashboard_data():
    snapshot, _cache_status = _get_or_build_dashboard_snapshot()
    return snapshot["data"]


@router.get("/dashboard-manifest")
def dashboard_manifest():
    snapshot, cache_status = _get_or_build_dashboard_snapshot()
    return {
        "data_version": snapshot["data_version"],
        "generated_at": snapshot["generated_at"],
        "cache_status": cache_status,
        **snapshot["manifest"],
    }


@router.get("/dashboard-initial-data")
def dashboard_initial_data():
    snapshot, cache_status = _get_or_build_dashboard_snapshot()
    manifest = snapshot["manifest"]
    data = snapshot["data"]
    default_coin_id = manifest.get("default_coin_id")
    default_cycle_number = manifest.get("default_cycle_number")

    initial_data: dict[str, dict] = {}
    for coin_manifest in manifest.get("coins", []):
        coin_id = coin_manifest.get("coin_id")
        if not coin_id:
            continue
        coin_data = data.get(coin_id, {})
        coin_copy = {
            "symbol": coin_data.get("symbol") or coin_manifest.get("symbol"),
            "name": coin_data.get("name") or coin_manifest.get("name"),
            "rank": coin_data.get("rank") or coin_manifest.get("rank"),
            "cycles": [],
        }
        if coin_id == default_coin_id:
            coin_copy["cycles"] = [
                cycle
                for cycle in coin_data.get("cycles", [])
                if int(cycle.get("cycle_number") or 0) == default_cycle_number
            ]
        initial_data[coin_id] = coin_copy

    return {
        "data_version": snapshot["data_version"],
        "generated_at": snapshot["generated_at"],
        "cache_status": cache_status,
        "data": initial_data,
    }


@router.get("/dashboard-cycle-data")
def dashboard_cycle_data(coin_id: str, cycle_number: int):
    snapshot, cache_status = _get_or_build_dashboard_snapshot()
    manifest = snapshot["manifest"]
    coin_manifest = _find_manifest_coin(manifest, coin_id)
    if not coin_manifest:
        raise HTTPException(status_code=404, detail=f"coin_id={coin_id} not found")

    cycle_manifest = next(
        (
            cycle
            for cycle in coin_manifest.get("cycles", [])
            if int(cycle.get("cycle_number") or 0) == cycle_number
        ),
        None,
    )
    if not cycle_manifest:
        raise HTTPException(
            status_code=404,
            detail=f"cycle_number={cycle_number} not found for coin_id={coin_id}",
        )

    cycle_data = _find_snapshot_cycle(snapshot, coin_id, cycle_number)
    if cycle_data is None:
        cycle_data = _empty_cycle_payload(cycle_number, cycle_manifest)

    return {
        "data_version": snapshot["data_version"],
        "generated_at": snapshot["generated_at"],
        "cache_status": cache_status,
        "coin_id": coin_id,
        "symbol": coin_manifest.get("symbol"),
        "cycle": cycle_data,
    }


@router.post("/internal/dashboard-cache/refresh")
def refresh_dashboard_cache(x_internal_secret: str | None = Header(default=None)):
    expected_secret = os.getenv("DASHBOARD_CACHE_REFRESH_SECRET")
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=403, detail="forbidden")

    start = time.perf_counter()
    with _DASHBOARD_REFRESH_LOCK:
        try:
            snapshot = _build_dashboard_snapshot()
            now = time.time()
            _DASHBOARD_SNAPSHOT_CACHE["snapshot"] = snapshot
            _DASHBOARD_SNAPSHOT_CACHE["created_at"] = now
        except Exception:
            return {
                "ok": False,
                "error": "dashboard snapshot refresh failed",
                "cache_status": (
                    "stale_kept"
                    if _DASHBOARD_SNAPSHOT_CACHE.get("snapshot") is not None
                    else "empty"
                ),
            }

    return {
        "ok": True,
        "data_version": snapshot["data_version"],
        "generated_at": snapshot["generated_at"],
        "cache_status": "refreshed",
        "build_duration_ms": int((time.perf_counter() - start) * 1000),
    }


def _is_cache_fresh(cache: dict[str, object]) -> bool:
    if cache.get("snapshot") is None:
        return False
    created_at = float(cache.get("created_at") or 0.0)
    return (time.time() - created_at) < _DASHBOARD_CACHE_TTL_SECONDS


def _get_or_build_dashboard_snapshot() -> tuple[dict, str]:
    if _is_cache_fresh(_DASHBOARD_SNAPSHOT_CACHE):
        return _DASHBOARD_SNAPSHOT_CACHE["snapshot"], "hit"  # type: ignore[return-value]

    stale_snapshot = _DASHBOARD_SNAPSHOT_CACHE.get("snapshot")
    acquired = _DASHBOARD_REFRESH_LOCK.acquire(blocking=stale_snapshot is None)
    if not acquired:
        return stale_snapshot, "stale"  # type: ignore[return-value]

    try:
        if _is_cache_fresh(_DASHBOARD_SNAPSHOT_CACHE):
            return _DASHBOARD_SNAPSHOT_CACHE["snapshot"], "hit"  # type: ignore[return-value]
        snapshot = _build_dashboard_snapshot()
        now = time.time()
        _DASHBOARD_SNAPSHOT_CACHE["snapshot"] = snapshot
        _DASHBOARD_SNAPSHOT_CACHE["created_at"] = now
        return snapshot, "miss" if stale_snapshot is None else "refreshed"
    except Exception:
        if stale_snapshot is not None:
            return stale_snapshot, "stale"
        raise HTTPException(status_code=503, detail="dashboard snapshot build failed")
    finally:
        _DASHBOARD_REFRESH_LOCK.release()


def _build_dashboard_snapshot() -> dict:
    data, coins_rows, summary_rows = _build_dashboard_data(return_coins=True)
    manifest = _build_manifest_from_dashboard_data(coins_rows, data, summary_rows)
    now = datetime.now(timezone.utc)
    generated_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data_version = "snapshot-" + now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex
    return {
        "data_version": data_version,
        "generated_at": generated_at,
        "data": data,
        "manifest": manifest,
    }


def _find_manifest_coin(manifest: dict, coin_id: str) -> dict | None:
    return next(
        (coin for coin in manifest.get("coins", []) if coin.get("coin_id") == coin_id),
        None,
    )


def _find_snapshot_cycle(snapshot: dict, coin_id: str, cycle_number: int) -> dict | None:
    coin_data = snapshot.get("data", {}).get(coin_id, {})
    for cycle in coin_data.get("cycles", []):
        if int(cycle.get("cycle_number") or 0) == int(cycle_number):
            return cycle
    return None


def _empty_cycle_payload(cycle_number: int, cycle_manifest: dict | None = None) -> dict:
    manifest = cycle_manifest or {}
    return {
        "cycle_number": cycle_number,
        "cycle_name": manifest.get("cycle_name") or f"Cycle {cycle_number}",
        "peak_date": manifest.get("peak_date"),
        "peak_price": manifest.get("peak_price"),
        "data": [],
        "box_zones": [],
        "prediction_paths": {"bull": [], "bear": []},
        "peak_predictions": [],
        "sub_boxes": [],
        "sub_box_candidates": [],
    }


def _build_manifest_from_dashboard_data(
    coins_rows: list[dict],
    data: dict[str, dict],
    summary_rows: list[dict] | None = None,
) -> dict:
    cycles_by_coin: dict[str, dict[int, dict]] = {}
    for coin_id, coin_data in data.items():
        for cycle in coin_data.get("cycles", []):
            cycle_number = int(cycle.get("cycle_number") or 0)
            if cycle_number <= 0:
                continue
            cycles_by_coin.setdefault(coin_id, {})[cycle_number] = {
                "cycle_number": cycle_number,
                "cycle_name": cycle.get("cycle_name"),
                "peak_date": cycle.get("peak_date"),
                "peak_price": cycle.get("peak_price"),
                "has_data": _cycle_has_payload(cycle),
            }

    for row in summary_rows or []:
        coin_id = row.get("coin_id")
        cycle_number = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_number <= 0:
            continue
        cycles_by_coin.setdefault(coin_id, {}).setdefault(
            cycle_number,
            {
                "cycle_number": cycle_number,
                "cycle_name": row.get("cycle_name"),
                "peak_date": row.get("peak_date"),
                "peak_price": row.get("peak_price"),
                "has_data": False,
            },
        )

    default_coin_id = next(
        (
            str(coin.get("id"))
            for coin in coins_rows
            if str(coin.get("symbol") or "").upper() == "BTC"
        ),
        None,
    )
    if not default_coin_id and coins_rows:
        default_coin_id = str(coins_rows[0].get("id"))

    default_cycle_number = None
    if default_coin_id:
        default_cycle_number = _get_default_cycle_number(
            {"cycles": list(cycles_by_coin.get(default_coin_id, {}).values())}
        )

    manifest_coins = []
    for coin in coins_rows:
        coin_id = coin.get("id")
        if not coin_id:
            continue
        coin_cycles = list(cycles_by_coin.get(coin_id, {}).values())
        current_cycle_number = _get_default_cycle_number({"cycles": coin_cycles})
        cycles = []
        for cycle in coin_cycles:
            cycle_number = int(cycle.get("cycle_number") or 0)
            if cycle_number <= 0:
                continue
            has_data = bool(cycle.get("has_data"))
            cycles.append(
                {
                    "cycle_number": cycle_number,
                    "cycle_name": cycle.get("cycle_name"),
                    "peak_date": cycle.get("peak_date"),
                    "peak_price": cycle.get("peak_price"),
                    "is_current": bool(cycle_number == current_cycle_number),
                    "is_initially_loaded": bool(
                        default_coin_id == coin_id and cycle_number == default_cycle_number
                    ),
                    "can_lazy_load": True,
                    "has_data": has_data,
                }
            )
        manifest_coins.append(
            {
                "coin_id": coin_id,
                "symbol": str(coin.get("symbol") or "").upper(),
                "name": coin.get("name"),
                "rank": coin.get("rank"),
                "cycles": sorted(cycles, key=lambda c: c["cycle_number"]),
            }
        )

    return {
        "default_coin_id": default_coin_id,
        "default_cycle_number": default_cycle_number,
        "coins": manifest_coins,
    }


def _get_default_cycle_number(coin_data: dict) -> int | None:
    cycles = coin_data.get("cycles", [])
    current = next(
        (
            cycle
            for cycle in cycles
            if "current" in str(cycle.get("cycle_name") or "").lower()
        ),
        None,
    )
    if current:
        return int(current.get("cycle_number") or 0)
    cycle_numbers = [int(cycle.get("cycle_number") or 0) for cycle in cycles]
    cycle_numbers = [number for number in cycle_numbers if number > 0]
    return max(cycle_numbers) if cycle_numbers else None


def _cycle_has_payload(cycle: dict) -> bool:
    prediction_paths = cycle.get("prediction_paths") or {}
    return (
        bool(cycle.get("data"))
        or bool(cycle.get("box_zones"))
        or bool(cycle.get("peak_predictions"))
        or any(bool(path) for path in prediction_paths.values())
    )


def _build_dashboard_data(return_coins: bool = False):
    sb = get_supabase()

    coins_rows = fetch_all_rows(
        sb.table("coins").select("id, symbol, name, rank").order("rank")
    )
    summary_rows = fetch_all_rows(
        sb.table("alt_cycle_summary")
        .select("coin_id, cycle_number, cycle_name, peak_date, peak_price")
        .order("coin_id")
        .order("cycle_number")
    )
    cycle_rows = fetch_all_rows(
        sb.table("alt_cycle_data")
        .select(
            "coin_id, cycle_number, cycle_name, days_since_peak, close_rate, high_rate, low_rate, peak_date, peak_price, timestamp"
        )
        .order("coin_id")
        .order("cycle_number")
        .order("days_since_peak")
    )
    box_rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select(
            "coin_id, cycle_number, box_index, phase, result, start_x, end_x, hi, lo, hi_day, lo_day, duration, range_pct, is_prediction, is_completed, rise_days, decline_days"
        )
        .order("coin_id")
        .order("cycle_number")
        .order("box_index")
    )
    path_rows = fetch_all_rows(
        sb.table("coin_prediction_paths")
        .select("coin_id, cycle_number, scenario, day_x, value")
        .order("coin_id")
        .order("cycle_number")
        .order("scenario")
        .order("day_x")
    )
    peak_rows = fetch_all_rows(
        sb.table("coin_prediction_peaks")
        .select("coin_id, cycle_number, peak_type, predicted_value, predicted_day")
        .order("coin_id")
        .order("cycle_number")
    )

    cycles_by_coin: dict[str, dict[int, dict]] = {}
    for row in cycle_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue

        coin_cycles = cycles_by_coin.setdefault(coin_id, {})
        cycle = coin_cycles.setdefault(
            cycle_num,
            {
                "cycle_number": cycle_num,
                "cycle_name": row.get("cycle_name"),
                "peak_date": row.get("peak_date"),
                "peak_price": row.get("peak_price"),
                "data": [],
            },
        )
        cycle["data"].append(
            {
                "x": int(row.get("days_since_peak") or 0),
                "close": round(float(row.get("close_rate") or 0.0), 4),
                "high": round(float(row.get("high_rate") or 0.0), 4),
                "low": round(float(row.get("low_rate") or 0.0), 4),
                "date": str(row.get("timestamp") or "")[:10],
            }
        )

    box_by_coin_cycle: dict[str, dict[int, list[dict]]] = {}
    for row in box_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue

        box_by_coin_cycle.setdefault(coin_id, {}).setdefault(cycle_num, []).append(
            {
                "boxIndex": int(row.get("box_index") or 0),
                "startX": row.get("start_x"),
                "endX": row.get("end_x"),
                "hi": row.get("hi"),
                "lo": row.get("lo"),
                "hiDay": row.get("hi_day"),
                "loDay": row.get("lo_day"),
                "duration": row.get("duration"),
                "rangePct": f"{float(row.get('range_pct') or 0.0):.1f}",
                "phase": row.get("phase"),
                "result": row.get("result"),
                "is_prediction": row.get("is_prediction"),
                "is_completed": row.get("is_completed"),
                "rise_days": row.get("rise_days"),
                "decline_days": row.get("decline_days"),
            }
        )

    path_by_coin_cycle: dict[str, dict[int, dict[str, list[dict]]]] = {}
    for row in path_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue

        cycle_paths = path_by_coin_cycle.setdefault(coin_id, {}).setdefault(
            cycle_num, {"bull": [], "bear": []}
        )
        key = str(row.get("scenario") or "").lower()
        key = key if key in ("bull", "bear") else "bull"
        cycle_paths[key].append({"x": row.get("day_x"), "value": row.get("value")})

    peak_by_coin_cycle: dict[str, dict[int, list[dict]]] = {}
    for row in peak_rows:
        coin_id = row.get("coin_id")
        cycle_num = int(row.get("cycle_number") or 0)
        if not coin_id or cycle_num <= 0:
            continue

        peak_by_coin_cycle.setdefault(coin_id, {}).setdefault(cycle_num, []).append(
            {
                "type": row.get("peak_type"),
                "value": row.get("predicted_value"),
                "day_x": row.get("predicted_day"),
            }
        )

    out: dict[str, dict] = {}
    for coin in coins_rows:
        coin_id = coin.get("id")
        if not coin_id:
            continue

        cycles = dict(cycles_by_coin.get(coin_id, {}))
        coin_zones = box_by_coin_cycle.get(coin_id, {})
        if not cycles and not coin_zones:
            continue

        if not cycles and coin_zones:
            for cycle_num in coin_zones:
                cycles[cycle_num] = {
                    "cycle_number": cycle_num,
                    "cycle_name": f"Cycle {cycle_num}",
                    "peak_date": "",
                    "peak_price": None,
                    "data": [],
                }

        cycles_list: list[dict] = []
        for cycle_num in sorted(cycles.keys()):
            cycle_data = cycles[cycle_num]
            raw_zones = coin_zones.get(cycle_num, [])
            cycle_zones = _apply_active_box_display_from_first_pred(raw_zones)
            cycle_paths = path_by_coin_cycle.get(coin_id, {}).get(
                cycle_num, {"bull": [], "bear": []}
            )
            cycle_peaks = peak_by_coin_cycle.get(coin_id, {}).get(cycle_num, [])
            sub_boxes, sub_box_candidates = build_sub_box_payload(
                cycle_data.get("data", []),
                cycle_zones,
            )
            cycles_list.append(
                {
                    "cycle_number": cycle_num,
                    "cycle_name": cycle_data.get("cycle_name"),
                    "peak_date": cycle_data.get("peak_date"),
                    "peak_price": cycle_data.get("peak_price"),
                    "data": cycle_data.get("data", []),
                    "box_zones": cycle_zones,
                    "prediction_paths": cycle_paths,
                    "peak_predictions": cycle_peaks,
                    "sub_boxes": sub_boxes,
                    "sub_box_candidates": sub_box_candidates,
                }
            )

        out[coin_id] = {
            "symbol": str(coin.get("symbol") or "").upper(),
            "name": coin.get("name"),
            "rank": coin.get("rank"),
            "cycles": cycles_list,
        }

    if return_coins:
        return out, coins_rows, summary_rows
    return out
