"""
predict_box_bear_chain.py
Bear 체인 예측 전담 모듈.

[A안 개선] 이전 사이클 실측값 기반 체인
  - lo[0]   = _start_lo (현재 실제 저점, 고정)
  - hi[i]   = lo[i] * (1 + ref_bear_ranges[i] / 100)   — 반등폭 (lo→hi)
  - lo[i+1] = hi[i] * (1 + ref_bear_declines[i] / 100) — 하락률 (hi→next_lo)
  - lo[N-1] = bottom_lo (마지막 박스 저점 고정)
  - dur[i]  = total_days / N (균등)
"""

from lib.common.config import MIN_BEAR_DURATION, MAX_PRED_HI, MAX_PRED_LO, BEAR_CHAIN_MAX_RANGE_INIT, BEAR_CHAIN_RANGE_DECAY_RATE

from .predict_box_bear import (
    _compute_bear_chain_lo_hi_days,
    _safe_div_pct,
    _make_bear_box_db_row,
    build_bear_box_day_points,
)


def _log_verbose(last, box_idx, chain_i, b_start, b_end, b_hi, b_lo, b_dur, b_range):
    if str(last["symbol"]).upper() not in {"BTC", "ETH", "XRP"}:
        return
    print(
        f"  ▶ PRED_BEAR_CHAIN  box#{box_idx} (chain_i={chain_i})"
        f"  day {b_start}~{b_end} ({b_dur}d)"
        f"  hi={b_hi:.2f}%  lo={b_lo:.2f}%  range={b_range:.1f}%"
    )


def run_bear_chain(
    coin_id,
    last,
    max_cyc,
    next_box_idx,
    bear_chain_day,
    bear_chain_val,
    bear_feat,
    prev_box_hi,
    prev_box_lo,
    bottom_day,
    bottom_lo,
    group_models,
    avg_cycle_days,
    override_start_x=None,
    override_start_x_value=None,
    reg_feat_cols=None,
    max_bear_chain=5,
    start_lo=None,
    max_pred_hi=MAX_PRED_HI,
    max_pred_lo=MAX_PRED_LO,
    ref_bear_ranges=None,
    ref_bear_declines=None,
):
    """A안 개선: 이전 사이클 반등폭(range) + 하락률(decline) 기반 체인."""
    box_start = override_start_x if override_start_x is not None else bear_chain_day + 1
    _start_lo = (
        float(override_start_x_value) if override_start_x_value is not None
        else start_lo if start_lo is not None
        else bear_chain_val
    )

    total_days = bottom_day - box_start
    if total_days < 1:
        return [], []

    N = min(max_bear_chain, max(1, total_days // MIN_BEAR_DURATION))
    dur_per_box = total_days // N

    chain_day = bear_chain_day
    chain_val = bear_chain_val
    prev_b_hi = prev_box_hi
    b_lo = max(0.01, min(max_pred_lo, _start_lo))   # box0 lo = 현재 실제 저점
    pred_rows = []
    path_specs = []

    for chain_i in range(N):
        # ── 기간 ──────────────────────────────────────────
        b_start = box_start if chain_i == 0 else chain_day + 1
        b_end = min(b_start + dur_per_box - 1, bottom_day)
        if chain_i == N - 1:
            b_end = bottom_day
        b_dur = b_end - b_start + 1
        if b_dur < 1:
            break

        # ── lo: 마지막 박스는 bottom_lo 고정 ──────────────
        if chain_i == N - 1:
            b_lo = max(0.01, min(max_pred_lo, float(bottom_lo)))

        # ── hi: lo * (1 + range_pct/100)  반등폭 ─────────
        if ref_bear_ranges and chain_i < len(ref_bear_ranges):
            range_pct = float(ref_bear_ranges[chain_i])
        else:
            range_pct = BEAR_CHAIN_MAX_RANGE_INIT * (BEAR_CHAIN_RANGE_DECAY_RATE ** chain_i)
        b_hi = b_lo * (1.0 + range_pct / 100.0)
        b_hi = min(max(b_hi, b_lo * 1.05), max_pred_hi)

        b_range = _safe_div_pct(b_hi, b_lo) if b_lo > 0 else 0.0
        b_lo_day, b_hi_day = _compute_bear_chain_lo_hi_days(b_start, b_end, b_dur, chain_day)
        _log_verbose(last, next_box_idx + chain_i, chain_i, b_start, b_end, b_hi, b_lo, b_dur, b_range)

        row = _make_bear_box_db_row(
            coin_id, last, max_cyc, next_box_idx + chain_i,
            b_start, b_end, b_hi, b_lo,
            b_hi_day, b_lo_day, b_dur, b_range,
            _safe_div_pct(b_hi, chain_val),
            _safe_div_pct(b_lo, b_hi),
            b_lo - 100.0,
        )
        pred_rows.append(row)
        path_specs.append((b_start, b_end, b_hi, b_lo, b_hi_day, b_lo_day, chain_day, chain_val, chain_i))

        chain_day = b_end
        chain_val = b_lo
        prev_b_hi = b_hi

        # ── 다음 박스 lo: 이번 hi * (1 + 하락률/100) ─────
        if chain_i < N - 1:
            if ref_bear_declines and chain_i < len(ref_bear_declines):
                decline = float(ref_bear_declines[chain_i])
            else:
                _r = BEAR_CHAIN_MAX_RANGE_INIT * (BEAR_CHAIN_RANGE_DECAY_RATE ** chain_i)
                decline = -_r / (1.0 + _r / 100.0)
            b_lo = b_hi * (1.0 + decline / 100.0)
            b_lo = max(0.01, min(max_pred_lo, b_lo))

    # ── 경로 생성 ──────────────────────────────────────────
    path_rows = []
    for i, spec in enumerate(path_specs):
        b_start, b_end, b_hi, b_lo, b_hi_day, b_lo_day, s_chain_day, s_chain_val, s_chain_i = spec
        next_lo = path_specs[i + 1][3] if i + 1 < len(path_specs) else None
        path = build_bear_box_day_points(
            coin_id, last, max_cyc,
            b_start, b_end, b_hi, b_lo,
            b_lo_day, b_hi_day,
            s_chain_day, s_chain_val, s_chain_i,
            next_box_lo=next_lo,
            bottom_day=bottom_day,
            bottom_lo=bottom_lo,
        )
        path_rows.extend(path)

    return pred_rows, path_rows
