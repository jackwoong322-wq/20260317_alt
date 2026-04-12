"""032_train_and_predict_box.py

XGBoost 기반 다음 박스권 예측 및 DB 저장

Usage: python 032_train_and_predict_box.py
"""

import logging
import math
from typing import Any
from datetime import datetime

import numpy as np
import pandas as pd
import requests

from lib.common.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    TARGET_HI,
    TARGET_LO,
    TARGET_DUR,
    TARGET_PHASE,
)
from lib.analyzer.db import setup_db
from lib.predictor.data import (
    load_box_df,
    build_training_pairs,
    build_bottom_dataset,
)
try:
    from lib.predictor.train import (
        train_box_models,
        train_box_reg_group,
        train_bottom_models,
        print_feature_importance,
    )
except ImportError:
    train_box_models = None
    train_box_reg_group = None
    train_bottom_models = None
    print_feature_importance = None
from lib.predictor.predict import (
    CREATE_PATHS_SQL,
    CREATE_PEAKS_SQL,
    predict_outputs,
    print_prediction_summary_rows,
)

log = logging.getLogger(__name__)

SUPABASE_PAGE_SIZE = 1000


class _NoOpConn:
    def close(self):
        return None


def _normalize_json_value(v):
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _normalize_rows(rows: list[dict]) -> list[dict]:
    return [{k: _normalize_json_value(v) for k, v in row.items()} for row in rows]


def get_supabase_headers(include_json: bool = False) -> dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL/SUPABASE_ANON_KEY가 설정되지 않았습니다.")
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


def fetch_all_supabase(
    table: str, select_cols: str, extra_params: dict | None = None
) -> list[dict]:
    rows = []
    offset = 0
    headers = get_supabase_headers()

    while True:
        params = {"select": select_cols}
        if extra_params:
            params.update(extra_params)

        page_headers = {
            **headers,
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + SUPABASE_PAGE_SIZE - 1}",
        }
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params=params,
            headers=page_headers,
            timeout=60,
        )
        res.raise_for_status()

        batch = res.json()
        rows.extend(batch)
        if len(batch) < SUPABASE_PAGE_SIZE:
            break
        offset += SUPABASE_PAGE_SIZE

    return rows


def setup_stage_db_for_supabase(conn: Any):
    setup_db(conn)
    conn.execute(CREATE_PATHS_SQL)
    conn.execute(CREATE_PEAKS_SQL)
    conn.commit()


def _insert_dict_rows(conn: Any, table: str, rows: list[dict]):
    if not rows:
        return

    try:
        valid_cols = [
            r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
        ]
    except Exception:
        valid_cols = [r[0] for r in conn.execute(f"DESCRIBE {table}").fetchall()]
    cols = [c for c in valid_cols if any(c in row for row in rows)]
    if not cols:
        return

    placeholders = ",".join(["?" for _ in cols])
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    values = [tuple(row.get(c) for c in cols) for row in rows]
    conn.executemany(sql, values)
    conn.commit()


def hydrate_stage_db_from_supabase(conn: Any):
    box_rows = fetch_all_supabase(
        "coin_analysis_results",
        "*",
        {
            "is_prediction": "eq.0",
            "order": "coin_id.asc,cycle_number.asc,box_index.asc",
        },
    )
    _insert_dict_rows(conn, "coin_analysis_results", box_rows)
    log.info("Supabase 데이터 적재 완료: coin_analysis_results=%d", len(box_rows))


def _post_rows_supabase(table: str, rows: list[dict]):
    if not rows:
        return
    headers = {**get_supabase_headers(include_json=True), "Prefer": "return=minimal"}
    for i in range(0, len(rows), SUPABASE_PAGE_SIZE):
        chunk = _normalize_rows(rows[i : i + SUPABASE_PAGE_SIZE])
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            json=chunk,
            timeout=60,
        )
        if not res.ok:
            body = (res.text or "")[:500]
            raise requests.HTTPError(
                f"Supabase insert failed for {table}: status={res.status_code}, body={body}",
                response=res,
            )


def reset_predictions_supabase():
    headers = {**get_supabase_headers(include_json=True), "Prefer": "return=minimal"}
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/coin_analysis_results",
        params={"is_prediction": "eq.1"},
        headers=headers,
        timeout=60,
    ).raise_for_status()
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/coin_prediction_paths",
        params={"id": "gt.0"},
        headers=headers,
        timeout=60,
    ).raise_for_status()
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/coin_prediction_peaks",
        params={"id": "gt.0"},
        headers=headers,
        timeout=60,
    ).raise_for_status()
    log.info("Supabase 예측 테이블 초기화 완료")


