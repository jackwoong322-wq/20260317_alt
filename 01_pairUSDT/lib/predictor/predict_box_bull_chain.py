"""
predict_box_bull_chain.py
Bull 체인 예측 전담 모듈.

[진입점] run_bull_chain() — Bull 체인 전체 실행, (pred_rows, path_rows) 반환
  1단계: 박스 전부 생성 (run_bull_chain_step 반복 → row만 수집, 경로용 스펙 수집)
  2단계: 수집한 박스 스펙으로 경로 한 번에 생성 (build_bull_box_day_points 반복)
  └ run_bull_chain_step() — 박스 한 개만 생성 (row + 경로용 스펙 반환, path는 생성 안 함)
       ├ prepare_step_features()
       ├ compute_step_box_bounds()
       ├ build_step_row()
       └ log_step_if_verbose()
"""

import numpy as np

from lib.common.utils import _safe_div_pct

from .predict_box_bull import (
    build_bull_box_day_points,
    predict_bull_box,
    _make_bull_row,
)


# ────────────────────────────────────────────────────────────────
# 스텝용 피처 준비
# ────────────────────────────────────────────────────────────────
def prepare_step_features(
    bull_feat,
    current_chain_idx,
    chain_i,
    bottom_day,
    bottom_lo,
    peak_day_pred,
    chain_day,
    chain_val,
    avg_cycle_days,
):
    feat = bull_feat.copy()
    feat["is_bull"] = 1
    feat["box_index"] = current_chain_idx

    feat_day = bottom_day if (chain_i == 0 and bottom_day is not None) else chain_day
    total_span = max(1, peak_day_pred - bottom_day) if peak_day_pred is not None else 1
    feat["cycle_progress_ratio"] = (feat_day - bottom_day) / total_span if total_span else 0.0
    feat["cycle_progress_ratio"] = max(0.0, min(1.0, feat["cycle_progress_ratio"]))

    return feat


# ────────────────────────────────────────────────────────────────
# 스텝 박스 경계(hi/lo/날짜) 계산
# ────────────────────────────────────────────────────────────────
def compute_step_box_bounds(
    pred,
    chain_i,
    chain_day,
    chain_val,
    prev_box_hi,
    prev_box_lo,
    bottom_day,
    bottom_lo,
    peak_day_pred,
    last,
    max_bull_chain,
    max_pred_hi,
    max_pred_lo,
):
    _, _, b_hi_chg_pct, b_lo_chg_pct, b_dur = pred

    # Bull: prev_lo → 이 박스 고점(hi), 고점 → 이 박스 저점(lo)
    bull_hi = min(max(prev_box_lo * (1.0 + b_hi_chg_pct / 100.0), 0.01), max_pred_hi)
    bull_lo = min(max(bull_hi * (1.0 + b_lo_chg_pct / 100.0), 0.01), max_pred_lo)
    if bull_hi < bull_lo:
        bull_lo = max(0.01, bull_hi * 0.98)

    b_start = chain_day + 1
    b_end = min(b_start + b_dur - 1, peak_day_pred)
    if chain_i == max_bull_chain - 1:
        b_end = peak_day_pred
    b_dur = b_end - b_start + 1
    if b_dur < 1 or b_start > peak_day_pred:
        return None

    pred_dur_b = b_dur
    hi_day_bull = b_start + pred_dur_b // 4
    lo_day_bull = b_start + pred_dur_b * 3 // 4
    range_bull = _safe_div_pct(bull_hi, bull_lo) if bull_lo > 0 else 0.0

    return (
        b_start,
        b_end,
        bull_hi,
        bull_lo,
        hi_day_bull,
        lo_day_bull,
        pred_dur_b,
        range_bull,
        b_hi_chg_pct,
        b_lo_chg_pct,
    )


# ────────────────────────────────────────────────────────────────
# 스텝 출력: DB용 행만 생성
# ────────────────────────────────────────────────────────────────
def build_step_row(
    coin_id,
    last,
    max_cyc,
    current_chain_idx,
    chain_i,
    chain_day,
    chain_val,
    b_start,
    b_end,
    bull_hi,
    bull_lo,
    hi_day_bull,
    lo_day_bull,
    pred_dur_b,
    range_bull,
    b_hi_chg_pct,
    b_lo_chg_pct,
    ref_lo,
    cycle_lo,
):
    """박스 하나에 대한 DB용 행만 반환. 경로는 run_bull_chain 2단계에서 한 번에 생성."""
    hi_change_bull = _safe_div_pct(bull_hi, ref_lo)
    lo_change_bull = _safe_div_pct(bull_lo, bull_hi)
    gain_bull = _safe_div_pct(bull_hi, cycle_lo) if cycle_lo > 0 else 0.0
    row = _make_bull_row(
        coin_id,
        last,
        max_cyc,
        current_chain_idx,
        b_start,
        b_end,
        bull_hi,
        bull_lo,
        hi_day_bull,
        lo_day_bull,
        pred_dur_b,
        range_bull,
        hi_change_bull,
        lo_change_bull,
        gain_bull,
    )
    return row


