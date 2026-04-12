"""Feature vector construction for prediction."""

import numpy as np
import pandas as pd

from lib.common.config import BOX_FEATURE_WEIGHTS


def build_feature_vector(
    last: pd.Series,
    coin_id,
    max_cyc: int,
    cycle_stats: dict,
    coin_stats: dict,
    phase_box_stats: dict,
    btc_cycle_max_hi: dict | None = None,
) -> tuple[dict, float]:
    """Build feature dict and avg_cycle_days for prediction."""
    cstat = cycle_stats[(coin_id, max_cyc)]
    cinfo = coin_stats.get(coin_id, {})

    total_days = cstat["total_days"]
    cycle_low_x = cstat["low_x"]
    cycle_low_pos_ratio = cycle_low_x / total_days if total_days else 0.0

    avg_cycle_days = cinfo.get("avg_cycle_days", total_days)
    cycle_progress_ratio = last["end_x"] / avg_cycle_days if avg_cycle_days else 0.0

    mean_lo_prev = cinfo.get("mean_lo", last["lo"])
    min_lo_prev = cinfo.get("min_lo", last["lo"])
    rel_to_prev_cycle_low = (last["lo"] - min_lo_prev) / abs(min_lo_prev) if min_lo_prev else 0.0
    rel_to_prev_support_mean = (last["lo"] - mean_lo_prev) / abs(mean_lo_prev) if mean_lo_prev else 0.0

    phase_label = "BULL" if last["phase"] == "BULL" else "BEAR"
    avg_box_cnt = phase_box_stats.get((coin_id, phase_label), last["box_index"] + 1)
    phase_box_index_ratio = (last["box_index"] + 1) / avg_box_cnt if avg_box_cnt else 0.0

    cycle_min_lo = cstat.get("min_lo") or 1.0
    hi_ratio = last["hi"] / cycle_min_lo if cycle_min_lo > 0 and last.get("hi", 0) > 0 else 1.0
    lo_ratio = last["lo"] / cycle_min_lo if cycle_min_lo > 0 and last.get("lo", 0) > 0 else 1.0
    hi_rel_to_cycle_lo = float(np.log(hi_ratio))
    lo_rel_to_cycle_lo = float(np.log(lo_ratio))

    feat = {
        "norm_range_pct": last["norm_range_pct"],
        "norm_hi_change_pct": last["norm_hi_change_pct"],
        "norm_lo_change_pct": last["norm_lo_change_pct"],
        "norm_gain_pct": last["norm_gain_pct"],
        "norm_duration": last["norm_duration"],
        "hi_rel_to_cycle_lo": hi_rel_to_cycle_lo,
        "lo_rel_to_cycle_lo": lo_rel_to_cycle_lo,
        "coin_rank": int(last["coin_rank"]),
        "is_bull": int(last["phase"] == "BULL"),
        "box_index": int(last["box_index"]),
        "cycle_progress_ratio": float(cycle_progress_ratio),
        "cycle_low_pos_ratio": float(cycle_low_pos_ratio),
        "rel_to_prev_cycle_low": float(rel_to_prev_cycle_low),
        "rel_to_prev_support_mean": float(rel_to_prev_support_mean),
        "phase_box_index_ratio": float(phase_box_index_ratio),
        "phase_avg_box_count": float(avg_box_cnt),
        "btc_prev_peak_ratio": 0.0,
    }
    btc_prev_peak_ratio = 0.0
    if (
        str(last["symbol"]).upper() == "BTC"
        and max_cyc > 1
        and btc_cycle_max_hi
        and (max_cyc - 1) in btc_cycle_max_hi
    ):
        prev_hi = btc_cycle_max_hi[max_cyc - 1]
        if prev_hi and prev_hi > 0 and last.get("hi"):
            btc_prev_peak_ratio = float(last["hi"]) / prev_hi
    feat["btc_prev_peak_ratio"] = float(btc_prev_peak_ratio)
    feat["log_cycle_number"] = float(np.log(max_cyc + 1))
    feat["_cycle_min_lo"] = float(cycle_min_lo)
    for col, w in BOX_FEATURE_WEIGHTS.items():
        if col in feat:
            feat[col] = float(feat[col]) * w
    return feat, float(avg_cycle_days)
