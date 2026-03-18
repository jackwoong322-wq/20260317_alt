"""
predict_box_bear_chain.py
Bear 체인 예측 전담 모듈.

[진입점] run_bear_chain() — Bear 체인 전체 실행, (pred_rows, path_rows) 반환
  1단계: 박스 전부 생성 (run_bear_chain_step 반복 → row만 수집, 경로용 스펙 수집)
  2단계: 수집한 박스 스펙으로 경로 한 번에 생성 (build_bear_box_day_points 반복)
  └ run_bear_chain_step() — 박스 한 개만 생성 (row + 경로용 스펙 반환, path는 생성 안 함)
       ├ prepare_step_features()
       ├ compute_step_box_bounds()
       ├ build_step_row()  — DB용 행만 생성
       └ log_step_if_verbose()
"""

import numpy as np

from .predict_box_bear import clamp_bear_box, _compute_bear_chain_lo_hi_days, _safe_div_pct, _make_bear_box_db_row, build_bear_box_day_points, predict_bear_box    

# ────────────────────────────────────────────────────────────────
# 스텝용 피처 준비
# ────────────────────────────────────────────────────────────────
def prepare_step_features(
    bear_feat,
    current_chain_idx,
    chain_i,
    bottom_day,
    bottom_lo,
    chain_day,
    chain_val,
    avg_cycle_days,
):
    feat = bear_feat.copy()
    feat["is_bull"]    = 0
    feat["box_index"]  = current_chain_idx

    feat_day = bottom_day if (chain_i == 0 and bottom_day is not None) else chain_day
    feat["cycle_progress_ratio"] = feat_day / avg_cycle_days if avg_cycle_days else 0.0

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
    last,
    max_bear_chain,
    max_pred_hi,
    max_pred_lo,
    override_start_x,
    override_start_x_value,
    start_lo,
):
    _, _, b_hi_chg_pct, b_lo_chg_pct, b_dur = pred

    b_hi = min(max(prev_box_lo * (1.0 + b_hi_chg_pct / 100.0), 0.01), max_pred_hi)
    b_lo = (
        min(max(float(override_start_x_value), 0.01), max_pred_lo)
        if override_start_x_value is not None
        else min(max(prev_box_hi * (1.0 + b_lo_chg_pct / 100.0), 0.01), max_pred_lo)
    )

    b_start = override_start_x if override_start_x is not None else chain_day + 1
    b_end   = min(b_start + b_dur - 1, bottom_day)
    if chain_i == max_bear_chain - 1:
        b_end = bottom_day
    b_dur = b_end - b_start + 1
    if b_dur < 1:
        return None

    resolved_start_lo = (
        float(override_start_x_value) if override_start_x_value is not None
        else start_lo if start_lo is not None
        else float(last["lo"]) if last.get("lo") is not None and np.isfinite(last["lo"])
        else chain_val
    )

    target_lo_max = (
        resolved_start_lo - (resolved_start_lo - bottom_lo) * (chain_i + 1) / max_bear_chain
        if bottom_lo is not None and b_end != bottom_day
        else None
    )

    # b_hi, b_lo = clamp_bear_box(
    #     b_hi, b_lo, b_end, bottom_day, bottom_lo,
    #     prev_box_hi, prev_box_lo,
    #     chain_i=chain_i,
    #     target_lo_max=target_lo_max,
    # )

    b_lo_day, b_hi_day = _compute_bear_chain_lo_hi_days(b_start, b_end, b_dur, chain_day)
    b_range  = _safe_div_pct(b_hi, b_lo) if b_lo > 0 else 0.0

    return (
        b_start, b_end,
        b_hi, b_lo,
        b_hi_day, b_lo_day,
        b_dur,
        b_range,
        b_hi_chg_pct, b_lo_chg_pct,
        b_lo - 100.0,   # b_gain
    )


# ────────────────────────────────────────────────────────────────
# 스텝 출력: DB용 행 + 일별 경로 포인트
# ────────────────────────────────────────────────────────────────
# ────────────────────────────────────────────────────────────────
# 스텝 출력: DB용 행만 생성 (경로는 박스 전부 생성 후 한 번에 생성)
# ────────────────────────────────────────────────────────────────
def build_step_row(
    coin_id, last, max_cyc,
    current_chain_idx,
    chain_i,
    chain_day, chain_val,
    b_start, b_end,
    b_hi, b_lo,
    b_hi_day, b_lo_day,
    b_dur, b_range,
    b_hi_chg_pct, b_lo_chg_pct,
    b_gain,
):
    """박스 하나에 대한 DB용 행만 반환. 경로는 run_bear_chain 2단계에서 한 번에 생성."""
    row = _make_bear_box_db_row(
        coin_id, last, max_cyc, current_chain_idx,
        b_start, b_end,
        b_hi, b_lo,
        b_hi_day, b_lo_day,
        b_dur, b_range,
        _safe_div_pct(b_hi, chain_val),
        _safe_div_pct(b_lo, b_hi),
        b_gain,
    )
    return row


# ────────────────────────────────────────────────────────────────
# 디버그 로그 (BTC/ETH/XRP만)
# ────────────────────────────────────────────────────────────────
def log_step_if_verbose(
    last, current_chain_idx, chain_i,
    b_start, b_end, b_hi, b_lo, b_dur, b_range,
):
    if str(last["symbol"]).upper() not in {"BTC", "ETH", "XRP"}:
        return
    print(
        f"  ▶ PRED_BEAR_CHAIN  box#{current_chain_idx} (chain_i={chain_i})"
        f"  day {b_start}~{b_end} ({b_dur}d)"
        f"  hi={b_hi:.2f}%  lo={b_lo:.2f}%  range={b_range:.1f}%"
    )


