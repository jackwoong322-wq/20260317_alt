"""Model prediction helpers."""

import numpy as np
import pandas as pd

from lib.common.config import (
    FEATURE_COLS,
    FEATURE_COLS_BEAR,
    FEATURE_COLS_BTC_REG,
    MAX_PRED_HI,
    MAX_PRED_LO,
    TARGET_DUR,
    TARGET_HI,
    TARGET_LO,
    TARGET_PHASE,
)


def _expected_model_features(model, fallback_cols: list[str]) -> list[str]:
    """Return the feature order recorded by the model when available."""
    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is not None:
        return [str(name) for name in feature_names]

    get_booster = getattr(model, "get_booster", None)
    if callable(get_booster):
        booster = get_booster()
        feature_names = getattr(booster, "feature_names", None)
        if feature_names:
            return [str(name) for name in feature_names]

    return list(fallback_cols)


def _select_model_features(
    X_pred: pd.DataFrame, model, fallback_cols: list[str]
) -> pd.DataFrame:
    cols = _expected_model_features(model, fallback_cols)
    missing = [col for col in cols if col not in X_pred.columns]
    if missing:
        raise ValueError(
            "Prediction feature vector is missing required model columns: "
            + ", ".join(missing)
        )
    return X_pred[cols]


def get_model_predictions(
    group_models: dict, X_pred: pd.DataFrame, last: pd.Series, reg_key: str = ""
):
    """Get hi/lo/dur and phase probabilities from group models."""
    if reg_key in ("BTC_BEAR", "BTC_BULL"):
        fallback_reg_cols = FEATURE_COLS_BTC_REG
    else:
        fallback_reg_cols = FEATURE_COLS_BEAR if reg_key.endswith("_BEAR") else FEATURE_COLS

    X_hi = _select_model_features(X_pred, group_models[TARGET_HI], fallback_reg_cols)
    X_lo = _select_model_features(X_pred, group_models[TARGET_LO], fallback_reg_cols)
    X_dur = _select_model_features(X_pred, group_models[TARGET_DUR], fallback_reg_cols)
    X_phase = _select_model_features(X_pred, group_models[TARGET_PHASE], FEATURE_COLS)

    pred_norm_hi = float(group_models[TARGET_HI].predict(X_hi)[0])
    pred_norm_lo = float(group_models[TARGET_LO].predict(X_lo)[0])
    pred_norm_dur = float(group_models[TARGET_DUR].predict(X_dur)[0])
    phase_proba = group_models[TARGET_PHASE].predict_proba(X_phase)[0]
    prob_bear, prob_bull = float(phase_proba[0]), float(phase_proba[1])

    last_hi = float(last["hi"]) if last["hi"] else 100.0
    last_lo = float(last["lo"]) if last["lo"] else 50.0
    hi_chg_pct = float(np.sign(pred_norm_hi) * np.expm1(abs(pred_norm_hi)))
    lo_chg_pct = float(np.sign(pred_norm_lo) * np.expm1(abs(pred_norm_lo)))
    pred_hi_bull = min(max(last_lo * (1.0 + hi_chg_pct / 100.0), 0.01), MAX_PRED_HI)
    pred_lo_bull = min(max(pred_hi_bull * (1.0 + lo_chg_pct / 100.0), 0.01), MAX_PRED_LO)
    pred_dur_bull = max(int(round(np.expm1(pred_norm_dur))), 1)
    if pred_hi_bull < pred_lo_bull:
        pred_hi_bull, pred_lo_bull = pred_lo_bull, pred_hi_bull
    return pred_norm_hi, pred_norm_lo, pred_norm_dur, prob_bear, prob_bull, pred_hi_bull, pred_lo_bull, pred_dur_bull


def find_most_similar_pattern(train_df: pd.DataFrame, feat_vec: pd.DataFrame) -> tuple[str, int, int, float]:
    """Find most similar training pattern by L2 distance."""
    X_train = train_df[FEATURE_COLS].to_numpy(dtype=float)
    v = feat_vec[FEATURE_COLS].to_numpy(dtype=float)[0]
    dists = np.linalg.norm(X_train - v, axis=1)
    idx = int(np.argmin(dists))
    best = train_df.iloc[idx]
    sim = float(1.0 / (1.0 + dists[idx]))
    return str(best["meta_symbol"]), int(best["meta_cycle"]), int(best["meta_box_index"]), sim
