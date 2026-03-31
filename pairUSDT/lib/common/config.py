import logging
import os
from pathlib import Path
from dotenv import load_dotenv

_PAIRUSDT_ROOT = Path(__file__).resolve().parents[2]  # pairUSDT
_WORKSPACE_ROOT = _PAIRUSDT_ROOT.parent

# 실행 위치와 무관하게 .env 로드
load_dotenv(_WORKSPACE_ROOT / ".env")
load_dotenv(_PAIRUSDT_ROOT / ".env", override=False)

# pairUSDT 폴더 내 crypto_usdt.db 사용 (실행 위치와 무관)
DB_PATH = str(_PAIRUSDT_ROOT / "crypto_usdt.db")

# DB 모드: sqlite(기본) | supabase
DB_MODE = os.getenv("DB_MODE", "sqlite")

# Supabase 연결 정보 (DB_MODE=supabase 시 사용)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

MIN_BOX_DAYS = 5
BEAR_BREAKOUT_RATIO = 0.98
BULL_BREAKOUT_RATIO = 1.10
BEAR_REBOUND_RATIO = 1.05
BULL_DRAWDOWN_RATIO = 0.95
BULL_PEAK_LOOKAHEAD = 15

MIN_BEAR_DURATION = 14
MIN_BULL_DURATION = 14
MAX_BEAR_CHAIN = 5  # Bear 체인 최대 박스 수 (예측 상한)
MAX_BULL_CHAIN = 5  # BULL 반등 구간 최대 박스 개수 (과도한 박스 방지)
MAX_PRED_HI = 299.8
MAX_PRED_LO = 150.0

# BTC 사이클 박스 수 예측 가드 (선형 회귀 후 보정)
MIN_BOX_COUNT = 1  # Bear/Bull 박스 수 최솟값
BEAR_GUARD_DELTA = (
    1  # Bear: prevCycle.bearCount - BEAR_GUARD_DELTA 이상 유지 (급감 방지)
)

# BEAR chain range 발산 억제: chain_i별 range_pct 상한 (단조 감소)
BEAR_CHAIN_MAX_RANGE_INIT = 32.0  # chain_i=0 상한 (%) — 첫 박스 20~30% 수준
BEAR_CHAIN_RANGE_DECAY_RATE = 0.96  # 박스당 완만한 감소
BEAR_CHAIN_HI_DECAY_MIN = 0.97  # 매 박스 hi 최소 감소율 (이전 hi 대비 3% 하락 보장)

# BTC 사이클 가중치: 최근 사이클이 과거 대비 압도적으로 높도록 exp 스케일 강도 (클수록 최근 비중 증가)
BTC_CYCLE_WEIGHT_EXP_COEF = 2.5
# Cy1 제외 후 사이클별 증가폭으로 추정할 때, 증가폭 산출이 불가할 때 쓰는 기본 증가율 (%)
BTC_BOTTOM_CYCLE_INCREASE_PCT = 7.0

FEATURE_COLS = [
    "norm_range_pct",
    "norm_hi_change_pct",
    "norm_lo_change_pct",
    "norm_gain_pct",
    "norm_duration",
    "hi_rel_to_cycle_lo",
    "lo_rel_to_cycle_lo",
    "coin_rank",
    "is_bull",
    "box_index",
    "cycle_progress_ratio",
    "cycle_low_pos_ratio",
    "rel_to_prev_cycle_low",
    "rel_to_prev_support_mean",
    "phase_box_index_ratio",
    "phase_avg_box_count",
    "btc_prev_peak_ratio",
    "log_cycle_number",
]

# BEAR 박스도 BULL과 동일한 17개 피처 사용 (norm_hi_change_pct 포함)
FEATURE_COLS_BEAR = list(FEATURE_COLS)

# BTC 전용 회귀: log_cycle_number 제외 (소표본 과적합 방지)
FEATURE_COLS_BTC_REG = [c for c in FEATURE_COLS if c != "log_cycle_number"]

TARGET_HI = "next_hi_change_pct"
TARGET_LO = "next_lo_change_pct"
TARGET_DUR = "next_norm_duration"
TARGET_PHASE = "next_is_bull"

# 박스 훈련/예측 시 해당 피처에 곱할 가중치 (스케일 up → 분할 시 더 많이 반영)
BOX_FEATURE_WEIGHTS = {
    "norm_hi_change_pct": 1.5,
    "norm_lo_change_pct": 1.0,
}

XGB_REG_PARAMS = dict(
    n_estimators=400,
    max_depth=4,
    learning_rate=0.04,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    verbosity=0,
)

# BTC 회귀 전용: 소표본 과적합 완화 (정규화 강화, 복잡도 축소)
XGB_REG_PARAMS_BTC = dict(
    n_estimators=400,
    max_depth=3,
    learning_rate=0.04,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    reg_alpha=0.5,
    reg_lambda=2.0,
    random_state=42,
    verbosity=0,
)

XGB_CLF_PARAMS = dict(
    n_estimators=300,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbosity=0,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
