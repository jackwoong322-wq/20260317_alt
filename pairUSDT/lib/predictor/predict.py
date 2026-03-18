# pairUSDT/lib/predictor/predict.py
"""Orchestrates prediction; re-exports public API."""
import logging
import sqlite3

import numpy as np
import pandas as pd

from lib.common.config import (
    FEATURE_COLS,
    MAX_PRED_HI,
    MAX_PRED_LO,
    MIN_BEAR_DURATION,
    TARGET_DUR,
    TARGET_HI,
    TARGET_LO,
    TARGET_PHASE,
    MAX_BEAR_CHAIN,
    MAX_BULL_CHAIN,
)
from lib.common.utils import _safe_div_pct
from lib.predictor.data import build_cycle_and_coin_stats
from lib.predictor.predict_box_bear import build_bear_chain
from lib.predictor.predict_bottom import calc_bottom_alt, calc_bottom_btc
from lib.predictor.predict_cycle_box_count import predict_cycle_box_counts
from lib.predictor.predict_box_bull import build_bull_chain, build_bull_path_rows, build_bull_scenario
from lib.predictor.predict_features import build_feature_vector
from lib.predictor.predict_judge import judge_bull_bear
from lib.predictor.predict_model import find_most_similar_pattern, get_model_predictions
from lib.predictor.predict_peak import calc_peak_btc, calc_peak_hybrid_for_coin, compute_cross_coin_peak_ratio
from lib.predictor.predict_paths import rebuild_prediction_paths
from lib.predictor.predict_schema import CREATE_PATHS_SQL, CREATE_PEAKS_SQL, INSERT_SQL
from lib.predictor.predict_btc_anchor import calc_btc_anchor

log = logging.getLogger(__name__)

# Re-export public API
__all__ = ["CREATE_PATHS_SQL", "CREATE_PEAKS_SQL", "predict_and_insert", "print_prediction_summary", "rebuild_prediction_paths"]


def _collect_peak_rows(coin_id, last, max_cyc, peak_hi, peak_day_pred, bottom_lo, bottom_day):
    rows = []
    if peak_hi is not None and peak_day_pred is not None:
        rows.append(
            (
                coin_id,
                str(last["symbol"]),
                int(last["coin_rank"]),
                max_cyc,
                str(last["cycle_name"]),
                "PEAK",
                peak_hi,
                peak_day_pred,
            )
        )
    if bottom_lo is not None and bottom_day is not None:
        rows.append(
            (
                coin_id,
                str(last["symbol"]),
                int(last["coin_rank"]),
                max_cyc,
                str(last["cycle_name"]),
                "BOTTOM",
                bottom_lo,
                bottom_day,
            )
        )
    return rows


def _apply_btc_anchor_cap(last, btc_anchor, pred_hi_bull, pred_lo_bull):
    if btc_anchor is not None and str(last["symbol"]).upper() != "BTC":
        if btc_anchor["slope_down"]:
            prog = float(btc_anchor["cycle_progress_ratio"])
            prog = max(0.0, min(1.0, prog))
            if prog > 0.6:
                strength = (prog - 0.6) / 0.4
                cap_factor = 0.85 - 0.15 * strength
                pred_hi_bull *= cap_factor
                pred_lo_bull *= cap_factor
    return pred_hi_bull, pred_lo_bull


def _print_btc_prediction_box(last, max_cyc, is_btc_coin, pred_is_bull, prob_bull, prob_bear, bull_meta, chain_pred_rows, bottom_lo, bottom_day, sim_symbol, sim_cycle, sim_box, similarity):
    if not is_btc_coin:
        return
    _w = 68
    _pad = _w - 2
    _line = "+" + "-" * _w + "+"
    if chain_pred_rows:
        first_s, first_e = chain_pred_rows[0][8], chain_pred_rows[-1][9]
        last_lo = chain_pred_rows[-1][11]
        _bear_lines = [
            "| " + f"[BEAR 시나리오]  {len(chain_pred_rows)}개 박스 (chain)".ljust(_pad) + " |",
            "| " + f"  day {first_s}~{first_e}  -> lo={last_lo:.2f}%".ljust(_pad) + " |",
            "| " + f"  bottom_lo = {bottom_lo:.2f}%   bottom_day = {bottom_day}".ljust(_pad) + " |",
        ]
    else:
        _bear_lines = ["| " + "[BEAR 시나리오]  예측 없음".ljust(_pad) + " |"]
    _bull_lines = (
        [
            "| " + "[BULL 시나리오]".ljust(_pad) + " |",
            "| " + f"  day {bull_meta['bull_start']}~{bull_meta['bull_end']}  ({bull_meta['pred_dur_bull']}d)".ljust(_pad) + " |",
            "| " + f"  hi = {bull_meta['bull_hi']:.2f}%   lo = {bull_meta['bull_lo']:.2f}%   range = {bull_meta['range_bull']:.1f}%".ljust(_pad) + " |",
            "| " + f"  P(BULL) = {prob_bull:.3f}   P(BEAR) = {prob_bear:.3f}".ljust(_pad) + " |",
        ]
        if not pred_is_bull
        else [
            "| " + "[BULL 시나리오]".ljust(_pad) + " |",
            "| " + f"  day {bull_meta['bull_start']}~{bull_meta['bull_end']}  ({bull_meta['pred_dur_bull']}d)".ljust(_pad) + " |",
            "| " + f"  hi = {bull_meta['bull_hi']:.2f}%   lo = {bull_meta['bull_lo']:.2f}%   range = {bull_meta['range_bull']:.1f}%".ljust(_pad) + " |",
            "| " + f"  P(BULL) = {prob_bull:.3f}   P(BEAR) = {prob_bear:.3f}".ljust(_pad) + " |",
        ]
    )
    _rows = (
        [_line, "| " + f"BTC 예측 결과 요약  (Cycle {max_cyc})".ljust(_pad) + " |", _line]
        + ["| " + f"현재 마지막 박스 : #{int(last['box_index'])}  {last['phase']}  day {int(last['start_x'])}~{int(last['end_x'])}".ljust(_pad) + " |"]
        + ["| " + f"                   hi={float(last['hi']):.2f}%  lo={float(last['lo']):.2f}%".ljust(_pad) + " |", _line]
        + _bull_lines + [_line] + _bear_lines + [_line]
        + ["| " + f"[유사 패턴]  {sim_symbol}  Cycle {sim_cycle}  Box #{sim_box}  유사도 {similarity*100:.0f}%".ljust(_pad) + " |", _line]
    )
    print("\n".join(_rows))


