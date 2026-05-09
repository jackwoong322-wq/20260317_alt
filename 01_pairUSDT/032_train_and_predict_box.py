"""032_train_and_predict_box.py

XGBoost 기반 다음 박스권 예측 및 DB 저장

Usage: python 032_train_and_predict_box.py
"""

import logging
import math
import os
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
DASHBOARD_CACHE_REFRESH_URL_ENV = "DASHBOARD_CACHE_REFRESH_URL"
DASHBOARD_CACHE_REFRESH_SECRET_ENV = "DASHBOARD_CACHE_REFRESH_SECRET"


class _NoOpConn:
    def close(self):
        return None


class PredictionValidationError(ValueError):
    """Raised when generated box scenarios violate chart-facing invariants."""


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


def _safe_int(value, default: int | None = None) -> int | None:
    if value is None or pd.isna(value):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return int(parsed)


def _safe_float(value, default: float | None = None) -> float | None:
    if value is None or pd.isna(value):
        return default
    parsed = float(value)
    if not math.isfinite(parsed):
        return default
    return parsed


def _active_box_lookup(observed_df: pd.DataFrame | None) -> dict[tuple[str, int, int], dict]:
    if observed_df is None or observed_df.empty:
        return {}
    required_cols = {"coin_id", "cycle_number", "box_index", "is_completed", "is_prediction"}
    if not required_cols.issubset(set(observed_df.columns)):
        return {}

    active_rows = observed_df[
        (observed_df["is_prediction"].astype(int) == 0)
        & (observed_df["is_completed"].astype(int) == 0)
    ]
    lookup = {}
    for _, row in active_rows.iterrows():
        key = (
            str(row["coin_id"]),
            int(row["cycle_number"]),
            int(row["box_index"]),
        )
        lookup[key] = row.to_dict()
    return lookup


def _observed_end_lookup(observed_df: pd.DataFrame | None) -> dict[tuple[str, int], int]:
    if observed_df is None or observed_df.empty:
        return {}
    required_cols = {"coin_id", "cycle_number", "end_x"}
    if not required_cols.issubset(set(observed_df.columns)):
        return {}
    lookup = {}
    for (coin_id, cycle_number), grp in observed_df.groupby(["coin_id", "cycle_number"]):
        lookup[(str(coin_id), int(cycle_number))] = int(grp["end_x"].max())
    return lookup


