"""BULL scenario and path construction."""

import logging

import numpy as np
import pandas as pd

from lib.common.config import (
    MAX_BULL_CHAIN,
    MAX_PRED_HI,
    MAX_PRED_LO,
    MIN_BULL_DURATION,
    TARGET_DUR,
    TARGET_HI,
    TARGET_LO,
)
from lib.common.utils import _ease_in_out, _log1p, _safe_div_pct, _signed_log1p, _wave_offset

log = logging.getLogger(__name__)


def predict_bull_box(group_models: dict, bull_feat: dict, avg_cycle_days: float, reg_feat_cols: list):
    """박스별 hi/lo/dur 회귀 예측 (Bull 체인 스텝용)."""
    X = pd.DataFrame([bull_feat])[reg_feat_cols]
    b_hi_raw = float(group_models[TARGET_HI].predict(X)[0])
    b_lo_raw = float(group_models[TARGET_LO].predict(X)[0])
    b_hi_chg_pct = float(np.sign(b_hi_raw) * np.expm1(abs(b_hi_raw)))
    b_lo_chg_pct = float(np.sign(b_lo_raw) * np.expm1(abs(b_lo_raw)))
    b_dur = max(int(round(np.expm1(float(group_models[TARGET_DUR].predict(X)[0])))), MIN_BULL_DURATION)
    return b_hi_raw, b_lo_raw, b_hi_chg_pct, b_lo_chg_pct, b_dur


def build_bull_box_day_points(
    coin_id, last, max_cyc, b_start, b_end, bull_hi, bull_lo, bull_hi_day, bull_lo_day,
    chain_day, chain_val, box_i, next_box_hi=None
):
    """구간을 시작점(Bottom: 날자·값 일치) → 고점 → 저점 → 다음 고점 순서로 그린다."""
    path_rows = []
    lower = min(bull_hi, bull_lo)
    upper = max(bull_hi, bull_lo)

    # 첫 박스만: 시작점 = Bottom (날자, 값 일치하는 지점)
    if box_i == 0 and chain_val is not None:
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bull", b_start, b_end, chain_day, chain_val))
        # Bottom → 고점 구간: (chain_day, chain_val)에서 (bull_hi_day, bull_hi)까지 곡선으로 상승
        if chain_day < bull_hi_day:
            seg0_days = max(1, bull_hi_day - chain_day)
            for d in range(chain_day + 1, bull_hi_day + 1):
                t = (d - chain_day) / seg0_days if seg0_days else 1.0
                t_smooth = _ease_in_out(t)
                v = chain_val + t_smooth * (bull_hi - chain_val)
                wave = (bull_hi - chain_val) * 0.03 * _wave_offset(d, chain_day, seg0_days, 5.0)
                v = float(v + wave)
                v = float(np.clip(v, min(lower, chain_val), max(upper, bull_hi)))
                path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bull", b_start, b_end, d, v))
        else:
            path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bull", b_start, b_end, bull_hi_day, float(bull_hi)))
        last_v = float(bull_hi)
    else:
        # 두 번째 박스부터: 구간 첫 포인트 = 고점
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bull", b_start, b_end, bull_hi_day, float(bull_hi)))
        last_v = float(bull_hi)

    # 구간2: 고점 → 저점 (bull_hi_day+1 .. bull_lo_day) — 곡선으로 하락
    seg2_days = max(1, bull_lo_day - bull_hi_day)
    for d in range(bull_hi_day + 1, bull_lo_day + 1):
        t = (d - bull_hi_day) / seg2_days if seg2_days else 1.0
        t_smooth = _ease_in_out(t)
        v = bull_hi + t_smooth * (bull_lo - bull_hi)
        wave = (bull_hi - bull_lo) * 0.03 * _wave_offset(d, bull_hi_day, seg2_days, 5.0)
        v = float(v + wave)
        v = float(np.clip(v, lower, upper))
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bull", b_start, b_end, d, v))
        last_v = v

    # 구간3: 저점 → 다음 박스 고점 — 곡선으로 상승 (next_box_hi 없으면 이 박스 bull_hi로)
    end_hi = float(next_box_hi) if next_box_hi is not None else bull_hi
    seg3_days = max(1, b_end - bull_lo_day)
    for d in range(bull_lo_day + 1, b_end + 1):
        t = (d - bull_lo_day) / seg3_days if seg3_days else 1.0
        t_smooth = _ease_in_out(t)
        v = bull_lo + t_smooth * (end_hi - bull_lo)
        wave = (end_hi - bull_lo) * 0.03 * _wave_offset(d, bull_lo_day, seg3_days, 5.0)
        v = float(v + wave)
        v = float(np.clip(v, min(lower, end_hi), max(upper, end_hi)))
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bull", b_start, b_end, d, v))
        last_v = v

    return path_rows


