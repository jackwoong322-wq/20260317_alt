"""Prediction path rebuilding from is_prediction=1 boxes."""

import sqlite3

from lib.common.utils import _ease_in_out


def _interpolate_segment(start_val: float, end_val: float, start_day: int, end_day: int):
    """Interpolate start_day~end_day with _ease_in_out; return (day_x, value) list."""
    if end_day <= start_day:
        return [(int(start_day), float(start_val))]
    n = end_day - start_day
    pts: list[tuple[int, float]] = []
    for i in range(n + 1):
        t = i / n
        v = start_val + _ease_in_out(t) * (end_val - start_val)
        pts.append((int(start_day + i), float(v)))
    return pts


def _build_paths_for_cycle(rows, symbol: str, scenario: str, start_val: float | None = None):
    """Build (symbol, scenario, day_x, value) path from prediction boxes."""
    if not rows:
        return []

    rows = sorted(rows, key=lambda r: int(r["start_x"]))
    path: list[tuple[str, str, int, float]] = []

    if scenario == "bear":
        cur_val = float(rows[0]["hi"])
    else:
        cur_val = float(start_val if start_val is not None else rows[0]["hi"])

    for i, r in enumerate(rows):
        start_x = int(r["start_x"])
        end_x = int(r["end_x"])
        hi = float(r["hi"])
        lo = float(r["lo"])
        hi_day = int(r["hi_day"])
        lo_day = int(r["lo_day"])

        if i + 1 < len(rows):
            next_start_val = float(rows[i + 1]["hi"])
        else:
            next_start_val = float(hi)

        segs: list[tuple[float, float, int, int]] = []

        if scenario == "bear":
            if lo_day < hi_day:
                segs.append((cur_val, lo, start_x, lo_day))
                segs.append((lo, hi, lo_day, hi_day))
                segs.append((hi, next_start_val, hi_day, end_x))
            else:
                segs.append((cur_val, hi, start_x, hi_day))
                segs.append((hi, lo, hi_day, lo_day))
                segs.append((lo, next_start_val, lo_day, end_x))
        else:
            if hi_day < lo_day:
                segs.append((cur_val, hi, start_x, hi_day))
                segs.append((hi, lo, hi_day, lo_day))
                segs.append((lo, next_start_val, lo_day, end_x))
            else:
                segs.append((cur_val, lo, start_x, lo_day))
                segs.append((lo, hi, lo_day, hi_day))
                segs.append((hi, next_start_val, hi_day, end_x))

        for sv, ev, sd, ed in segs:
            seg_pts = _interpolate_segment(sv, ev, sd, ed)
            for day, val in seg_pts:
                path.append((symbol, scenario, int(day), float(val)))
            if seg_pts:
                _, last_v = seg_pts[-1]
                cur_val = float(last_v)

    if scenario == "bull" and path and rows:
        peak_hi = float(rows[-1]["hi"])
        sym, sc, day, _ = path[-1]
        path[-1] = (sym, sc, day, peak_hi)

    return path


def _load_bottom_predictions(conn: sqlite3.Connection) -> dict:
    """Load (coin_id, cycle_number) -> (bottom_day, bottom_lo) from coin_prediction_peaks."""
    try:
        rows = conn.execute(
            """
            SELECT coin_id, cycle_number, predicted_day, predicted_value
            FROM coin_prediction_peaks
            WHERE peak_type = 'BOTTOM' AND predicted_day IS NOT NULL AND predicted_value IS NOT NULL
            """
        ).fetchall()
    except Exception:
        return {}
    result = {}
    for r in rows:
        cid = r[0]
        cyc = int(r[1]) if r[1] is not None else 0
        try:
            cid_norm = int(cid) if cid is not None else 0
        except (ValueError, TypeError):
            cid_norm = str(cid) if cid is not None else ""
        result[(cid_norm, cyc)] = (int(r[2]), float(r[3]))
    return result