def _log_bear_chain_verbose(_verbose, chain_pred_rows, last, max_cyc, bottom_day, bottom_lo, prob_bear_t, prob_bull_t, pred_rows):
    if not chain_pred_rows:
        if _verbose:
            log.info("    BEAR 예측  : 스킵 (bottom 모델 미충족 또는 기간 부족)")
        return
    if _verbose:
        log.info(
            "    BEAR 예측  : %d개 박스 (chain)  day %d~%d  → lo=%.2f%%",
            len(chain_pred_rows), chain_pred_rows[0][8], chain_pred_rows[-1][9], chain_pred_rows[-1][11],
        )
    if _verbose:
        log.info(
            "    BEAR bottom: day=%d  lo=%.2f%%  (trend P(bear)=%.3f  P(bull)=%.3f)",
            bottom_day, bottom_lo,
            prob_bear_t if prob_bear_t is not None else 0.0,
            prob_bull_t if prob_bull_t is not None else 0.0,
        )
    chain_rows = [r for r in pred_rows if r[1] == str(last["symbol"]) and r[3] == max_cyc and r[7] == "PRED_BEAR_CHAIN"]
    if chain_rows and _verbose:
        log.info("    Bear 체인 박스 (%d개):", len(chain_rows))
        for cr in chain_rows:
            log.info("      chain box#%d  day %d~%d (%dd)  hi=%.2f%%  lo=%.2f%%", cr[5], cr[8], cr[9], cr[14], cr[10], cr[11])


def _log_coin_prediction_verbose(
    last,
    max_cyc,
    is_btc_coin,
    _verbose,
    pred_is_bull,
    prob_bull,
    prob_bear,
    bull_meta,
    chain_pred_rows,
    bottom_lo,
    bottom_day,
    prob_bear_t,
    prob_bull_t,
    pred_rows,
    sim_symbol,
    sim_cycle,
    sim_box,
    similarity,
):
    sep = "─" * 72
    _print_btc_prediction_box(
        last, max_cyc, is_btc_coin, pred_is_bull, prob_bull, prob_bear,
        bull_meta, chain_pred_rows, bottom_lo, bottom_day,
        sim_symbol, sim_cycle, sim_box, similarity,
    )
    if _verbose:
        log.info(sep)
        log.info(
            "  ▶ [%s] Cycle %d  |  last box: #%d %s  day %d~%d  hi=%.2f%%  lo=%.2f%%",
            last["symbol"], max_cyc, int(last["box_index"]), last["phase"],
            int(last["start_x"]), int(last["end_x"]), float(last["hi"]), float(last["lo"]),
        )
        log.info("    phase 확률: P(BULL)=%.3f  P(BEAR)=%.3f  → %s", prob_bull, prob_bear, "BULL" if pred_is_bull else "BEAR")
    if _verbose and pred_is_bull:
        _hi_log = min(float(bull_meta["bull_hi"]), MAX_PRED_HI - 0.01)
        log.info(
            "    BULL 예측  : box#%d  day %d~%d (%dd)  hi=%.2f%%  lo=%.2f%%  range=%.1f%%",
            bull_meta.get("next_box_idx", 0),
            bull_meta["bull_start"],
            bull_meta["bull_end"],
            bull_meta["pred_dur_bull"],
            _hi_log,
            bull_meta["bull_lo"],
            bull_meta["range_bull"],
        )
    _log_bear_chain_verbose(_verbose, chain_pred_rows, last, max_cyc, bottom_day, bottom_lo, prob_bear_t, prob_bull_t, pred_rows)
    if _verbose:
        log.info("    유사 패턴   : %s Cycle %d Box #%d  유사도=%.0f%%", sim_symbol, sim_cycle, sim_box, similarity * 100.0)
    if _verbose:
        log.info(sep)


