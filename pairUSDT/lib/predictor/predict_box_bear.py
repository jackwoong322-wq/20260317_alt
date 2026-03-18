"""BEAR scenario and chain construction."""

import logging

import numpy as np
import pandas as pd

from lib.common.config import (
    BEAR_CHAIN_HI_DECAY_MIN,
    BEAR_CHAIN_MAX_RANGE_INIT,
    BEAR_CHAIN_RANGE_DECAY_RATE,
    FEATURE_COLS_BEAR,
    FEATURE_COLS_BTC_REG,
    MAX_BEAR_CHAIN,
    MAX_PRED_HI,
    MAX_PRED_LO,
    MIN_BEAR_DURATION,
    TARGET_DUR,
    TARGET_HI,
    TARGET_LO,
)
from lib.common.utils import _ease_in_out, _log1p, _safe_div_pct, _signed_log1p, _wave_offset
from lib.common.config import BOX_FEATURE_WEIGHTS

log = logging.getLogger(__name__)


def build_bear_scenario(
    coin_id,
    last: pd.Series,
    max_cyc: int,
    next_box_idx: int,
    start_x: int,
    ref_hi: float,
    bottom_lo,
    bottom_day,
):
    """Build single BEAR scenario row."""
    if bottom_lo is not None and bottom_day is not None:
        _pre_bear_dur = max(bottom_day, start_x + 1) - start_x + 1
        if _pre_bear_dur < MIN_BEAR_DURATION:
            bottom_lo = None

    if bottom_lo is None or bottom_day is None:
        return None, None, None, None

    bear_start = start_x
    bear_end = max(bottom_day, bear_start + 1)
    bear_hi = ref_hi
    bear_lo = bottom_lo
    dur_bear = bear_end - bear_start + 1

    hi_change_bear = _safe_div_pct(bear_hi, bear_lo)
    lo_change_bear = _safe_div_pct(bear_lo, ref_hi)
    gain_bear = bear_lo - 100.0
    range_bear = _safe_div_pct(bear_hi, bear_lo) if bear_lo > 0 else 0.0

    hi_day_bear = bear_start + dur_bear // 4
    lo_day_bear = bear_start + dur_bear * 3 // 4

    bear_row = _make_bear_row_single(
        coin_id, last, max_cyc, next_box_idx, bear_start, bear_end, bear_hi, bear_lo,
        hi_day_bear, lo_day_bear, dur_bear, range_bear, hi_change_bear, lo_change_bear, gain_bear,
    )
    if str(last["symbol"]).upper() in {"BTC", "ETH", "XRP"}:
        print(
            f"  ▶ PRED_BEAR  box#{next_box_idx+1}"
            f"  day {bear_start}~{bear_end} ({dur_bear}d)"
            f"  hi={bear_hi:.2f}%  lo={bear_lo:.2f}%  range={range_bear:.1f}%"
        )
    meta = {"bear_start": bear_start, "bear_end": bear_end, "dur_bear": dur_bear, "bear_hi": bear_hi, "bear_lo": bear_lo}
    return bear_row, meta, bottom_lo, bottom_day


def _make_bear_row_single(
    coin_id, last, max_cyc, next_box_idx, bear_start, bear_end, bear_hi, bear_lo,
    hi_day_bear, lo_day_bear, dur_bear, range_bear, hi_change_bear, lo_change_bear, gain_bear
):
    return (
        coin_id,
        str(last["symbol"]),
        int(last["coin_rank"]),
        max_cyc,
        str(last["cycle_name"]),
        next_box_idx + 1,
        "BEAR",
        "PRED_BEAR",
        bear_start,
        bear_end,
        bear_hi,
        bear_lo,
        hi_day_bear,
        lo_day_bear,
        dur_bear,
        range_bear,
        hi_change_bear,
        lo_change_bear,
        gain_bear,
        _log1p(bear_hi),
        _log1p(bear_lo),
        _log1p(range_bear),
        _log1p(dur_bear),
        _signed_log1p(hi_change_bear),
        _signed_log1p(lo_change_bear),
        _signed_log1p(gain_bear),
        0,
        1,
    )