def _validate_prediction_dicts(
    pred_dicts: list[dict],
    path_dicts: list[dict],
    peak_dicts: list[dict],
    observed_df: pd.DataFrame | None = None,
) -> None:
    """Validate generated box scenarios before publishing them to Supabase."""
    active_lookup = _active_box_lookup(observed_df)
    observed_end_by_cycle = _observed_end_lookup(observed_df)
    path_ranges: dict[tuple[str, int, str], list[int]] = {}
    active_predictions: set[tuple[str, int, int]] = set()
    prediction_keys: set[tuple[str, int, int]] = set()
    errors: list[str] = []

    for idx, row in enumerate(pred_dicts):
        prefix = (
            f"pred[{idx}] {row.get('symbol')} "
            f"cy={row.get('cycle_number')} box={row.get('box_index')}"
        )
        if _safe_int(row.get("is_prediction"), 0) != 1:
            errors.append(f"{prefix}: is_prediction must be 1")

        start_x = _safe_int(row.get("start_x"))
        end_x = _safe_int(row.get("end_x"))
        duration = _safe_int(row.get("duration"))
        hi = _safe_float(row.get("hi"))
        lo = _safe_float(row.get("lo"))
        hi_day = _safe_int(row.get("hi_day"), end_x)
        lo_day = _safe_int(row.get("lo_day"), end_x)

        if start_x is None or end_x is None or start_x > end_x:
            errors.append(f"{prefix}: invalid start_x/end_x")
        if hi is None or lo is None or hi < lo:
            errors.append(f"{prefix}: hi must be >= lo")
        if start_x is not None and end_x is not None:
            expected_duration = end_x - start_x + 1
            if duration is not None and duration != expected_duration:
                errors.append(
                    f"{prefix}: duration {duration} != {expected_duration}"
                )
            if hi_day is not None and not (start_x <= hi_day <= end_x):
                errors.append(f"{prefix}: hi_day outside box range")
            if lo_day is not None and not (start_x <= lo_day <= end_x):
                errors.append(f"{prefix}: lo_day outside box range")

        result = str(row.get("result") or "")
        pred_key = (
            str(row.get("coin_id")),
            _safe_int(row.get("cycle_number"), -1),
            _safe_int(row.get("box_index"), -1),
        )
        prediction_keys.add(pred_key)
        scenario = "bull" if str(row.get("phase") or "").upper() == "BULL" else "bear"
        if start_x is not None and end_x is not None:
            range_key = (
                str(row.get("coin_id")),
                _safe_int(row.get("cycle_number"), -1),
                scenario,
            )
            if range_key not in path_ranges:
                path_ranges[range_key] = [start_x, end_x]
            else:
                path_ranges[range_key][0] = min(path_ranges[range_key][0], start_x)
                path_ranges[range_key][1] = max(path_ranges[range_key][1], end_x)

        if result in {"PRED_BEAR_ACTIVE", "PRED_BULL_ACTIVE"}:
            active_predictions.add(pred_key)
            active = active_lookup.get(pred_key)
            if not active:
                errors.append(f"{prefix}: active prediction has no observed ACTIVE row")
            else:
                active_start = _safe_int(active.get("start_x"))
                active_end = _safe_int(active.get("end_x"))
                if start_x != active_start:
                    errors.append(
                        f"{prefix}: active prediction start_x {start_x} != observed {active_start}"
                    )
                if end_x is not None and active_end is not None and end_x < active_end:
                    errors.append(
                        f"{prefix}: active prediction end_x {end_x} < observed {active_end}"
                    )

    for active_key, active in active_lookup.items():
        if active_key in prediction_keys and active_key not in active_predictions:
            errors.append(
                "active prediction for "
                f"{active.get('symbol', active_key[0])} cy={active_key[1]} "
                f"box={active_key[2]} must use PRED_BEAR_ACTIVE/PRED_BULL_ACTIVE"
            )
        if active_key not in prediction_keys:
            errors.append(
                "missing active completion prediction for "
                f"{active.get('symbol', active_key[0])} cy={active_key[1]} box={active_key[2]}"
            )

    for idx, row in enumerate(path_dicts):
        prefix = (
            f"path[{idx}] {row.get('symbol')} "
            f"cy={row.get('cycle_number')} scenario={row.get('scenario')}"
        )
        scenario = str(row.get("scenario") or "").lower()
        if scenario not in {"bear", "bull"}:
            errors.append(f"{prefix}: invalid scenario")
        start_x = _safe_int(row.get("start_x"))
        end_x = _safe_int(row.get("end_x"))
        day_x = _safe_int(row.get("day_x"))
        value = _safe_float(row.get("value"))
        range_key = (
            str(row.get("coin_id")),
            _safe_int(row.get("cycle_number"), -1),
            scenario,
        )
        allowed_range = path_ranges.get(range_key)
        if start_x is None or end_x is None or day_x is None:
            errors.append(f"{prefix}: day_x outside path range")
        elif start_x > end_x:
            errors.append(f"{prefix}: invalid start_x/end_x")
        elif allowed_range is None:
            errors.append(f"{prefix}: no matching prediction scenario")
        elif allowed_range is not None:
            min_day = min(allowed_range[0], start_x)
            max_day = max(allowed_range[1], end_x)
            if not (min_day <= day_x <= max_day):
                errors.append(f"{prefix}: day_x outside scenario range")
        elif not (start_x <= day_x <= end_x):
            errors.append(f"{prefix}: day_x outside path range")
        if value is None or value <= 0:
            errors.append(f"{prefix}: value must be positive")

    for idx, row in enumerate(peak_dicts):
        prefix = (
            f"peak[{idx}] {row.get('symbol')} "
            f"cy={row.get('cycle_number')} type={row.get('peak_type')}"
        )
        predicted_value = _safe_float(row.get("predicted_value"))
        predicted_day = _safe_int(row.get("predicted_day"))
        peak_type = str(row.get("peak_type") or "").upper()
        if peak_type not in {"PEAK", "BOTTOM"}:
            errors.append(f"{prefix}: invalid peak_type")
        if predicted_value is None or predicted_value <= 0:
            errors.append(f"{prefix}: predicted_value must be positive")
        if predicted_day is None:
            errors.append(f"{prefix}: predicted_day is required")
        key = (str(row.get("coin_id")), _safe_int(row.get("cycle_number"), -1))
        observed_end = observed_end_by_cycle.get(key)
        if (
            observed_end is not None
            and predicted_day is not None
            and predicted_day < observed_end
        ):
            errors.append(
                f"{prefix}: predicted_day {predicted_day} < observed end {observed_end}"
            )

    if errors:
        preview = "; ".join(errors[:5])
        suffix = "" if len(errors) <= 5 else f"; ... +{len(errors) - 5} more"
        raise PredictionValidationError(preview + suffix)


def _prediction_scope_summary(pred_dicts: list[dict]) -> dict:
    summary = {
        "active_completion_rows": 0,
        "next_box_rows": 0,
        "extended_only_rows": 0,
        "default_visible_rows": 0,
    }
    by_cycle: dict[tuple[str, int], list[dict]] = {}
    for row in pred_dicts:
        key = (str(row.get("coin_id")), int(row.get("cycle_number") or 0))
        by_cycle.setdefault(key, []).append(row)

    for rows in by_cycle.values():
        ordered = sorted(
            rows,
            key=lambda r: (
                int(r.get("box_index") or 0),
                int(r.get("start_x") or 0),
                str(r.get("result") or ""),
            ),
        )
        active_rows = [
            r
            for r in ordered
            if str(r.get("result") or "") in {"PRED_BEAR_ACTIVE", "PRED_BULL_ACTIVE"}
        ]
        future_rows = [r for r in ordered if r not in active_rows]
        default_rows = active_rows + future_rows[:1]
        summary["active_completion_rows"] += len(active_rows)
        summary["next_box_rows"] += min(len(future_rows), 1)
        summary["extended_only_rows"] += max(len(future_rows) - 1, 0)
        summary["default_visible_rows"] += len(default_rows)

    return summary


