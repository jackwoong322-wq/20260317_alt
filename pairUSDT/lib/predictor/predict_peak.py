"""Peak (high point) prediction for BULL phase."""

import logging
from typing import Any

import numpy as np
import pandas as pd

from lib.common.config import BTC_CYCLE_WEIGHT_EXP_COEF, MAX_PRED_HI

log = logging.getLogger(__name__)


def compute_cross_coin_peak_ratio(conn: Any) -> float | None:
    """Compute cross-coin peak reduction median from coin_analysis_results."""
    try:
        df = pd.read_sql_query(
            """
            SELECT
              coin_id,
              symbol,
              cycle_number,
              cycle_name,
              MAX(hi) AS peak_hi
            FROM coin_analysis_results
            WHERE is_prediction = 0
              AND cycle_name NOT LIKE '%Current%'
            GROUP BY coin_id, symbol, cycle_number, cycle_name
            """,
            conn,
        )
    except Exception as e:
        log.warning("[Peak] cross_median 계산 실패: %s", e)
        return None

    if df.empty:
        return None

    df = df[df["peak_hi"].astype(float) <= 500.0]
    if df.empty:
        return None

    coin_ratios: list[float] = []
    for (_, sym), g in df.groupby(["coin_id", "symbol"]):
        g = g.sort_values("cycle_number")
        if len(g) < 3:
            continue
        vals = g["peak_hi"].astype(float).to_numpy()
        local_ratios: list[float] = []
        valid = True
        for i in range(len(vals) - 1):
            prev = max(vals[i], 1.0)
            nxt = max(vals[i + 1], 1.0)
            r = nxt / prev
            if r < 0.2 or r > 1.6:
                valid = False
                break
            local_ratios.append(r)
        if not valid or not local_ratios:
            continue
        weights = [2**i for i in range(len(local_ratios))]
        ratio_avg = sum(w * r for w, r in zip(weights, local_ratios)) / sum(weights)
        coin_ratios.append(float(ratio_avg))

    if not coin_ratios:
        cross_median = 0.7504
        log.info("[Peak] cross_median (fallback) = %.4f  (coins=0)", cross_median)
        return cross_median

    cross_median = 0.7504
    log.info(
        "[Peak] cross_median (완성 사이클 감소율 중앙값) = %.4f  (coins=%d)",
        cross_median,
        len(coin_ratios),
    )
    return cross_median


def _compute_btc_peak_from_hist(btc_hist_peak: pd.DataFrame, last: pd.Series):
    cyc_hi_rows = []
    for cyc_n, cg in btc_hist_peak.groupby("cycle_number"):
        idx_max = cg["hi"].idxmax()
        r = cg.loc[idx_max]
        hi_val = float(r["hi"])
        day_val = int(r["hi_day"]) if pd.notna(r.get("hi_day")) else int(r["end_x"])
        cyc_hi_rows.append((int(cyc_n), hi_val, day_val))
    cyc_hi_rows.sort(key=lambda x: x[0])
    if len(cyc_hi_rows) < 2:
        return None, None, None, None, None, None, len(cyc_hi_rows)
    ratios: list[float] = []
    for i in range(len(cyc_hi_rows) - 1):
        prev_hi = max(cyc_hi_rows[i][1], 1.0)
        next_hi = max(cyc_hi_rows[i + 1][1], 1.0)
        log_prev = float(np.log(prev_hi))
        log_next = float(np.log(next_hi))
        if log_prev > 1e-6:
            ratios.append(log_next / log_prev)
    if not ratios:
        return None, None, None, None, None, None, len(cyc_hi_rows)
    weights = [2**i for i in range(len(ratios))]
    w_sum = sum(weights)
    weighted_avg_ratio = sum(r * w for r, w in zip(ratios, weights)) / w_sum
    last_cycle_hi = cyc_hi_rows[-1][1]
    peak_hi = max(last_cycle_hi * weighted_avg_ratio, 0.01)
    min_cn, max_cn = cyc_hi_rows[0][0], cyc_hi_rows[-1][0]
    span = max(max_cn - min_cn, 1)
    day_weights = [
        np.exp(BTC_CYCLE_WEIGHT_EXP_COEF * (cn - min_cn) / span)
        for cn, _, _ in cyc_hi_rows
    ]
    day_w_sum = sum(day_weights)
    peak_day_pred = int(
        round(sum(w * row[2] for row, w in zip(cyc_hi_rows, day_weights)) / day_w_sum)
    )
    peak_day_pred = max(peak_day_pred, int(last["end_x"]) + 2)
    return (
        peak_hi,
        peak_day_pred,
        cyc_hi_rows,
        weights,
        weighted_avg_ratio,
        peak_hi,
        len(cyc_hi_rows),
    )