def _predict_one_coin_phase1(coin_id, max_cyc, grp, last, df_all, train_df, models, bottom_models, peak_models, cycle_stats, coin_stats, phase_box_stats, btc_anchor, btc_cycle_max_hi=None, cross_median: float | None = None):
    _verbose = str(last["symbol"]).upper() in {"BTC", "ETH", "XRP"}
    feat, avg_cycle_days = build_feature_vector(last, coin_id, max_cyc, cycle_stats, coin_stats, phase_box_stats, btc_cycle_max_hi)
    X_pred = pd.DataFrame([feat])[FEATURE_COLS]
    group_key = "BTC" if str(last["symbol"]).upper() == "BTC" else "ALT"
    phase_models = models.get(group_key)
    if phase_models is None:
        phase_models = models.get("ALT")
    if phase_models is None or TARGET_PHASE not in phase_models:
        return None
    phase_proba = phase_models[TARGET_PHASE].predict_proba(X_pred)[0]
    prob_bear, prob_bull = float(phase_proba[0]), float(phase_proba[1])
    reg_key = group_key + ("_BEAR" if prob_bear >= prob_bull else "_BULL")
    reg_models = models.get(reg_key) or models.get("ALT_BEAR") or models.get("ALT_BULL")
    if reg_models is None or TARGET_HI not in reg_models:
        return None
    group_models = {
        TARGET_PHASE: phase_models[TARGET_PHASE],
        TARGET_HI: reg_models[TARGET_HI],
        TARGET_LO: reg_models[TARGET_LO],
        TARGET_DUR: reg_models[TARGET_DUR],
    }
    pred_norm_hi, pred_norm_lo, pred_norm_dur, prob_bear, prob_bull, pred_hi_bull, pred_lo_bull, pred_dur_bull = get_model_predictions(group_models, X_pred, last, reg_key=reg_key)
    is_btc_coin = group_key == "BTC"
    bottom_lo, bottom_day, prob_bear_t, prob_bull_t = None, None, None, None
    if is_btc_coin:
        bottom_lo, bottom_day = calc_bottom_btc(df_all, max_cyc, last)
        prob_bear_t, prob_bull_t = prob_bear, prob_bull
    else:
        bottom_lo, bottom_day, prob_bear_t, prob_bull_t = calc_bottom_alt(bottom_models, group_key, X_pred, last)
        # ALT bottom 모델 미학습(샘플<30) 시 폴백: 현재 박스 기준으로 bear chain 진입 허용
        if bottom_lo is None and bottom_day is None and bottom_models.get(group_key) is None:
            ref_lo = float(last["lo"]) if last.get("lo") is not None and np.isfinite(last.get("lo")) else 50.0
            bottom_lo = min(max(ref_lo * 0.70, 5.0), MAX_PRED_LO)
            bottom_day = int(last["end_x"]) + max(MIN_BEAR_DURATION, 30)
            prob_bear_t, prob_bull_t = prob_bear, prob_bull
            log.info("  [%s] Bottom 모델 없음 → 폴백 bottom_lo=%.2f%% bottom_day=%d", last["symbol"], bottom_lo, bottom_day)
    pred_is_bull, *_ = judge_bull_bear(last, grp, max_cyc, prob_bull, prob_bear, bottom_day, btc_anchor, bottom_lo=bottom_lo)
    peak_hi, peak_day_pred = None, None
    if is_btc_coin:
        peak_hi, peak_day_pred = calc_peak_btc(df_all, max_cyc, last, coin_id, cross_median)
    else:
        # ALT 코인도 BTC와 동일한 하이브리드 감소율 기반 peak_hi 계산 사용
        peak_hi, peak_day_pred = calc_peak_hybrid_for_coin(
            df_all, coin_id, max_cyc, last, cross_median, label=str(last["symbol"]).upper()
        )
    log.debug("    Peak 예측: hi=%.2f%%  day=%s", peak_hi if peak_hi else 0.0, str(peak_day_pred) if peak_day_pred else "-")
    peak_rows = list(_collect_peak_rows(coin_id, last, max_cyc, peak_hi, peak_day_pred, bottom_lo, bottom_day))
    start_x = int(last["end_x"]) + 1
    ref_lo = float(last["lo"]) if last["lo"] else 100.0
    cycle_lo = float(grp["lo"].min()) if not grp.empty else ref_lo
    next_box_idx = int(grp[grp["is_prediction"] == 0]["box_index"].max()) + 1
    return {"last": last, "coin_id": coin_id, "max_cyc": max_cyc, "grp": grp, "df_all": df_all, "train_df": train_df,
        "models": models, "bottom_models": bottom_models, "peak_models": peak_models,
        "cycle_stats": cycle_stats, "coin_stats": coin_stats, "phase_box_stats": phase_box_stats, "btc_anchor": btc_anchor,
        "feat": feat, "avg_cycle_days": avg_cycle_days, "X_pred": X_pred, "group_key": group_key, "group_models": group_models, "reg_key": reg_key,
        "pred_hi_bull": pred_hi_bull, "pred_lo_bull": pred_lo_bull, "pred_dur_bull": pred_dur_bull,
        "is_btc_coin": is_btc_coin, "bottom_lo": bottom_lo, "bottom_day": bottom_day, "prob_bear_t": prob_bear_t, "prob_bull_t": prob_bull_t,
        "pred_is_bull": pred_is_bull, "peak_hi": peak_hi, "peak_day_pred": peak_day_pred, "peak_rows": peak_rows,
        "start_x": start_x, "ref_lo": ref_lo, "cycle_lo": cycle_lo, "next_box_idx": next_box_idx,
        "_verbose": _verbose, "prob_bear": prob_bear, "prob_bull": prob_bull}