# ────────────────────────────────────────────────────────────────
# 박스 한 개 스텝 실행
# ────────────────────────────────────────────────────────────────
def run_bear_chain_step(
    coin_id, last, max_cyc,
    next_box_idx,
    chain_i,
    chain_day, chain_val,
    prev_box_hi, prev_box_lo,
    bear_feat,
    bottom_day, bottom_lo,
    group_models, avg_cycle_days,
    max_bear_chain, max_pred_hi, max_pred_lo,
    reg_feat_cols,
    override_start_x,
    override_start_x_value,
    start_lo,
):
    current_chain_idx = next_box_idx + chain_i

    # 첫 스텝에서 시작값 오버라이드가 있으면 해당 값을 사용
    step_chain_val = override_start_x_value if (chain_i == 0 and override_start_x_value is not None) else chain_val

    feat = prepare_step_features(
        bear_feat, current_chain_idx, chain_i,
        bottom_day, bottom_lo,
        chain_day, chain_val,
        avg_cycle_days,
    )

    pred = predict_bear_box(group_models, feat, avg_cycle_days, reg_feat_cols)

    bounds = compute_step_box_bounds(
        pred, chain_i,
        chain_day, step_chain_val,
        prev_box_hi, prev_box_lo,
        bottom_day, bottom_lo,
        last,
        max_bear_chain, max_pred_hi, max_pred_lo,
        override_start_x, override_start_x_value, start_lo,
    )
    if bounds is None:
        return None

    b_start, b_end, b_hi, b_lo, b_hi_day, b_lo_day, b_dur, b_range, b_hi_chg_pct, b_lo_chg_pct, b_gain = bounds

    row = build_step_row(
        coin_id, last, max_cyc,
        current_chain_idx, chain_i,
        chain_day, step_chain_val,
        b_start, b_end,
        b_hi, b_lo,
        b_hi_day, b_lo_day,
        b_dur, b_range,
        b_hi_chg_pct, b_lo_chg_pct,
        b_gain,
    )
    log_step_if_verbose(last, current_chain_idx, chain_i, b_start, b_end, b_hi, b_lo, b_dur, b_range)
    # 경로용 스펙 (박스 전부 생성 후 한 번에 경로 생성할 때 사용)
    path_spec = (
        b_start, b_end, b_hi, b_lo,
        b_hi_day, b_lo_day,
        chain_day, step_chain_val, chain_i,
    )
    return row, path_spec, b_end, b_lo, b_hi, b_lo


# ────────────────────────────────────────────────────────────────
# 진입점: Bear 체인 전체 실행
# ────────────────────────────────────────────────────────────────
def run_bear_chain(
    coin_id, last, max_cyc,
    next_box_idx,
    bear_chain_day, bear_chain_val,
    bear_feat,
    prev_box_hi, prev_box_lo,
    bottom_day, bottom_lo,
    group_models, avg_cycle_days,
    override_start_x=None,
    override_start_x_value=None,
    reg_feat_cols=None,
    max_bear_chain=5,
    start_lo=None,
    max_pred_hi=500.0,
    max_pred_lo=100.0,
):
    chain_day    = bear_chain_day
    chain_val    = bear_chain_val
    box_hi       = prev_box_hi
    box_lo       = prev_box_lo
    pred_rows    = []
    path_specs   = []  # 박스 전부 생성 후 한 번에 경로 생성할 스펙 목록

    # 1단계: 박스 전부 생성 (row 수집 + 경로용 스펙 수집)
    for chain_i in range(max_bear_chain):
        result = run_bear_chain_step(
            coin_id, last, max_cyc,
            next_box_idx,
            chain_i,
            chain_day, chain_val,
            box_hi, box_lo,
            bear_feat,
            bottom_day, bottom_lo,
            group_models, avg_cycle_days,
            max_bear_chain, max_pred_hi, max_pred_lo,
            reg_feat_cols or [],
            override_start_x if chain_i == 0 else None,
            override_start_x_value if chain_i == 0 else None,
            start_lo,
        )
        if result is None:
            break

        row, path_spec, next_day, next_val, next_hi, next_lo = result
        pred_rows.append(row)
        path_specs.append(path_spec)

        chain_day = next_day
        chain_val = next_val
        box_hi    = next_hi
        box_lo    = next_lo

    # 2단계: 수집한 박스 스펙으로 경로 한 번에 생성
    path_rows = []
    for i, spec in enumerate(path_specs):
        b_start, b_end, b_hi, b_lo, b_hi_day, b_lo_day, s_chain_day, s_chain_val, s_chain_i = spec
        next_lo = path_specs[i + 1][3] if i + 1 < len(path_specs) else None  # 다음 박스 저점
        path = build_bear_box_day_points(
            coin_id, last, max_cyc,
            b_start, b_end,
            b_hi, b_lo,
            b_lo_day, b_hi_day,
            s_chain_day, s_chain_val,
            s_chain_i,
            next_box_lo=next_lo,
            bottom_day=bottom_day,
            bottom_lo=bottom_lo,
        )
        path_rows.extend(path)

    return pred_rows, path_rows