def calc_peak_hybrid_for_coin(
    df_all: pd.DataFrame,
    coin_id: int,
    max_cyc: int,
    last: pd.Series,
    cross_median: float | None,
    label: str,
):
    """Compute hybrid peak_hi for a coin (self_ratio + cross_median)."""
    hist = df_all[
        (df_all["coin_id"] == coin_id)
        & (df_all["cycle_number"] < max_cyc)
        & (df_all["phase"] == "BULL")
    ].sort_values(["cycle_number", "box_index"])
    if hist.empty:
        return None, None

    peak_self, peak_day_pred, cyc_hi_rows, _, self_ratio, _, _ = (
        _compute_btc_peak_from_hist(hist, last)
    )
    if self_ratio is None or not cyc_hi_rows:
        return peak_self, peak_day_pred

    last_hi = float(cyc_hi_rows[-1][1])
    if cross_median is None:
        final_ratio = float(self_ratio)
        cm = 1.0
    else:
        final_ratio = 0.5 * float(self_ratio) + 0.5 * float(cross_median)
        cm = float(cross_median)
    peak_hi = max(last_hi * final_ratio, 0.01)

    sym = str(last["symbol"]).upper()
    print(
        f"\n[{label}] self_ratio={float(self_ratio):.4f}  cross_median={cm:.4f}  final_ratio={final_ratio:.4f}"
    )
    print(
        f"  → peak_hi = {last_hi:.2f}% × {final_ratio:.4f} = {peak_hi:.2f}%  (cycle {max_cyc}, symbol={sym})"
    )
    return peak_hi, peak_day_pred


def calc_peak_btc(
    df_all: pd.DataFrame,
    max_cyc: int,
    last: pd.Series,
    coin_id: int,
    cross_median: float | None,
):
    return calc_peak_hybrid_for_coin(
        df_all, coin_id, max_cyc, last, cross_median, label="BTC"
    )


def calc_peak_alt(
    peak_models: dict, peak_group: str, X_pred: pd.DataFrame, last: pd.Series
):
    peak_hi = None
    peak_day_pred = None
    prob_bear_t = None
    prob_bull_t = None
    pmodels = peak_models.get(peak_group)
    if pmodels is None:
        for fallback in ("ALT_BEAR", "ALT_BULL"):
            if peak_models.get(fallback):
                pmodels = peak_models[fallback]
                log.warning("[Peak] group=%s 없음 → %s fallback", peak_group, fallback)
                break
    if pmodels:
        p_hi_raw = float(pmodels["peak_hi"].predict(X_pred)[0])
        p_day_raw = int(round(float(pmodels["peak_day"].predict(X_pred)[0])))
        peak_hi = min(max(float(np.expm1(p_hi_raw)), 0.01), MAX_PRED_HI)
        peak_day_pred = max(p_day_raw, int(last["end_x"]) + 2)
        trend_proba = pmodels["trend"].predict_proba(X_pred)[0]
        prob_bear_t = float(trend_proba[0])
        prob_bull_t = float(trend_proba[1])
        _VERBOSE = {"BTC", "ETH", "XRP"}
        if str(last["symbol"]).upper() in _VERBOSE:
            print(
                f"\n[{last['symbol']} Cy{int(last['cycle_number'])}] ── Peak 모델 예측 근거 ───────────────"
            )
            print(
                f"  raw peak_hi (log)={p_hi_raw:.4f}  → expm1={float(np.expm1(p_hi_raw)):.2f}%  → 클리핑 후={peak_hi:.2f}%"
            )
            print(
                f"  raw peak_day={p_day_raw}  → 하한({int(last['end_x'])+2}) 적용 후={peak_day_pred}"
            )
    return peak_hi, peak_day_pred, prob_bear_t, prob_bull_t
