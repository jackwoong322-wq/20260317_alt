"""BULL/BEAR phase judgment logic."""

import pandas as pd


def _check_lower_low_slope(last: pd.Series, grp: pd.DataFrame):
    lower_low = False
    _prev_lo_val = None
    if len(grp) >= 2:
        prev = grp.iloc[-2]
        _prev_lo_val = float(prev["lo"])
        lower_low = last["lo"] < prev["lo"]

    _gain_pct_val = float(last.get("gain_pct", 0.0) or 0.0)
    _lo_chg_pct_val = float(last.get("lo_change_pct", 0.0) or 0.0)
    slope_down = _gain_pct_val < -10 or _lo_chg_pct_val < -5
    return lower_low, _prev_lo_val, slope_down, _gain_pct_val, _lo_chg_pct_val


def _check_force_bear(last, grp, bottom_day, bottom_lo, lower_low, slope_down, btc_anchor):
    actual_lo = float(grp["lo"].min()) if not grp.empty else float("inf")
    actual_lo_idx = grp["lo"].idxmin() if not grp.empty else None
    actual_lo_day = int(grp.loc[actual_lo_idx, "end_x"]) if actual_lo_idx is not None else 0

    force_bear = False
    _force_reason = []

    if bottom_day is not None:
        not_at_bottom = int(last["end_x"]) < bottom_day
        if not_at_bottom:
            force_bear = True
            _force_reason.append("before_bottom")
        else:
            if actual_lo <= (bottom_lo or 0):
                if lower_low:
                    force_bear = True
                    _force_reason.append("lower_low")
                if slope_down:
                    force_bear = True
                    _force_reason.append("slope_down")
            else:
                if lower_low:
                    force_bear = True
                    _force_reason.append("lower_low_no_bottom")
                if slope_down:
                    force_bear = True
                    _force_reason.append("slope_down_no_bottom")
    else:
        if lower_low:
            force_bear = True
            _force_reason.append("lower_low")
        if slope_down:
            force_bear = True
            _force_reason.append("slope_down")

    _btc_anchor_triggered = False
    if not force_bear and btc_anchor is not None and str(last["symbol"]).upper() != "BTC":
        if btc_anchor["slope_down"] and btc_anchor["cycle_progress_ratio"] > 0.6:
            force_bear = True
            _btc_anchor_triggered = True
            _force_reason.append("btc_anchor")

    return force_bear, _force_reason, _btc_anchor_triggered


def judge_bull_bear(
    last: pd.Series,
    grp: pd.DataFrame,
    max_cyc: int,
    prob_bull: float,
    prob_bear: float,
    bottom_day,
    btc_anchor,
    bottom_lo=None,
):
    """Judge BULL vs BEAR; returns (pred_is_bull, lower_low, prev_lo_val, slope_down, ...)."""
    lower_low, _prev_lo_val, slope_down, _gain_pct_val, _lo_chg_pct_val = _check_lower_low_slope(last, grp)
    force_bear, _force_reason, _btc_anchor_triggered = _check_force_bear(
        last, grp, bottom_day, bottom_lo, lower_low, slope_down, btc_anchor
    )

    pred_is_bull = 1 if prob_bull >= prob_bear else 0
    if force_bear:
        pred_is_bull = 0

    _VERBOSE = {"BTC", "ETH", "XRP"}
    if str(last["symbol"]).upper() in _VERBOSE:
        _pfx = f"[{last['symbol']} Cy{max_cyc}]"
        print(f"\n{_pfx} ── BULL/BEAR 판정 ───────────────────────────────")
        print(
            f"  phase 확률: P(BULL)={prob_bull:.3f}  P(BEAR)={prob_bear:.3f}"
            f"  → 모델 판정: {'BULL' if (1 if prob_bull >= prob_bear else 0) else 'BEAR'}"
        )
        print(
            f"  lower_low : {lower_low}"
            + (f"  (last.lo={float(last['lo']):.2f}%  prev.lo={_prev_lo_val:.2f}%)" if _prev_lo_val is not None else "")
        )
        print(f"  slope_down: {slope_down}" f"  (gain_pct={_gain_pct_val:.2f}%  lo_change_pct={_lo_chg_pct_val:.2f}%)")
        if _btc_anchor_triggered and btc_anchor is not None:
            print(
                f"  btc_anchor: slope_down={btc_anchor['slope_down']}"
                f"  cycle_progress_ratio={btc_anchor['cycle_progress_ratio']:.3f}"
            )
        print(f"  force_bear: {force_bear}" + (f"  이유={_force_reason}" if _force_reason else "") + f"  최종 판정: {'BULL' if pred_is_bull else 'BEAR'}")

    return (
        pred_is_bull,
        lower_low,
        _prev_lo_val,
        slope_down,
        _gain_pct_val,
        _lo_chg_pct_val,
        force_bear,
        _force_reason,
        _btc_anchor_triggered,
    )
