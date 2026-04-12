from fastapi import APIRouter, HTTPException
from db import fetch_all_rows, get_supabase

router = APIRouter()


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
    sb = get_supabase()

    coins_rows = fetch_all_rows(
        sb.table("coins").select("id, symbol, name, rank").order("rank")
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
                }
            )

        out[coin_id] = {
            "symbol": str(coin.get("symbol") or "").upper(),
            "name": coin.get("name"),
            "rank": coin.get("rank"),
            "cycles": cycles_list,
        }

    return out
