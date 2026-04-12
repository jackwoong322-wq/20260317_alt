"""Bottom (low point) prediction for BEAR phase."""

import logging

import numpy as np
import pandas as pd

from lib.common.config import BTC_CYCLE_WEIGHT_EXP_COEF, BTC_BOTTOM_CYCLE_INCREASE_PCT, MAX_PRED_LO

log = logging.getLogger(__name__)


def calc_bottom_btc(df_all: pd.DataFrame, max_cyc: int, last: pd.Series):
    """Compute BTC bottom: Cy1 제외 후 사이클별 증가폭 평균으로 다음 사이클 최저점 추정.
    (예: Cy2 7.4% → Cy3 15.9% → Cy4 22.4% → 증가폭 ~7% → 다음 ~29%)"""
    bottom_lo = None
    bottom_day = None
    btc_hist = (
        df_all[(df_all["symbol"].str.upper() == "BTC") & (df_all["cycle_number"] < max_cyc)]
        .sort_values(["cycle_number", "box_index"])
    )
    if not btc_hist.empty:
        cyc_lo_rows = []
        for cyc_n, cg in btc_hist.groupby("cycle_number"):
            idx_min = cg["lo"].idxmin()
            r = cg.loc[idx_min]
            lo_val = float(r["lo"])
            day_val = int(r["lo_day"]) if pd.notna(r.get("lo_day")) else int(r["end_x"])
            cyc_lo_rows.append((int(cyc_n), lo_val, day_val))
        if cyc_lo_rows:
            cyc_nums = [x[0] for x in cyc_lo_rows]
            min_cyc_n, max_cyc_n = min(cyc_nums), max(cyc_nums)
            # Cy1(가장 오래된 사이클) 제외
            rows_excl = [r for r in cyc_lo_rows if r[0] > min_cyc_n]
            if len(rows_excl) >= 2:
                # 사이클별 증가폭 평균 (%p)
                increases = [rows_excl[i + 1][1] - rows_excl[i][1] for i in range(len(rows_excl) - 1)]
                avg_increase = float(np.mean(increases))
                last_lo = rows_excl[-1][1]
                last_day = rows_excl[-1][2]
                bottom_lo = last_lo + avg_increase
                # bottom_day: 마지막 사이클 저점일 가중평균 또는 마지막+일수 추이
                day_increases = [rows_excl[i + 1][2] - rows_excl[i][2] for i in range(len(rows_excl) - 1)]
                avg_day_step = int(round(float(np.mean(day_increases)))) if day_increases else 0
                bottom_day = last_day + max(avg_day_step, 0)
                log.debug(
                    "    [BTC] bottom 증가폭 추정: last_lo=%.2f%% + avg_increase=%.2f%% → %.2f%%",
                    last_lo, avg_increase, bottom_lo,
                )
                print(f"\n[BTC Cy{max_cyc}] ── Bottom 증가폭 추정 (Cy{min_cyc_n} 제외) ──────────────")
                for i, (cn, lv, ld) in enumerate(rows_excl):
                    inc = f"  (+{rows_excl[i][1]-rows_excl[i-1][1]:.1f}%p)" if i > 0 else ""
                    print(f"  Cy{cn:2d}  lo={lv:7.2f}%  day={ld:4d}{inc}")
                print(f"  → 증가폭 평균 = {avg_increase:.2f}%p  → bottom_lo = {last_lo:.2f} + {avg_increase:.2f} = {bottom_lo:.2f}%")
                print(f"  → bottom_day = {bottom_day}")
            elif len(rows_excl) == 1:
                last_lo = rows_excl[0][1]
                last_day = rows_excl[0][2]
                bottom_lo = last_lo + BTC_BOTTOM_CYCLE_INCREASE_PCT
                bottom_day = last_day + 50
                print(f"\n[BTC Cy{max_cyc}] ── Bottom 1개만 있어 기본 증가율 적용 ──────────────")
                print(f"  Cy{rows_excl[0][0]}  lo={last_lo:.2f}%  → bottom_lo = {last_lo:.2f} + {BTC_BOTTOM_CYCLE_INCREASE_PCT} = {bottom_lo:.2f}%")
            else:
                # Cy1만 있거나 1개뿐: 기존 가중평균
                rows_excl = cyc_lo_rows
                span = max(max_cyc_n - min_cyc_n, 1)
                weights = [
                    np.exp(BTC_CYCLE_WEIGHT_EXP_COEF * (cn - min_cyc_n) / span)
                    for cn, _, _ in cyc_lo_rows
                ]
                w_sum = sum(weights)
                bottom_lo = sum(w * v for (_, v, _), w in zip(cyc_lo_rows, weights)) / w_sum
                bottom_day = int(round(sum(w * row[2] for row, w in zip(cyc_lo_rows, weights)) / w_sum))
                print(f"\n[BTC Cy{max_cyc}] ── Bottom 가중평균 (Cy1 제외 후 데이터 부족) ──────────────")
                for (cn, lv, ld), w in zip(cyc_lo_rows, weights):
                    print(f"  Cy{cn:2d}  lo={lv:7.2f}%  day={ld:4d}  weight={w:.3f}")
                print(f"  → 가중평균  bottom_lo={bottom_lo:.2f}%  bottom_day={bottom_day}")

            bottom_day = max(bottom_day, int(last["end_x"]) + 2)
            bottom_lo = min(max(bottom_lo, 0.01), MAX_PRED_LO)
    return bottom_lo, bottom_day


def calc_bottom_alt(bottom_models: dict, group_name: str, X_pred: pd.DataFrame, last: pd.Series):
    """Compute ALT bottom from bottom models."""
    bottom_lo = None
    bottom_day = None
    prob_bear_t = None
    prob_bull_t = None
    bmodels = bottom_models.get(group_name)
    if bmodels:
        b_lo_raw = float(bmodels["bottom_lo"].predict(X_pred)[0])
        b_day_raw = int(round(float(bmodels["bottom_day"].predict(X_pred)[0])))
        bottom_lo = min(max(float(np.expm1(b_lo_raw)), 0.01), MAX_PRED_LO)
        bottom_day = max(b_day_raw, int(last["end_x"]) + 2)
        trend_proba = bmodels["trend"].predict_proba(X_pred)[0]
        prob_bear_t, prob_bull_t = float(trend_proba[0]), float(trend_proba[1])
        _VERBOSE = {"BTC", "ETH", "XRP"}
        if str(last["symbol"]).upper() in _VERBOSE:
            print(f"\n[{last['symbol']} Cy{int(last['cycle_number'])}] ── Bottom 모델 예측 근거 ──────────────")
            print(
                f"  raw bottom_lo (log)={b_lo_raw:.4f}  → expm1={float(np.expm1(b_lo_raw)):.2f}%"
                f"  → 클리핑 후={bottom_lo:.2f}%"
            )
            print(f"  raw bottom_day={b_day_raw}  → 하한({int(last['end_x'])+2}) 적용 후={bottom_day}")
    return bottom_lo, bottom_day, prob_bear_t, prob_bull_t