def _prediction_rows_to_dicts(rows: list[tuple]) -> list[dict]:
    return [
        {
            "coin_id": r[0],
            "symbol": r[1],
            "coin_rank": r[2],
            "cycle_number": r[3],
            "cycle_name": r[4],
            "box_index": r[5],
            "phase": r[6],
            "result": r[7],
            "start_x": r[8],
            "end_x": r[9],
            "hi": r[10],
            "lo": r[11],
            "hi_day": r[12],
            "lo_day": r[13],
            "duration": r[14],
            "range_pct": r[15],
            "hi_change_pct": r[16],
            "lo_change_pct": r[17],
            "gain_pct": r[18],
            "norm_hi": r[19],
            "norm_lo": r[20],
            "norm_range_pct": r[21],
            "norm_duration": r[22],
            "norm_hi_change_pct": r[23],
            "norm_lo_change_pct": r[24],
            "norm_gain_pct": r[25],
            "is_completed": r[26],
            "is_prediction": r[27],
            "rise_days": r[28],
            "decline_days": r[29],
            "rise_rate": None,
            "decline_intensity": None,
        }
        for r in rows
    ]


def _path_rows_to_dicts(rows: list[tuple]) -> list[dict]:
    return [
        {
            "coin_id": r[0],
            "symbol": r[1],
            "cycle_number": r[2],
            "scenario": r[3],
            "start_x": r[4],
            "end_x": r[5],
            "day_x": r[6],
            "value": r[7],
        }
        for r in rows
    ]


def _peak_rows_to_dicts(rows: list[tuple]) -> list[dict]:
    return [
        {
            "coin_id": r[0],
            "symbol": r[1],
            "coin_rank": r[2],
            "cycle_number": r[3],
            "cycle_name": r[4],
            "peak_type": r[5],
            "predicted_value": r[6],
            "predicted_day": r[7],
        }
        for r in rows
    ]


def sync_predictions_to_supabase(
    pred_rows_or_conn: Any,
    path_rows: list[tuple] | None = None,
    peak_rows: list[tuple] | None = None,
):
    if path_rows is None and peak_rows is None:
        return []
    pred_rows = pred_rows_or_conn
    pred_dicts = _prediction_rows_to_dicts(pred_rows)
    path_dicts = _path_rows_to_dicts(path_rows)
    peak_dicts = _peak_rows_to_dicts(peak_rows)

    _post_rows_supabase("coin_analysis_results", pred_dicts)
    log.info("coin_analysis_results 저장 완료: %d행", len(pred_dicts))

    _post_rows_supabase("coin_prediction_paths", path_dicts)
    log.info("coin_prediction_paths 저장 완료: %d행", len(path_dicts))

    _post_rows_supabase("coin_prediction_peaks", peak_dicts)
    log.info("coin_prediction_peaks 저장 완료: %d행", len(peak_dicts))

    return pred_dicts