def predict_bear_box(group_models: dict, bear_feat: dict, avg_cycle_days: float, reg_feat_cols: list):
    X_bear_chain = pd.DataFrame([bear_feat])[reg_feat_cols]
    b_hi_chg_raw = float(group_models[TARGET_HI].predict(X_bear_chain)[0])
    b_lo_chg_raw = float(group_models[TARGET_LO].predict(X_bear_chain)[0])
    b_hi_chg_pct = float(np.sign(b_hi_chg_raw) * np.expm1(abs(b_hi_chg_raw)))
    b_lo_chg_pct = float(np.sign(b_lo_chg_raw) * np.expm1(abs(b_lo_chg_raw)))
    b_dur = max(int(round(np.expm1(float(group_models[TARGET_DUR].predict(X_bear_chain)[0])))), MIN_BEAR_DURATION)
    return b_hi_chg_raw, b_lo_chg_raw, b_hi_chg_pct, b_lo_chg_pct, b_dur


def clamp_bear_box(b_hi, b_lo, b_end, bottom_day, bottom_lo, prev_box_hi, prev_box_lo, chain_i=0, target_lo_max=None):
    if b_hi < b_lo:
        b_hi, b_lo = b_lo, b_hi
    MIN_BEAR_REBOUND = 1.03
    b_hi = max(b_hi, prev_box_lo * MIN_BEAR_REBOUND)
    b_hi = min(b_hi, MAX_PRED_HI)
    b_hi = max(b_hi, prev_box_hi * 0.85)
    b_hi = min(b_hi, MAX_PRED_HI)
    max_range = BEAR_CHAIN_MAX_RANGE_INIT * (BEAR_CHAIN_RANGE_DECAY_RATE ** chain_i)
    if b_lo > 0:
        range_pct = (b_hi - b_lo) / b_lo * 100.0
        if range_pct > max_range:
            b_lo = b_hi / (1.0 + max_range / 100.0)
            b_lo = max(0.01, min(MAX_PRED_LO, b_lo))
    b_hi = min(b_hi, prev_box_hi * BEAR_CHAIN_HI_DECAY_MIN)
    if b_hi < b_lo:
        b_lo = max(0.01, b_hi * 0.99)
    if chain_i == 0 and b_lo > 0:
        min_lo_25pct = b_hi / 1.25
        if b_lo > min_lo_25pct:
            b_lo = max(0.01, min(MAX_PRED_LO, min_lo_25pct))
    if target_lo_max is not None and bottom_lo is not None and (b_end != bottom_day):
        target_lo_max = max(0.01, min(MAX_PRED_LO, float(target_lo_max)))
        b_lo = target_lo_max
        if chain_i == 0 and b_lo > 0:
            b_hi = max(b_hi, b_lo * 1.25)
            b_hi = min(MAX_PRED_HI, b_hi)
        if b_hi < b_lo:
            b_hi = b_lo * (1.0 + min(max_range, 15.0) / 100.0)
            b_hi = min(MAX_PRED_HI, b_hi)
        if b_lo > 0:
            range_pct = (b_hi - b_lo) / b_lo * 100.0
            if range_pct > max_range:
                b_hi = b_lo * (1.0 + max_range / 100.0)
                b_hi = min(MAX_PRED_HI, b_hi)
    if bottom_lo is not None and b_end == bottom_day:
        b_lo = min(max(bottom_lo, 0.01), MAX_PRED_LO)
        max_range_final = BEAR_CHAIN_MAX_RANGE_INIT * (BEAR_CHAIN_RANGE_DECAY_RATE ** chain_i)
        if b_lo > 0 and (b_hi - b_lo) / b_lo * 100.0 > max_range_final:
            b_hi = b_lo * (1.0 + max_range_final / 100.0)
            b_hi = min(MAX_PRED_HI, b_hi)
        if b_hi < b_lo:
            b_hi = b_lo
    return b_hi, b_lo