def rebuild_prediction_paths(conn: sqlite3.Connection):
    """Rebuild coin_prediction_paths from is_prediction=1 boxes using interpolation."""
    cur = conn.cursor()
    cur.execute("DELETE FROM coin_prediction_paths")
    bottom_by_coin_cycle = _load_bottom_predictions(conn)

    cur.execute(
        """
        SELECT
            coin_id,
            symbol,
            cycle_number,
            phase,
            start_x,
            end_x,
            hi,
            lo,
            hi_day,
            lo_day
        FROM coin_analysis_results
        WHERE is_prediction = 1
        ORDER BY symbol, cycle_number, start_x
        """
    )
    rows = cur.fetchall()

    by_symbol: dict[str, dict[int, list[dict]]] = {}
    for coin_id, sym, cyc, phase, sx, ex, hi, lo, hd, ld in rows:
        sym = str(sym)
        cyc = int(cyc)
        bucket = by_symbol.setdefault(sym, {}).setdefault(cyc, [])
        bucket.append(
            {
                "coin_id": coin_id,
                "symbol": sym,
                "cycle_number": cyc,
                "phase": str(phase),
                "start_x": int(sx),
                "end_x": int(ex),
                "hi": float(hi),
                "lo": float(lo),
                "hi_day": int(hd),
                "lo_day": int(ld),
            }
        )

    all_rows: list[tuple] = []

    for sym, cycles in by_symbol.items():
        for cyc, boxes in cycles.items():
            bears = [r for r in boxes if r["phase"] == "BEAR"]
            bulls = [r for r in boxes if r["phase"] == "BULL"]

            bear_path = _build_paths_for_cycle(bears, sym, "bear") if bears else []

            # Bull 경로는 예측 Bottom에서 시작. Bear 체인 뒤 Bull일 때 Bottom = 마지막 Bear 박스의 (lo_day, lo)
            bull_start_val = None
            bottom_day, bottom_lo = None, None
            if bears:
                last_bear = bears[-1]
                bottom_day = int(last_bear["lo_day"])
                bottom_lo = float(last_bear["lo"])
                bull_start_val = bottom_lo
            elif bulls:
                bull_start_val = float(bulls[0]["lo"])

            bull_path = []
            if bulls:
                bull_path = _build_paths_for_cycle(bulls, sym, "bull", start_val=bull_start_val)
                # Bull 경로는 예측 Bottom에서 시작
                # 1) Bear 체인 뒤: Bottom = 마지막 Bear 박스 (lo_day, lo)
                # 2) Bull만 있을 때: Bottom = coin_prediction_peaks의 BOTTOM
                if bull_path:
                    first_day = bull_path[0][2]
                    use_bottom_day, use_bottom_lo = bottom_day, bottom_lo
                    cid_raw = boxes[0]["coin_id"]
                    try:
                        cid_key = int(cid_raw) if cid_raw is not None else 0
                    except (ValueError, TypeError):
                        cid_key = str(cid_raw) if cid_raw is not None else ""
                    if use_bottom_day is None and (cid_key, cyc) in bottom_by_coin_cycle:
                        use_bottom_day, use_bottom_lo = bottom_by_coin_cycle[(cid_key, cyc)]
                    if use_bottom_day is not None and use_bottom_lo is not None and first_day > use_bottom_day:
                        bull_path = [(sym, "bull", use_bottom_day, use_bottom_lo)] + bull_path

            for scenario, path in (("bear", bear_path), ("bull", bull_path)):
                if not path:
                    continue
                day_values = [d for _, _, d, _ in path]
                start_x = min(day_values)
                end_x = max(day_values)
                coin_id = boxes[0]["coin_id"]
                for _, _, day, val in path:
                    all_rows.append(
                        (
                            coin_id,
                            sym,
                            cyc,
                            scenario,
                            start_x,
                            end_x,
                            int(day),
                            float(val),
                        )
                    )

    if all_rows:
        cur.executemany(
            """
            INSERT INTO coin_prediction_paths
              (coin_id, symbol, cycle_number, scenario, start_x, end_x, day_x, value)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            all_rows,
        )
    conn.commit()