def log_prediction_scenario_summary(
    pred_dicts: list[dict], path_dicts: list[dict], peak_dicts: list[dict]
) -> dict:
    summary = _prediction_scope_summary(pred_dicts)
    log.info(
        "Box scenario summary: active_completion=%d next_box=%d "
        "default_visible=%d extended_only=%d paths=%d markers=%d",
        summary["active_completion_rows"],
        summary["next_box_rows"],
        summary["default_visible_rows"],
        summary["extended_only_rows"],
        len(path_dicts),
        len(peak_dicts),
    )
    return summary


def sync_predictions_to_supabase(
    pred_rows_or_conn: Any,
    path_rows: list[tuple] | None = None,
    peak_rows: list[tuple] | None = None,
    observed_df: pd.DataFrame | None = None,
):
    if path_rows is None and peak_rows is None:
        return []
    pred_rows = pred_rows_or_conn
    pred_dicts = _prediction_rows_to_dicts(pred_rows)
    path_dicts = _path_rows_to_dicts(path_rows)
    peak_dicts = _peak_rows_to_dicts(peak_rows)

    if not pred_dicts:
        log.warning(
            "No box scenario rows generated; skipping Supabase publish and preserving existing predictions."
        )
        return []

    _validate_prediction_dicts(pred_dicts, path_dicts, peak_dicts, observed_df)
    log_prediction_scenario_summary(pred_dicts, path_dicts, peak_dicts)

    reset_predictions_supabase()
    _post_rows_supabase("coin_analysis_results", pred_dicts)
    log.info("coin_analysis_results 저장 완료: %d행", len(pred_dicts))

    _post_rows_supabase("coin_prediction_paths", path_dicts)
    log.info("coin_prediction_paths 저장 완료: %d행", len(path_dicts))

    _post_rows_supabase("coin_prediction_peaks", peak_dicts)
    log.info("coin_prediction_peaks 저장 완료: %d행", len(peak_dicts))

    return pred_dicts


def refresh_dashboard_cache_after_save() -> bool:
    refresh_url = os.getenv(DASHBOARD_CACHE_REFRESH_URL_ENV)
    refresh_secret = os.getenv(DASHBOARD_CACHE_REFRESH_SECRET_ENV)
    if not refresh_url or not refresh_secret:
        log.warning(
            "Dashboard cache refresh skipped: %s/%s not configured",
            DASHBOARD_CACHE_REFRESH_URL_ENV,
            DASHBOARD_CACHE_REFRESH_SECRET_ENV,
        )
        return False

    try:
        res = requests.post(
            refresh_url,
            headers={"X-Internal-Secret": refresh_secret},
            timeout=60,
        )
        if not res.ok:
            body = (res.text or "")[:500]
            log.warning(
                "Dashboard cache refresh failed: status=%s body=%s",
                res.status_code,
                body,
            )
            return False
        payload = res.json()
        if not payload.get("ok"):
            log.warning("Dashboard cache refresh returned failure: %s", payload)
            return False
        log.info(
            "Dashboard cache refreshed: data_version=%s cache_status=%s",
            payload.get("data_version"),
            payload.get("cache_status"),
        )
        return True
    except Exception as exc:
        log.warning("Dashboard cache refresh request failed: %s", exc)
        return False


def sync_predictions_to_supabase_and_refresh(
    pred_rows_or_conn: Any,
    path_rows: list[tuple] | None = None,
    peak_rows: list[tuple] | None = None,
    observed_df: pd.DataFrame | None = None,
):
    pred_dicts = sync_predictions_to_supabase(
        pred_rows_or_conn, path_rows, peak_rows, observed_df
    )
    if not pred_dicts:
        return pred_dicts
    refresh_dashboard_cache_after_save()
    return pred_dicts


def main():
    log.info("=" * 65)
    log.info("032_train_and_predict_box.py 시작")
    log.info("=" * 65)
    log.info("실행 모드: supabase")
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
    train_source_df = df_all[
        (df_all["is_prediction"].astype(int) == 0)
        & (df_all["is_completed"].astype(int) == 1)
    ].copy()
    train_df = build_training_pairs(train_source_df)
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

    if not pred_rows:
        log.warning(
            "생성된 box scenario가 없어 Supabase publish를 건너뜁니다. 기존 예측을 보존합니다."
        )
        conn.close()
        log.info("완료 — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return

    pred_dicts = sync_predictions_to_supabase_and_refresh(
        pred_rows, path_rows, peak_rows, df_all
    )

    print_prediction_summary_rows(pred_dicts)

    conn.close()
    log.info("완료 — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("다음 단계: python 033_visualizer_html.py  (노란 점선 예측 박스 확인)")


if __name__ == "__main__":
    main()
