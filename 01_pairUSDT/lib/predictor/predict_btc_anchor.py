"""BTC anchor calculation for prediction context."""

import pandas as pd


def calc_btc_anchor(df_all: pd.DataFrame, cycle_stats: dict, coin_stats: dict):
    """Compute BTC anchor state for alt-coin prediction context."""
    btc_anchor = None
    btc_rows = df_all[df_all["symbol"].str.upper() == "BTC"]
    if not btc_rows.empty:
        btc_coin_id = btc_rows["coin_id"].iloc[0]
        btc_cycle_num = int(btc_rows["cycle_number"].max())

        btc_grp = (
            df_all[(df_all["coin_id"] == btc_coin_id) & (df_all["cycle_number"] == btc_cycle_num)]
            .sort_values("box_index")
            .reset_index(drop=True)
        )
        if not btc_grp.empty:
            btc_cstat = cycle_stats[(btc_coin_id, btc_cycle_num)]
            btc_cinfo = coin_stats.get(btc_coin_id, {})

            btc_total_days = btc_cstat["total_days"]
            btc_avg_cycle_days = btc_cinfo.get("avg_cycle_days", btc_total_days)

            btc_active = btc_grp[btc_grp["is_completed"] == 0]
            btc_last = btc_active.iloc[-1] if not btc_active.empty else btc_grp.iloc[-1]

            btc_cycle_progress_ratio = (
                btc_last["end_x"] / btc_avg_cycle_days if btc_avg_cycle_days else 0.0
            )

            btc_lower_low = False
            if len(btc_grp) >= 2:
                btc_prev = btc_grp.iloc[-2]
                btc_lower_low = btc_last["lo"] < btc_prev["lo"]

            btc_gain = btc_last.get("gain_pct", 0.0) or 0.0
            btc_lo_chg = btc_last.get("lo_change_pct", 0.0) or 0.0
            btc_slope_down = btc_gain < -10 or btc_lo_chg < -5

            btc_anchor = {
                "coin_id": btc_coin_id,
                "cycle_number": btc_cycle_num,
                "cycle_progress_ratio": float(btc_cycle_progress_ratio),
                "lower_low": bool(btc_lower_low),
                "slope_down": bool(btc_slope_down),
                "gain_pct": float(btc_gain),
                "lo_change_pct": float(btc_lo_chg),
            }
    return btc_anchor