def main():
    log.info("=" * 65)
    log.info("032_train_and_predict_box.py 시작")
    log.info("=" * 65)
    log.info("실행 모드: supabase")
    try:
        reset_predictions_supabase()
    except ValueError:
        log.warning("Supabase 설정이 없어 reset_predictions_supabase를 건너뜁니다.")
    try:
        import duckdb
    except ImportError as e:
        raise ImportError("duckdb 패키지가 필요합니다. pip install duckdb") from e
    conn = duckdb.connect(database=":memory:")
    setup_stage_db_for_supabase(conn)
    hydrate_stage_db_from_supabase(conn)

    log.info("[1/5] 데이터 로드")
    df_all = load_box_df(conn)
    log.info("      총 %d개 박스 (is_prediction=0)", len(df_all))

    if df_all.empty:
        log.warning(
            "학습 대상 박스가 없습니다. (coin_analysis_results is_prediction=0 비어있음)"
        )
        sync_predictions_to_supabase(conn)
        conn.close()
        log.info("완료 — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return

    if (
        train_box_models is None
        or train_box_reg_group is None
        or train_bottom_models is None
        or print_feature_importance is None
    ):
        raise ImportError("xgboost/scikit-learn 기반 학습 의존성이 필요합니다.")

    df_all = df_all.copy()
    df_all["coin_id"] = df_all["coin_id"].astype(str)

    # 임시: BTC만 사용 (원복 시 아래 두 줄 제거)
    # df_all = df_all[df_all["symbol"].str.upper() == "BTC"].copy()
    # log.info("      (임시) BTC만 사용 — %d개 박스", len(df_all))

    log.info("[2/7] 연속 박스 쌍 구성")
    train_df = build_training_pairs(df_all)
    log.info("      연속 쌍 수: %d개", len(train_df))

    # BTC 박스 훈련 시 2021 + Current 사이클만 사용
    train_df_btc_full = train_df.copy()  # fallback용으로 전체 BTC 쌍 보존
    if not train_df.empty and "meta_cycle_name" in train_df.columns:
        btc_mask = train_df["meta_symbol"].astype(str).str.upper() == "BTC"
        if btc_mask.any():
            cycle_ok = (
                train_df["meta_cycle_name"]
                .astype(str)
                .str.contains("2021|Current", case=False, na=False)
            )
            train_df = train_df[~btc_mask | cycle_ok].copy()
            log.info(
                "      BTC 박스 훈련: 2021/Current 사이클만 사용 → %d개 쌍",
                len(train_df),
            )

    log.info("[3/7] Bottom 학습 데이터 구성")
    bottom_df = build_bottom_dataset(df_all)
    log.info("      Bottom 샘플 수: %d개", len(bottom_df))

    log.info("[4/7] XGBoost 박스 모델 학습 (phase + BEAR/BULL별 회귀)")
    models_by_group, metrics_by_group = train_box_models(train_df)

    # BTC_BEAR 스킵 시 → 전 사이클(2021)만으로 fallback 재학습
    if (
        "BTC_BEAR" not in models_by_group
        and "meta_cycle_name" in train_df_btc_full.columns
    ):
        log.info("      [Fallback] BTC_BEAR 스킵 → 2021 사이클만으로 재학습 시도")
        btc_bear_2021 = train_df_btc_full[
            (train_df_btc_full["meta_symbol"].astype(str).str.upper() == "BTC")
            & (
                train_df_btc_full["meta_cycle_name"]
                .astype(str)
                .str.contains("2021", case=False, na=False)
            )
            & (train_df_btc_full[TARGET_PHASE] == 0)
        ]
        mdl, met = train_box_reg_group("BTC_BEAR", btc_bear_2021)
        if mdl is not None:
            models_by_group["BTC_BEAR"] = mdl
            metrics_by_group["BTC_BEAR"] = met
            log.info(
                "      [Fallback] BTC_BEAR 2021 사이클 fallback 학습 완료 (%d개)",
                len(btc_bear_2021),
            )
        else:
            log.warning("      [Fallback] BTC_BEAR 2021 사이클도 샘플 부족 → 예측 불가")

    log.info("검증 오차(RMSE) / 정확도(Acc) 요약:")
    for grp_name, metrics in metrics_by_group.items():
        if grp_name in ("BTC", "ALT"):
            acc_ph = metrics.get(TARGET_PHASE)
            if acc_ph is not None:
                log.info(
                    "  [%s] phase     Accuracy = %.3f  (%.1f%%)",
                    grp_name,
                    acc_ph,
                    acc_ph * 100,
                )
        else:
            rmse_hi = metrics.get(TARGET_HI)
            rmse_lo = metrics.get(TARGET_LO)
            rmse_dur = metrics.get(TARGET_DUR)
            if rmse_hi is not None:
                log.info(
                    "  [%s] next_hi   RMSE = %.4f  (원래단위 오차 ≈ ±%.1f%%)",
                    grp_name,
                    rmse_hi,
                    float(np.expm1(rmse_hi)),
                )
            if rmse_lo is not None:
                log.info(
                    "  [%s] next_lo   RMSE = %.4f  (원래단위 오차 ≈ ±%.1f%%)",
                    grp_name,
                    rmse_lo,
                    float(np.expm1(rmse_lo)),
                )
            if rmse_dur is not None:
                log.info(
                    "  [%s] next_dur  RMSE = %.4f  (원래단위 오차 ≈ ±%dd)",
                    grp_name,
                    rmse_dur,
                    int(np.expm1(rmse_dur)),
                )

    log.info("[5/7] 피처 중요도 분석")
    print_feature_importance(models_by_group)

    log.info("[6/7] Bottom 전용 모델 학습")
    bottom_models = train_bottom_models(bottom_df)

    conn.execute(CREATE_PATHS_SQL)
    conn.execute(CREATE_PEAKS_SQL)
    conn.execute("DELETE FROM coin_prediction_paths")
    conn.execute("DELETE FROM coin_prediction_peaks")
    conn.commit()

    log.info("[7/7] 예측 실행")
    pred_rows, path_rows, peak_rows, pred_count, skip_count = predict_outputs(
        conn, df_all, train_df, models_by_group, bottom_models, {}
    )
    log.info(
        "예측 생성 완료: 코인 %d개  스킵 %d개  | pred_rows=%d  path_rows=%d  peak_rows=%d",
        pred_count,
        skip_count,
        len(pred_rows),
        len(path_rows),
        len(peak_rows),
    )

    pred_dicts = sync_predictions_to_supabase(pred_rows, path_rows, peak_rows)

    print_prediction_summary_rows(pred_dicts)

    conn.close()
    log.info("완료 — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("다음 단계: python 033_visualizer_html.py  (노란 점선 예측 박스 확인)")


if __name__ == "__main__":
    main()