def build_bull_path_rows(
    coin_id, last, max_cyc, cur_day, cur_val, bull_start, bull_end, bull_hi, bull_lo, peak_day
):
    """단일 BULL 박스: Bottom(cur_day, cur_val)에서 시작해 고점→저점→끝 순서로 경로 생성."""
    pred_dur = max(1, bull_end - bull_start + 1)
    hi_day_bull = bull_start + pred_dur // 4
    lo_day_bull = bull_start + pred_dur * 3 // 4
    return build_bull_box_day_points(
        coin_id, last, max_cyc,
        bull_start, bull_end,
        bull_hi, bull_lo,
        hi_day_bull, lo_day_bull,
        cur_day, cur_val,
        0,
        next_box_hi=None,
    )


def _make_bull_row(
    coin_id, last, max_cyc, next_box_idx, bull_start, bull_end, bull_hi, bull_lo,
    hi_day_bull, lo_day_bull, pred_dur_bull, range_bull, hi_change_bull, lo_change_bull, gain_bull
):
    return (
        coin_id,
        str(last["symbol"]),
        int(last["coin_rank"]),
        max_cyc,
        str(last["cycle_name"]),
        next_box_idx,
        "BULL",
        "PRED_BULL_CHAIN",
        bull_start,
        bull_end,
        bull_hi,
        bull_lo,
        hi_day_bull,
        lo_day_bull,
        pred_dur_bull,
        range_bull,
        hi_change_bull,
        lo_change_bull,
        gain_bull,
        _log1p(bull_hi),
        _log1p(bull_lo),
        _log1p(range_bull),
        _log1p(pred_dur_bull),
        _signed_log1p(hi_change_bull),
        _signed_log1p(lo_change_bull),
        _signed_log1p(gain_bull),
        0,
        1,
        None,
        None,
    )