def build_bear_box_day_points(
    coin_id, last, max_cyc, b_start, b_end, b_hi, b_lo, b_lo_day, b_hi_day,
    bear_chain_day, bear_chain_val, chain_i, next_box_lo=None,
    bottom_day=None, bottom_lo=None,
):
    """구간을 저점(시작) → 고점 → 다음 박스 저점 순서로 그린다.
    마지막 박스(next_box_lo is None이고 bottom_day/bottom_lo 있음)면
    구간3을 고점(b_hi)에서 예측 최저점(bottom_day, bottom_lo)까지 그린다."""
    path_rows = []
    lo_path = b_lo
    if bear_chain_val is not None:
        denom = abs(bear_chain_val) if abs(bear_chain_val) > 1e-6 else 1.0
        if abs(bear_chain_val - b_lo) / denom < 0.001:
            lo_path = bear_chain_val * 1.00

    lower = min(b_hi, lo_path)
    upper = max(b_hi, lo_path)

    last_v = float(lo_path)
    # (선택) 첫 박스만 이전 구간 끝을 넣어 연결
    if chain_i == 0 and bear_chain_val is not None:
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bear", b_start, b_end, bear_chain_day, bear_chain_val))
    # 저점(시작): 구간의 첫 포인트 = (b_lo_day, b_lo)
    path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bear", b_start, b_end, b_lo_day, float(lo_path)))

    # 구간2: 저점 → 고점 (b_lo_day+1 .. b_hi_day)
    seg2_days = max(1, b_hi_day - b_lo_day)
    for d in range(b_lo_day + 1, b_hi_day + 1):
        t = (d - b_lo_day) / seg2_days if seg2_days else 1.0
        t_smooth = _ease_in_out(t)
        v = lo_path + t_smooth * (b_hi - lo_path)
        wave = (b_hi - lo_path) * _wave_offset(d, b_lo_day, seg2_days, 7.0)
        v = float(v + wave)
        if last_v is not None:
            denom = abs(last_v) if abs(last_v) > 1e-6 else 1.0
            if abs(v - last_v) / denom < 1e-4:
                v = last_v * 0.999
        v = float(np.clip(v, lower, upper))
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bear", b_start, b_end, d, v))
        last_v = v

    # 구간3: 고점 → 다음 박스 저점 (마지막 박스면 고점 → 예측 최저점까지)
    is_last_box = next_box_lo is None and bottom_day is not None and bottom_lo is not None
    if is_last_box:
        seg3_end_day = int(bottom_day)
        end_lo = float(bottom_lo)
    else:
        seg3_end_day = b_end
        end_lo = float(next_box_lo) if next_box_lo is not None else b_lo
    seg3_days = max(1, seg3_end_day - b_hi_day)
    for d in range(b_hi_day + 1, seg3_end_day + 1):
        t = (d - b_hi_day) / seg3_days if seg3_days else 1.0
        t_smooth = _ease_in_out(t)
        v = b_hi + t_smooth * (end_lo - b_hi)
        wave = (b_hi - end_lo) * 0.03 * _wave_offset(d, b_hi_day, seg3_days, 5.0)
        v = float(v + wave)
        v = float(np.clip(v, min(lower, end_lo), max(upper, end_lo)))
        path_rows.append((coin_id, str(last["symbol"]), max_cyc, "bear", b_start, b_end, d, v))
        last_v = v

    return path_rows


def update_bear_feat_after_box(bear_feat, prev_box_hi, b_hi, b_lo, b_dur, b_hi_chg_pct, b_lo_chg_pct, b_range, b_gain):
    cycle_min_lo = bear_feat.get("_cycle_min_lo") or 1.0
    hi_ratio = b_hi / cycle_min_lo if cycle_min_lo > 0 and b_hi > 0 else 1.0
    lo_ratio = b_lo / cycle_min_lo if cycle_min_lo > 0 and b_lo > 0 else 1.0
    bear_feat["hi_rel_to_cycle_lo"] = float(np.log(hi_ratio))
    bear_feat["lo_rel_to_cycle_lo"] = float(np.log(lo_ratio))
    bear_feat["norm_duration"] = float(np.log1p(max(b_dur, 0.0)))
    bear_feat["norm_hi_change_pct"] = float(_signed_log1p(b_hi_chg_pct))
    bear_feat["norm_lo_change_pct"] = float(_signed_log1p(b_lo_chg_pct))
    bear_feat["norm_range_pct"] = float(np.log1p(max(abs(b_range), 0.0)))
    bear_feat["norm_gain_pct"] = float(_signed_log1p(b_gain))
    for col, w in BOX_FEATURE_WEIGHTS.items():
        if col in bear_feat:
            bear_feat[col] = float(bear_feat[col]) * w