def _find_low_day_in_period(conn: sqlite3.Connection, coin_id: int, cycle_number: int, day_start: int, day_end: int) -> tuple[int, float] | None:
    """alt_cycle_data에서 [day_start, day_end] 구간의 실제 저점일·저점값 반환. 없으면 None."""
    try:
        row = conn.execute(
            """
            SELECT days_since_peak, low_rate
            FROM alt_cycle_data
            WHERE coin_id = ? AND cycle_number = ? AND days_since_peak >= ? AND days_since_peak <= ?
            ORDER BY low_rate ASC
            LIMIT 1
            """,
            (coin_id, cycle_number, day_start, day_end),
        ).fetchone()
        if row and row[0] is not None and row[1] is not None:
            return int(row[0]), float(row[1])
    except Exception:
        pass
    return None


def _predict_one_coin_phase2(conn: sqlite3.Connection, bundle: dict):
    last, coin_id, max_cyc = bundle["last"], bundle["coin_id"], bundle["max_cyc"]
    feat, pred_hi_bull, pred_lo_bull, pred_dur_bull = bundle["feat"], bundle["pred_hi_bull"], bundle["pred_lo_bull"], bundle["pred_dur_bull"]
    pred_is_bull, bottom_lo, bottom_day = bundle["pred_is_bull"], bundle["bottom_lo"], bundle["bottom_day"]
    start_x, next_box_idx, ref_lo, cycle_lo = bundle["start_x"], bundle["next_box_idx"], bundle["ref_lo"], bundle["cycle_lo"]

    # 선형 회귀 기반 Bear/Bull 박스 수 예측 (BTC/알트 동일: 해당 코인 완성 사이클 2개 미만이면 None → config 상수 사용)
    cycle_prediction = None
    cycle_prediction = predict_cycle_box_counts(conn, max_cyc, coin_id=coin_id)
    if cycle_prediction is not None:
        log.info(
            "  [%s] Cycle %d 박스 수 예측: Bear=%d Bull=%d (method=%s guard_bear=%s guard_bull=%s)",
            last["symbol"], max_cyc, cycle_prediction.bear_count, cycle_prediction.bull_count,
            cycle_prediction.method, cycle_prediction.guard_applied["bear"], cycle_prediction.guard_applied["bull"],
        )
    bundle["cycle_prediction"] = cycle_prediction
    if int(last.get("is_completed", 1)) == 0:
        active_result = "BEAR_ACTIVE" if not pred_is_bull else "BULL_ACTIVE"
        conn.execute(
            """UPDATE coin_analysis_results SET result = ?
               WHERE coin_id = ? AND cycle_number = ? AND is_completed = 0 AND is_prediction = 0""",
            (active_result, coin_id, max_cyc),
        )
        # 예측 후 active 박스의 저점을 예측된 최저점(bottom)으로 변경 (화살표 방향: 현재 저점 → 예측 저점)
        if bottom_lo is not None and bottom_day is not None:
            conn.execute(
                """UPDATE coin_analysis_results SET lo = ?, lo_day = ?
                   WHERE coin_id = ? AND cycle_number = ? AND is_completed = 0 AND is_prediction = 0""",
                (bottom_lo, bottom_day, coin_id, max_cyc),
            )
        conn.commit()
        log.info("  [%s] ACTIVE 박스 result 업데이트: %s", last["symbol"], active_result)
    pred_hi_bull, pred_lo_bull = _apply_btc_anchor_cap(last, bundle["btc_anchor"], pred_hi_bull, pred_lo_bull)
    # Bull 시나리오 1개 생성 (Bear chain의 cur_day/cur_val 계산용; Bear 있을 때는 나중에 연속 Bull로 대체)
    bull_row, bull_path_rows, bull_meta = build_bull_scenario(
        coin_id, last, max_cyc, next_box_idx, start_x, ref_lo, cycle_lo,
        pred_hi_bull, pred_lo_bull, pred_dur_bull,
        bottom_day=bottom_day, bottom_lo=bottom_lo,
    )
    bull_meta["next_box_idx"] = next_box_idx
    pred_rows, path_rows = [], []
    pred_rows.append(bull_row)
    path_rows = list(bull_path_rows)
    if bottom_lo is not None and bottom_day is not None:
        _pre_bear_dur = max(bottom_day, start_x + 1) - start_x + 1
        if _pre_bear_dur < MIN_BEAR_DURATION:
            bottom_lo = None
    chain_pred_rows = []
    chain_path_rows = []
    if bottom_lo is not None and bottom_day is not None:
        # ACTIVE 박스(is_completed=0) hi/lo를 AI 계산 기준으로 사용
        active_rows = bundle["grp"][bundle["grp"]["is_completed"] == 0]
        active_hi = float(active_rows.iloc[-1]["hi"]) if not active_rows.empty else None
        active_lo = float(active_rows.iloc[-1]["lo"]) if not active_rows.empty else None
        # Bear box 시작일 = 저점일. 저점(저점일, 저점값)부터 시작, 고점은 모델이 예측(b_hi)하여 표시
        day_start = int(last["end_x"])
        if not active_rows.empty:
            act = active_rows.iloc[-1]
            day_end = max(day_start, int(act["hi_day"]) if pd.notna(act.get("hi_day")) else int(act["end_x"]))
        else:
            day_end = bottom_day if bottom_day is not None else day_start + 365
        low_info = _find_low_day_in_period(conn, coin_id, max_cyc, day_start, day_end)
        if low_info is not None:
            bear_cur_day, bear_cur_val = low_info
            bear_box_start_x = bear_cur_day
        else:
            if not active_rows.empty:
                act = active_rows.iloc[-1]
                bear_cur_day = int(act["lo_day"]) if pd.notna(act.get("lo_day")) else int(act.get("start_x", last["end_x"]))
                bear_cur_val = float(act["lo"])
            else:
                bear_cur_day = int(last["lo_day"]) if pd.notna(last.get("lo_day")) else int(last["end_x"])
                bear_cur_val = float(last["lo"]) if last.get("lo") is not None else float(last["hi"])
            bear_box_start_x = bear_cur_day
        # 이전 사이클(2021) BEAR 박스 데이터 추출
        _sym = str(last["symbol"]).upper()
        _bear_2021 = (
            bundle["df_all"][
                (bundle["df_all"]["symbol"].str.upper() == _sym)
                & (bundle["df_all"]["cycle_name"].str.contains("2021", case=False, na=False))
                & (bundle["df_all"]["phase"] == "BEAR")
                & (bundle["df_all"]["is_completed"] == 1)
            ]
            .sort_values("box_index")
            .reset_index(drop=True)
        )
        # 반등폭: lo → hi within box
        _ref_ranges = _bear_2021["range_pct"].tolist()
        # 하락률: 이전박스 hi → 현재박스 lo  (box[i].hi → box[i+1].lo)
        _ref_declines = []
        for _i in range(len(_bear_2021) - 1):
            _curr_hi = float(_bear_2021.iloc[_i]["hi"])
            _next_lo = float(_bear_2021.iloc[_i + 1]["lo"])
            _ref_declines.append((_next_lo - _curr_hi) / _curr_hi * 100 if _curr_hi > 0 else -30.0)
        # 현재 사이클에서 완료된 BEAR 박스 수 = 오프셋
        _bear_offset = int(
            bundle["grp"][
                (bundle["grp"]["phase"] == "BEAR")
                & (bundle["grp"]["is_completed"] == 1)
            ].shape[0]
        )
        _ref_ranges_offset = _ref_ranges[_bear_offset:] or None
        _ref_declines_offset = _ref_declines[_bear_offset:] or None
        log.info("  [%s] BEAR offset=%d ranges=%s declines=%s", _sym, _bear_offset, _ref_ranges_offset, _ref_declines_offset)

        # 이전 사이클(2021) BULL 박스 데이터 추출
        _bull_2021 = (
            bundle["df_all"][
                (bundle["df_all"]["symbol"].str.upper() == _sym)
                & (bundle["df_all"]["cycle_name"].str.contains("2021", case=False, na=False))
                & (bundle["df_all"]["phase"] == "BULL")
                & (bundle["df_all"]["is_completed"] == 1)
            ]
            .sort_values("box_index")
            .reset_index(drop=True)
        )
        # 상승폭: lo → hi within box
        _ref_bull_ranges = _bull_2021["range_pct"].tolist()
        # 눌림폭: box[i].hi → box[i+1].lo (음수)
        _ref_bull_pullbacks = []
        for _i in range(len(_bull_2021) - 1):
            _curr_hi = float(_bull_2021.iloc[_i]["hi"])
            _next_lo = float(_bull_2021.iloc[_i + 1]["lo"])
            _ref_bull_pullbacks.append((_next_lo - _curr_hi) / _curr_hi * 100 if _curr_hi > 0 else -10.0)
        # 현재 사이클에서 완료된 BULL 박스 수 = 오프셋
        _bull_offset = int(
            bundle["grp"][
                (bundle["grp"]["phase"] == "BULL")
                & (bundle["grp"]["is_completed"] == 1)
            ].shape[0]
        )
        _ref_bull_ranges_offset = _ref_bull_ranges[_bull_offset:] or None
        _ref_bull_pullbacks_offset = _ref_bull_pullbacks[_bull_offset:] or None
        log.info("  [%s] BULL offset=%d ranges=%s pullbacks=%s", _sym, _bull_offset, _ref_bull_ranges_offset, _ref_bull_pullbacks_offset)
        chain_pred_rows, chain_path_rows = build_bear_chain(
            coin_id=coin_id, last=last, max_cyc=max_cyc, next_box_idx=next_box_idx,
            bottom_day=bottom_day, bottom_lo=bottom_lo,
            cur_day=bear_cur_day, cur_val=bear_cur_val,
            feat=feat, avg_cycle_days=bundle["avg_cycle_days"], models=bundle["models"], group_key=bundle["group_key"],
            box_start_x=bear_box_start_x,
            active_box_hi=active_hi,
            active_box_lo=active_lo,
            max_bear_chain=min(bundle["cycle_prediction"].bear_count, MAX_BEAR_CHAIN) if bundle.get("cycle_prediction") else None,
            ref_bear_ranges=_ref_ranges_offset,
            ref_bear_declines=_ref_declines_offset,
        )
        pred_rows.extend(chain_pred_rows)
        # Bear chain 종료점에서 Bull path 연결: 하락→최저점→반등 이 한 줄로 이어지도록
        if chain_path_rows:
            last_bear = chain_path_rows[-1]
            bear_end_day, bear_end_val = last_bear[6], last_bear[7]
            # Bear chain이 있으면 Bull은 최저점 다음날부터 시작. 연속 BULL 박스 생성
            peak_hi = bundle.get("peak_hi")
            peak_day_pred = bundle.get("peak_day_pred")
            if peak_hi is not None and peak_day_pred is not None and peak_day_pred > bottom_day:
                next_box_idx_after_bear = next_box_idx + len(chain_pred_rows)
                bull_chain_rows, bull_chain_path = build_bull_chain(
                    coin_id, last, max_cyc, next_box_idx_after_bear,
                    bottom_day, bottom_lo, peak_day_pred, peak_hi,
                    pred_hi_bull, pred_lo_bull, pred_dur_bull, ref_lo, cycle_lo,
                    max_bull_chain=min(bundle["cycle_prediction"].bull_count, MAX_BULL_CHAIN) if bundle.get("cycle_prediction") else None,
                    ref_bull_ranges=_ref_bull_ranges_offset,
                    ref_bull_pullbacks=_ref_bull_pullbacks_offset,
                )
                if bull_chain_rows:
                    pred_rows.pop(0)
                    pred_rows.extend(bull_chain_rows)
                    bull_meta["bull_start"] = bottom_day + 1
                    bull_meta["bull_end"] = peak_day_pred + max(1, pred_dur_bull // 2)
                    bull_meta["bull_hi"] = peak_hi
                    bull_meta["bull_lo"] = pred_lo_bull
                    bull_meta["range_bull"] = _safe_div_pct(peak_hi, pred_lo_bull) if pred_lo_bull and pred_lo_bull > 0 else 0.0
                    # Bear 체인 path 뒤에 바로 Bull 체인 path를 이어붙인다 (중간 bridge 포인트로 인한 스파이크 제거)
                    path_rows = list(chain_path_rows) + [r for r in bull_chain_path if r[6] >= bottom_day]
                else:
                    bull_meta["bull_start"] = bottom_day + 1
                    bull_meta["bull_end"] = bottom_day + pred_dur_bull
                    path_rows = list(chain_path_rows) + [
                        (coin_id, str(last["symbol"]), max_cyc, "bull", bull_meta["bull_start"], bull_meta["bull_end"], bear_end_day, bear_end_val)
                    ] + [r for r in bull_path_rows if r[6] > bear_end_day]
            else:
                # peak 없음: 단일 Bull 박스만 최저점 다음날부터
                pred_rows.pop(0)
                bull_row_after, _, _ = build_bull_scenario(
                    coin_id, last, max_cyc, next_box_idx + len(chain_pred_rows), bottom_day + 1, ref_lo, cycle_lo,
                    pred_hi_bull, pred_lo_bull, pred_dur_bull,
                    bottom_day=bottom_day, bottom_lo=bottom_lo,
                )
                pred_rows.append(bull_row_after)
                bull_meta["bull_start"] = bottom_day + 1
                bull_meta["bull_end"] = bull_row_after[9]
                bull_meta["bull_hi"] = bull_row_after[10]
                bull_meta["bull_lo"] = bull_row_after[11]
                bull_meta["range_bull"] = bull_row_after[17]
                peak_day_approx = bull_row_after[12]
                bull_path_from_bottom = build_bull_path_rows(
                    coin_id, last, max_cyc, bottom_day, bottom_lo,
                    bottom_day + 1, bull_row_after[9], bull_row_after[10], bull_row_after[11], peak_day_approx,
                )
                bridge = (coin_id, str(last["symbol"]), max_cyc, "bull", bull_meta["bull_start"], bull_meta["bull_end"], bear_end_day, bear_end_val)
                path_rows = list(chain_path_rows) + [bridge] + [r for r in bull_path_from_bottom if r[6] > bear_end_day]
        else:
            path_rows = list(bull_path_rows)
    sim_symbol, sim_cycle, sim_box, similarity = find_most_similar_pattern(bundle["train_df"], bundle["X_pred"])
    bundle["pred_rows"] = pred_rows
    bundle["path_rows"] = path_rows
    bundle["chain_pred_rows"] = chain_pred_rows
    bundle["bull_meta"] = bull_meta
    bundle["bottom_lo"] = bottom_lo
    bundle["sim_symbol"] = sim_symbol
    bundle["sim_cycle"] = sim_cycle
    bundle["sim_box"] = sim_box
    bundle["similarity"] = similarity


def _predict_one_coin(
    conn: sqlite3.Connection,
    coin_id: int,
    max_cyc: int,
    grp: pd.DataFrame,
    last: pd.Series,
    df_all: pd.DataFrame,
    train_df: pd.DataFrame,
    models: dict,
    bottom_models: dict,
    peak_models: dict,
    cycle_stats: dict,
    coin_stats: dict,
    phase_box_stats: dict,
    btc_anchor: dict | None,
    btc_cycle_max_hi: dict | None = None,
    cross_median: float | None = None,
):
    bundle = _predict_one_coin_phase1(
        coin_id, max_cyc, grp, last, df_all, train_df, models,
        bottom_models, peak_models, cycle_stats, coin_stats, phase_box_stats, btc_anchor,
        btc_cycle_max_hi=btc_cycle_max_hi,
        cross_median=cross_median,
    )
    if bundle is None:
        return [], [], [], True
    _predict_one_coin_phase2(conn, bundle)
    b = bundle
    _log_coin_prediction_verbose(
        b["last"], b["max_cyc"], b["is_btc_coin"], b["_verbose"],
        b["pred_is_bull"], b["prob_bull"], b["prob_bear"], b["bull_meta"],
        b["chain_pred_rows"], b["bottom_lo"], b["bottom_day"], b["prob_bear_t"], b["prob_bull_t"],
        b["pred_rows"], b["sim_symbol"], b["sim_cycle"], b["sim_box"], b["similarity"],
    )
    return b["pred_rows"], b["path_rows"], b["peak_rows"], False


def predict_and_insert(
    conn: sqlite3.Connection,
    df_all: pd.DataFrame,
    train_df: pd.DataFrame,
    models: dict,
    bottom_models: dict,
    peak_models: dict,
) -> int:
    deleted = conn.execute("DELETE FROM coin_analysis_results WHERE is_prediction = 1").rowcount
    conn.commit()
    log.info("기존 예측 %d건 삭제 후 재예측 시작", deleted)

    # 예측 경로 저장용 테이블이 없을 수 있으므로 생성 (033 비주얼라이저에서 읽음)
    conn.execute(CREATE_PATHS_SQL)
    conn.commit()

    current_cycles = df_all.groupby("coin_id")["cycle_number"].max().reset_index().rename(columns={"cycle_number": "max_cycle"})
    cycle_stats, coin_stats, phase_box_stats, btc_cycle_max_hi = build_cycle_and_coin_stats(df_all)
    btc_anchor = calc_btc_anchor(df_all, cycle_stats, coin_stats)
    cross_median = compute_cross_coin_peak_ratio(conn)
    pred_count = 0
    skip_count = 0
    pred_rows = []
    path_rows = []
    peak_rows = []
    for _, row in current_cycles.iterrows():
        coin_id = row["coin_id"]
        max_cyc = int(row["max_cycle"])

        grp = (
            df_all[(df_all["coin_id"] == coin_id) & (df_all["cycle_number"] == max_cyc)]
            .sort_values("box_index")
            .reset_index(drop=True)
        )
        if grp.empty:
            continue

        active = grp[grp["is_completed"] == 0]
        completed = grp[grp["is_completed"] == 1]
        # ACTIVE 박스 전 completed 박스를 last로 사용 (그 다음부터 예측)
        if not active.empty and not completed.empty:
            last = completed.iloc[-1]
        elif not active.empty:
            last = active.iloc[-1]
        else:
            last = grp.iloc[-1]

        prows, pathrows, peakrs, skipped = _predict_one_coin(
            conn, coin_id, max_cyc, grp, last, df_all, train_df, models,
            bottom_models, peak_models, cycle_stats, coin_stats, phase_box_stats, btc_anchor,
            btc_cycle_max_hi=btc_cycle_max_hi,
            cross_median=cross_median,
        )
        if skipped:
            skip_count += 1
            continue
        pred_rows.extend(prows)
        path_rows.extend(pathrows)
        peak_rows.extend(peakrs)
        pred_count += 1

    _insert_predictions_to_db(conn, pred_rows, path_rows, peak_rows, pred_count, skip_count)
    # 기존 체인 기반 path를 한 번 저장한 뒤, 새 보간 기반 알고리즘으로 전체 path를 재구성해 덮어쓴다.
    # rebuild_prediction_paths(conn)
    return pred_count


def _insert_predictions_to_db(conn, pred_rows, path_rows, peak_rows, pred_count, skip_count):
    if pred_rows:
        conn.executemany(INSERT_SQL, pred_rows)
    # coin_prediction_paths 테이블이 있어야 함 (predict_and_insert에서 CREATE_PATHS_SQL 실행)
    if path_rows:
        conn.executemany(
            """
            INSERT INTO coin_prediction_paths
            (coin_id, symbol, cycle_number, scenario, start_x, end_x, day_x, value)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            path_rows,
        )
    else:
        log.warning(
            "path_rows가 비어 있어 coin_prediction_paths에 저장된 경로가 없습니다. "
            "예측이 스킵되었거나(모든 코인 skip) Bear/Bull 경로가 생성되지 않았을 수 있습니다."
        )
    if peak_rows:
        conn.execute(CREATE_PEAKS_SQL)
        conn.execute("DELETE FROM coin_prediction_peaks")
        conn.executemany(
            """
            INSERT INTO coin_prediction_peaks
            (coin_id, symbol, coin_rank, cycle_number, cycle_name,
             peak_type, predicted_value, predicted_day)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            peak_rows,
        )
    conn.commit()
    log.info("=" * 72)
    log.info("  예측 저장 완료: 코인 %d개  스킵 %d개  | pred_rows=%d  path_rows=%d", pred_count, skip_count, len(pred_rows), len(path_rows))
    log.info("=" * 72)


def _print_summary_table(df: pd.DataFrame):
    log.info("=" * 75)
    log.info("예측 결과 요약 (상위 20개)")
    log.info(
        "  %-6s  %-4s  %-5s  %5s  %8s  %8s  %6s  %6s  %6s  %6s  %6s",
        "Symbol",
        "Rank",
        "Phase",
        "Start",
        "End",
        "Dur(d)",
        "Hi(%)",
        "Lo(%)",
        "Range(%)",
        "HiDay",
        "LoDay",
    )
    log.info("  " + "-" * 70)
    _SUMMARY_SYMBOLS = {"BTC", "ETH", "XRP", "BNB", "SOL"}
    df_filtered = df[df["symbol"].str.upper().isin(_SUMMARY_SYMBOLS)]
    for _, r in df_filtered.iterrows():
        log.info(
            "  %-6s  #%3d  %-5s  %5d  %5d~%5d  %4dd  %6.1f  %6.1f  %5.1f%%  %6d  %6d",
            r["symbol"],
            r["coin_rank"],
            r["phase"],
            r["start_x"],
            r["start_x"],
            r["end_x"],
            r["duration"],
            r["hi"],
            r["lo"],
            r["range_pct"],
            int(r["hi_day"]) if not pd.isna(r["hi_day"]) else -1,
            int(r["lo_day"]) if not pd.isna(r["lo_day"]) else -1,
        )
    log.info("  ... 총 %d개 코인 예측 완료", len(df))
    log.info("=" * 75)


def _print_summary_stats(df: pd.DataFrame):
    log.info("예측 통계:")
    hi_series = df["hi"].astype(float).clip(upper=MAX_PRED_HI - 0.01)
    log.info(
        "  hi   mean=%.2f%%  std=%.2f%%  min=%.2f%%  max=%.2f%%",
        hi_series.mean(),
        hi_series.std(),
        hi_series.min(),
        hi_series.max(),
    )
    log.info(
        "  lo   mean=%.2f%%  std=%.2f%%  min=%.2f%%  max=%.2f%%",
        df["lo"].mean(),
        df["lo"].std(),
        df["lo"].min(),
        df["lo"].max(),
    )
    log.info(
        "  dur  mean=%.1fd  std=%.1fd  min=%dd  max=%dd",
        df["duration"].mean(),
        df["duration"].std(),
        int(df["duration"].min()),
        int(df["duration"].max()),
    )
    bull_cnt = (df["phase"] == "BULL").sum()
    bear_cnt = (df["phase"] == "BEAR").sum()
    log.info("  phase  BULL=%d개  BEAR=%d개", bull_cnt, bear_cnt)


def print_prediction_summary(conn: sqlite3.Connection):
    df = pd.read_sql_query(
        """
        SELECT symbol, coin_rank, cycle_name, phase,
               start_x, end_x, duration, hi, lo, hi_day, lo_day, range_pct
        FROM coin_analysis_results
        WHERE is_prediction = 1
        ORDER BY coin_rank
        """,
        conn,
    )
    if df.empty:
        log.warning("저장된 예측이 없습니다.")
        return

    _print_summary_table(df)
    _print_summary_stats(df)