def build_bull_scenario(
    coin_id,
    last: pd.Series,
    max_cyc: int,
    next_box_idx: int,
    start_x: int,
    ref_lo: float,
    cycle_lo: float,
    pred_hi_bull: float,
    pred_lo_bull: float,
    pred_dur_bull: int,
    *,
    bottom_day: int | None = None,
    bottom_lo: float | None = None,
):
    """Build single BULL scenario row and path.
    저점 = 예측한 Bottom (bottom_day, bottom_lo).
    cur_day <= bottom_day 이면 (bottom_day, bottom_lo)에서 시작,
    cur_day > bottom_day 이면 마지막 박스의 저점에서 시작.
    """
    bull_start = start_x
    bull_end = bull_start + pred_dur_bull - 1
    bull_hi = pred_hi_bull
    bull_lo = pred_lo_bull

    hi_change_bull = _safe_div_pct(bull_hi, ref_lo)
    lo_change_bull = _safe_div_pct(bull_lo, bull_hi)
    gain_bull = _safe_div_pct(bull_hi, cycle_lo) if cycle_lo > 0 else 0.0
    range_bull = _safe_div_pct(bull_hi, bull_lo) if bull_lo > 0 else 0.0

    hi_day_bull = bull_start + pred_dur_bull // 4
    lo_day_bull = bull_start + pred_dur_bull * 3 // 4

    bull_row = _make_bull_row(
        coin_id, last, max_cyc, next_box_idx, bull_start, bull_end, bull_hi, bull_lo,
        hi_day_bull, lo_day_bull, pred_dur_bull, range_bull, hi_change_bull, lo_change_bull, gain_bull,
    )
    if last["phase"] == "BEAR":
        cur_day = int(last["hi_day"]) if last["hi_day"] else int(last["end_x"])
        cur_val = float(last["hi"])
    else:
        cur_day = int(last["lo_day"]) if last["lo_day"] else int(last["end_x"])
        cur_val = float(last["lo"])
    # 저점 = 예측한 Bottom. cur_day <= bottom_day 이면 (bottom_day, bottom_lo)에서 시작
    if bottom_day is not None and bottom_lo is not None:
        if cur_day <= bottom_day:
            cur_day = bottom_day
            cur_val = bottom_lo
        else:
            cur_day = int(last["lo_day"]) if pd.notna(last.get("lo_day")) else int(last["end_x"])
            cur_val = float(last["lo"])
    else:
        if cur_day <= lo_day_bull:
            cur_day = lo_day_bull
            cur_val = bull_lo
        else:
            cur_day = int(last["lo_day"]) if pd.notna(last.get("lo_day")) else int(last["end_x"])
            cur_val = float(last["lo"])
    peak_day = hi_day_bull
    if peak_day <= cur_day:
        peak_day = cur_day + max(1, (bull_end - cur_day) // 4)
    elif peak_day >= bull_end:
        peak_day = cur_day + max(1, (bull_end - cur_day) // 2)
    bull_path_rows = build_bull_path_rows(
        coin_id, last, max_cyc, cur_day, cur_val, bull_start, bull_end, bull_hi, bull_lo, peak_day
    )
    meta = {
        "bull_start": bull_start,
        "bull_end": bull_end,
        "pred_dur_bull": pred_dur_bull,
        "bull_hi": bull_hi,
        "bull_lo": bull_lo,
        "range_bull": range_bull,
        "cur_day": cur_day,
        "cur_val": cur_val,
    }
    return bull_row, bull_path_rows, meta


def build_bull_chain(
    coin_id,
    last: pd.Series,
    max_cyc: int,
    next_box_idx_after_bear: int,
    bottom_day: int,
    bottom_lo: float,
    peak_day_pred: int,
    peak_hi: float,
    pred_hi_bull: float,
    pred_lo_bull: float,
    pred_dur_bull: int,
    ref_lo: float,
    cycle_lo: float,
    max_bull_chain: int | None = None,
    ref_bull_ranges: list | None = None,
    ref_bull_pullbacks: list | None = None,
):
    """Bull 체인: lo→hi 상승폭(ref_bull_ranges) + hi→next_lo 눌림폭(ref_bull_pullbacks) 기반.

    lo[0]   = bottom_lo (고정)
    hi[i]   = lo[i] * (1 + range[i]/100)        ← 2021 상승폭
    lo[i+1] = hi[i] * (1 + pullback[i]/100)     ← 2021 눌림폭 (음수)
    hi[N-1] = peak_hi (고정)
    """
    bull_start_first = bottom_day + 1
    if peak_day_pred <= bull_start_first:
        return [], []

    total_days = peak_day_pred - bull_start_first + 1
    n_boxes_raw = max(2, (total_days + pred_dur_bull - 1) // max(1, pred_dur_bull))
    N = min(max_bull_chain if max_bull_chain is not None else MAX_BULL_CHAIN, n_boxes_raw)
    dur_per_box = total_days // N

    _BULL_RANGE_DEFAULT = 42.0   # fallback 상승폭 %
    _BULL_PULLBACK_DEFAULT = -15.0  # fallback 눌림폭 %

    bull_rows: list[tuple] = []
    path_specs: list[tuple] = []
    box_idx = next_box_idx_after_bear

    chain_day = bottom_day
    chain_val = bottom_lo
    bull_lo = max(0.01, min(MAX_PRED_LO, float(bottom_lo)))  # box0 lo = bottom_lo

    for i in range(N):
        # ── 기간 ──────────────────────────────────────────
        b_start = bull_start_first if i == 0 else chain_day + 1
        b_end = min(b_start + dur_per_box - 1, peak_day_pred)
        if i == N - 1:
            b_end = peak_day_pred
        pred_dur_b = b_end - b_start + 1
        if pred_dur_b <= 0 or b_start > peak_day_pred:
            break

        # ── hi: lo * (1 + range/100)  상승폭 ────────────
        if ref_bull_ranges and i < len(ref_bull_ranges):
            range_pct = float(ref_bull_ranges[i])
        else:
            range_pct = _BULL_RANGE_DEFAULT
        bull_hi = bull_lo * (1.0 + range_pct / 100.0)

        # 마지막 박스: hi = peak_hi 고정
        if i == N - 1:
            bull_hi = max(0.01, min(MAX_PRED_HI, float(peak_hi)))

        bull_hi = min(max(bull_hi, bull_lo * 1.05), MAX_PRED_HI)

        hi_day_bull = b_start + pred_dur_b // 4
        lo_day_bull = b_start + pred_dur_b * 3 // 4
        range_bull = _safe_div_pct(bull_hi, bull_lo) if bull_lo > 0 else 0.0
        hi_change_bull = _safe_div_pct(bull_hi, ref_lo)
        lo_change_bull = _safe_div_pct(bull_lo, bull_hi)
        gain_bull = _safe_div_pct(bull_hi, cycle_lo) if cycle_lo > 0 else 0.0

        row = _make_bull_row(
            coin_id, last, max_cyc, box_idx, b_start, b_end, bull_hi, bull_lo,
            hi_day_bull, lo_day_bull, pred_dur_b, range_bull, hi_change_bull, lo_change_bull, gain_bull,
        )
        bull_rows.append(row)
        path_specs.append((b_start, b_end, bull_hi, bull_lo, hi_day_bull, lo_day_bull, chain_day, chain_val))
        box_idx += 1

        if str(last["symbol"]).upper() in {"BTC", "ETH", "XRP"}:
            print(
                f"  ▶ PRED_BULL_CHAIN  box#{box_idx}"
                f"  day {b_start}~{b_end} ({pred_dur_b}d)"
                f"  hi={bull_hi:.2f}%  lo={bull_lo:.2f}%  range={range_bull:.1f}%"
            )

        chain_day = b_end
        chain_val = bull_lo

        # ── 다음 박스 lo: 이번 hi * (1 + pullback/100)  눌림폭 ──
        if i < N - 1:
            if ref_bull_pullbacks and i < len(ref_bull_pullbacks):
                pullback = float(ref_bull_pullbacks[i])
            else:
                pullback = _BULL_PULLBACK_DEFAULT
            bull_lo = bull_hi * (1.0 + pullback / 100.0)
            bull_lo = max(0.01, min(MAX_PRED_LO, bull_lo))

    bull_path_rows = []
    for i, spec in enumerate(path_specs):
        b_start, b_end, bull_hi, bull_lo, hi_day_bull, lo_day_bull, s_chain_day, s_chain_val = spec
        next_hi = path_specs[i + 1][2] if i + 1 < len(path_specs) else None
        path = build_bull_box_day_points(
            coin_id, last, max_cyc,
            b_start, b_end,
            bull_hi, bull_lo,
            hi_day_bull, lo_day_bull,
            s_chain_day, s_chain_val,
            i,
            next_box_hi=next_hi,
        )
        bull_path_rows.extend(path)
    return bull_rows, bull_path_rows