def _compute_bear_chain_lo_hi_days(b_start, b_end, b_dur, bear_chain_day):
    """박스 구간을 저점(시작) → 고점 → 끝 순서로 쓸 때, 저점일·고점일을 정한다."""
    min_seg = max(2, b_dur // 4)
    # 저점을 구간 시작 근처로 둠 (저점 = 시작)
    b_lo_day = b_start
    b_hi_day = min(b_start + min_seg, b_end - 1)
    b_hi_day = max(b_hi_day, b_lo_day + 1)
    if b_hi_day >= b_end:
        b_hi_day = b_end - 1
    if b_hi_day <= b_lo_day:
        b_hi_day = b_lo_day + max(2, b_dur // 4)
        b_hi_day = min(b_hi_day, b_end)
    return b_lo_day, b_hi_day


def _make_bear_box_db_row(
    coin_id, last, max_cyc, current_chain_idx, b_start, b_end, b_hi, b_lo,
    b_hi_day, b_lo_day, b_dur, b_range, b_hi_chg, b_lo_chg, b_gain
):
    return (
        coin_id,
        str(last["symbol"]),
        int(last["coin_rank"]),
        max_cyc,
        str(last["cycle_name"]),
        current_chain_idx,
        "BEAR",
        "PRED_BEAR_CHAIN",
        b_start,
        b_end,
        b_hi,
        b_lo,
        b_hi_day,
        b_lo_day,
        b_dur,
        b_range,
        b_hi_chg,
        b_lo_chg,
        b_gain,
        _log1p(b_hi),
        _log1p(b_lo),
        _log1p(abs(b_range)),
        _log1p(b_dur),
        _signed_log1p(b_hi_chg),
        _signed_log1p(b_lo_chg),
        _signed_log1p(b_gain),
        0,
        1,
    )

def _build_bear_chain_heuristic(
    coin_id,
    last: pd.Series,
    max_cyc: int,
    next_box_idx: int,
    bottom_day: int,
    bottom_lo: float,
    cur_day: int,
    cur_val: float,
    box_start_x: int,
    active_box_hi: float | None,
    active_box_lo: float | None,
    max_bear_chain: int = MAX_BEAR_CHAIN,
) -> tuple[list, list]:
    """AI 모델 없을 때 휴리스틱 Bear 체인 (폴백)."""
    prev_box_hi = active_box_hi if active_box_hi is not None else (float(last["hi"]) if last["hi"] else 100.0)
    prev_box_lo = active_box_lo if active_box_lo is not None else (float(last["lo"]) if last["lo"] else 50.0)
    start_lo = min(float(last["lo"]) if last.get("lo") and np.isfinite(last["lo"]) else cur_val, active_box_lo or 999.0) if active_box_lo else (float(last["lo"]) if last.get("lo") and np.isfinite(last["lo"]) else cur_val)
    bear_chain_day = cur_day
    bear_chain_val = cur_val
    pred_rows = []
    path_rows = []
    total_days = bottom_day - box_start_x
    if total_days < 1:
        return [], []
    n_boxes = min(max_bear_chain, max(1, (total_days + MIN_BEAR_DURATION - 1) // MIN_BEAR_DURATION))
    days_per_box = max(MIN_BEAR_DURATION, total_days // n_boxes)
    for chain_i in range(n_boxes):
        if bear_chain_day >= bottom_day:
            break
        b_start = box_start_x if chain_i == 0 else bear_chain_day + 1
        b_end = min(b_start + days_per_box - 1, bottom_day)
        if chain_i == n_boxes - 1:
            b_end = bottom_day
        b_dur = b_end - b_start + 1
        if b_dur < 1:
            break
        progress = (chain_i + 1) / n_boxes
        b_lo = start_lo - (start_lo - bottom_lo) * progress
        b_lo = min(max(b_lo, 0.01), MAX_PRED_LO)
        b_hi = prev_box_lo * (BEAR_CHAIN_HI_DECAY_MIN ** (chain_i + 1))
        b_hi = min(max(b_hi, b_lo * 1.05), MAX_PRED_HI)
        max_range = BEAR_CHAIN_MAX_RANGE_INIT * (BEAR_CHAIN_RANGE_DECAY_RATE ** chain_i)
        if (b_hi - b_lo) / b_lo * 100 > max_range:
            b_lo = b_hi / (1.0 + max_range / 100.0)
        b_hi, b_lo = clamp_bear_box(b_hi, b_lo, b_end, bottom_day, bottom_lo, prev_box_hi, prev_box_lo, chain_i=chain_i)
        b_lo_day, b_hi_day = _compute_bear_chain_lo_hi_days(b_start, b_end, b_dur, bear_chain_day)
        b_range = _safe_div_pct(b_hi, b_lo) if b_lo > 0 else 0.0
        b_hi_chg = _safe_div_pct(b_hi, bear_chain_val)
        b_lo_chg = _safe_div_pct(b_lo, b_hi)
        b_gain = b_lo - 100.0
        current_chain_idx = next_box_idx + chain_i
        row = _make_bear_box_db_row(coin_id, last, max_cyc, current_chain_idx, b_start, b_end, b_hi, b_lo, b_hi_day, b_lo_day, b_dur, b_range, b_hi_chg, b_lo_chg, b_gain)
        pred_rows.append(row)
        path_chunk = build_bear_box_day_points(
            coin_id, last, max_cyc, b_start, b_end, b_hi, b_lo, b_lo_day, b_hi_day,
            bear_chain_day, bear_chain_val, chain_i,
            next_box_lo=None,
            bottom_day=bottom_day,
            bottom_lo=bottom_lo,
        )
        path_rows.extend(path_chunk)
        bear_chain_day, bear_chain_val = b_end, b_lo
        prev_box_hi, prev_box_lo = b_hi, b_lo
    if pred_rows and str(last["symbol"]).upper() in {"BTC", "ETH", "XRP"}:
        log.info("[Bear chain] %s_BEAR/ALT_BEAR 없음 → 휴리스틱 폴백 %d개 박스", last["symbol"], len(pred_rows))
    return pred_rows, path_rows


def build_bear_chain(
    coin_id,
    last: pd.Series,
    max_cyc: int,
    next_box_idx: int,
    bottom_day: int,
    bottom_lo: float | None,
    cur_day: int,
    cur_val: float,
    feat: dict,
    avg_cycle_days: float,
    models: dict,
    group_key: str,
    box_start_x: int | None = None,
    active_box_hi: float | None = None,
    active_box_lo: float | None = None,
    max_bear_chain: int | None = None,
):
    """Bear 체인 생성. max_bear_chain이 None이면 config MAX_BEAR_CHAIN 사용 (BTC는 예측값으로 전달 가능)."""
    effective_max_bear = max_bear_chain if max_bear_chain is not None else MAX_BEAR_CHAIN
    group_models = models.get(group_key + "_BEAR") or models.get("ALT_BEAR")
    if group_models is None or TARGET_HI not in group_models:
        log.warning("[Bear chain] %s_BEAR/ALT_BEAR 없음 → 휴리스틱 폴백 사용", group_key)
        return _build_bear_chain_heuristic(
            coin_id, last, max_cyc, next_box_idx, bottom_day, bottom_lo if bottom_lo is not None else 20.0,
            cur_day, cur_val,
            box_start_x=box_start_x or int(last["end_x"]) + 1,
            active_box_hi=active_box_hi,
            active_box_lo=active_box_lo,
            max_bear_chain=effective_max_bear,
        )

    bear_reg_feat_cols = FEATURE_COLS_BTC_REG if group_key == "BTC" else FEATURE_COLS_BEAR
    bear_feat = feat.copy()
    prev_box_hi = active_box_hi if active_box_hi is not None else (float(last["hi"]) if last["hi"] else 100.0)
    prev_box_lo = active_box_lo if active_box_lo is not None else (float(last["lo"]) if last["lo"] else 50.0)
    last_lo_raw = float(last["lo"]) if last.get("lo") is not None and np.isfinite(last.get("lo")) else cur_val
    start_lo = min(last_lo_raw, active_box_lo) if active_box_lo is not None else last_lo_raw

    from lib.predictor.predict_box_bear_chain import run_bear_chain
    pred_rows, path_rows = run_bear_chain(
        coin_id, last, max_cyc,
        next_box_idx,
        cur_day, cur_val,
        bear_feat,
        prev_box_hi, prev_box_lo,
        bottom_day, bottom_lo if bottom_lo is not None else 20.0,
        group_models, avg_cycle_days,
        override_start_x=box_start_x if box_start_x is not None else None,
        override_start_x_value=cur_val if box_start_x is not None else None,
        reg_feat_cols=bear_reg_feat_cols,
        max_bear_chain=effective_max_bear,
        start_lo=start_lo,
        max_pred_hi=MAX_PRED_HI,
        max_pred_lo=MAX_PRED_LO,
    )

    if group_key == "BTC" and len(pred_rows) > 0:
        range_pcts = [r[15] for r in pred_rows]
        monotonic = all(range_pcts[i] >= range_pcts[i + 1] for i in range(len(range_pcts) - 1))
        log.info("[BTC BEAR chain] 박스별 range_pct(%%): %s  → 단조감소/수렴: %s", range_pcts, monotonic)
    return pred_rows, path_rows