# ────────────────────────────────────────────────────────────────
# 디버그 로그 (BTC/ETH/XRP만)
# ────────────────────────────────────────────────────────────────
def log_step_if_verbose(
    last,
    current_chain_idx,
    chain_i,
    b_start,
    b_end,
    bull_hi,
    bull_lo,
    pred_dur_b,
    range_bull,
):
    if str(last["symbol"]).upper() not in {"BTC", "ETH", "XRP"}:
        return
    print(
        f"  ▶ PRED_BULL_CHAIN  box#{current_chain_idx} (chain_i={chain_i})"
        f"  day {b_start}~{b_end} ({pred_dur_b}d)"
        f"  hi={bull_hi:.2f}%  lo={bull_lo:.2f}%  range={range_bull:.1f}%"
    )


# ────────────────────────────────────────────────────────────────
# 박스 한 개 스텝 실행
# ────────────────────────────────────────────────────────────────
def run_bull_chain_step(
    coin_id,
    last,
    max_cyc,
    next_box_idx,
    chain_i,
    chain_day,
    chain_val,
    prev_box_hi,
    prev_box_lo,
    bull_feat,
    bottom_day,
    bottom_lo,
    peak_day_pred,
    group_models,
    avg_cycle_days,
    max_bull_chain,
    max_pred_hi,
    max_pred_lo,
    reg_feat_cols,
    ref_lo,
    cycle_lo,
):
    current_chain_idx = next_box_idx + chain_i

    feat = prepare_step_features(
        bull_feat,
        current_chain_idx,
        chain_i,
        bottom_day,
        bottom_lo,
        peak_day_pred,
        chain_day,
        chain_val,
        avg_cycle_days,
    )

    pred = predict_bull_box(group_models, feat, avg_cycle_days, reg_feat_cols)

    bounds = compute_step_box_bounds(
        pred,
        chain_i,
        chain_day,
        chain_val,
        prev_box_hi,
        prev_box_lo,
        bottom_day,
        bottom_lo,
        peak_day_pred,
        last,
        max_bull_chain,
        max_pred_hi,
        max_pred_lo,
    )
    if bounds is None:
        return None

    (b_start, b_end, bull_hi, bull_lo, hi_day_bull, lo_day_bull, pred_dur_b, range_bull, b_hi_chg_pct, b_lo_chg_pct) = bounds

    row = build_step_row(
        coin_id,
        last,
        max_cyc,
        current_chain_idx,
        chain_i,
        chain_day,
        chain_val,
        b_start,
        b_end,
        bull_hi,
        bull_lo,
        hi_day_bull,
        lo_day_bull,
        pred_dur_b,
        range_bull,
        b_hi_chg_pct,
        b_lo_chg_pct,
        ref_lo,
        cycle_lo,
    )
    log_step_if_verbose(last, current_chain_idx, chain_i, b_start, b_end, bull_hi, bull_lo, pred_dur_b, range_bull)

    path_spec = (
        b_start,
        b_end,
        bull_hi,
        bull_lo,
        hi_day_bull,
        lo_day_bull,
        chain_day,
        chain_val,
        chain_i,
    )
    return row, path_spec, b_end, bull_lo, bull_hi, bull_lo


# ────────────────────────────────────────────────────────────────
# 진입점: Bull 체인 전체 실행
# ────────────────────────────────────────────────────────────────
def run_bull_chain(
    coin_id,
    last,
    max_cyc,
    next_box_idx,
    bull_chain_day,
    bull_chain_val,
    bull_feat,
    prev_box_hi,
    prev_box_lo,
    bottom_day,
    bottom_lo,
    peak_day_pred,
    group_models,
    avg_cycle_days,
    ref_lo,
    cycle_lo,
    reg_feat_cols=None,
    max_bull_chain=5,
    max_pred_hi=500.0,
    max_pred_lo=100.0,
):
    chain_day = bull_chain_day
    chain_val = bull_chain_val
    box_hi = prev_box_hi
    box_lo = prev_box_lo
    pred_rows = []
    path_specs = []

    for chain_i in range(max_bull_chain):
        if chain_day >= peak_day_pred:
            break
        result = run_bull_chain_step(
            coin_id,
            last,
            max_cyc,
            next_box_idx,
            chain_i,
            chain_day,
            chain_val,
            box_hi,
            box_lo,
            bull_feat,
            bottom_day,
            bottom_lo,
            peak_day_pred,
            group_models,
            avg_cycle_days,
            max_bull_chain,
            max_pred_hi,
            max_pred_lo,
            reg_feat_cols or [],
            ref_lo,
            cycle_lo,
        )
        if result is None:
            break

        row, path_spec, next_day, next_val, next_hi, next_lo = result
        pred_rows.append(row)
        path_specs.append(path_spec)

        chain_day = next_day
        chain_val = next_val
        box_hi = next_hi
        box_lo = next_lo

    path_rows = []
    for i, spec in enumerate(path_specs):
        b_start, b_end, bull_hi, bull_lo, hi_day_bull, lo_day_bull, s_chain_day, s_chain_val, s_chain_i = spec
        next_hi = path_specs[i + 1][2] if i + 1 < len(path_specs) else None
        path = build_bull_box_day_points(
            coin_id,
            last,
            max_cyc,
            b_start,
            b_end,
            bull_hi,
            bull_lo,
            hi_day_bull,
            lo_day_bull,
            s_chain_day,
            s_chain_val,
            s_chain_i,
            next_box_hi=next_hi,
        )
        path_rows.extend(path)

    return pred_rows, path_rows
