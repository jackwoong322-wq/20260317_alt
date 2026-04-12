# Bear vs Bull 체인 로직 비교

## 1. 구조

| 구분 | Bear | Bull |
|------|------|------|
| **진입점** | `predict_box_bear.build_bear_chain()` | `predict_box_bull.build_bull_chain()` |
| **체인 전용 모듈** | 있음: `predict_box_bear_chain.py` | 없음 (모두 `predict_box_bull.py` 안에 있음) |
| **실제 체인 실행** | `run_bear_chain()` (스텝 반복) | `build_bull_chain()` 내부에서 한 번에 처리 |

## 2. 박스 예측 방식 (가장 큰 차이)

### Bear
- **스텝마다 회귀 모델 사용**
  - `run_bear_chain` → 루프에서 `run_bear_chain_step` 호출
  - 각 스텝에서 `predict_bear_box(group_models, feat, avg_cycle_days, reg_feat_cols)` 호출
    - `TARGET_HI`, `TARGET_LO`, `TARGET_DUR` 모델로 **b_hi_chg_pct, b_lo_chg_pct, b_dur** 예측
  - `compute_step_box_bounds(pred, ...)` 로 **b_hi, b_lo, b_start, b_end, b_hi_day, b_lo_day** 계산
- 모델이 없으면 `_build_bear_chain_heuristic()` 폴백 (휴리스틱으로 b_hi/b_lo 계산)

### Bull
- **체인 내 박스는 회귀 모델 미사용**
  - `build_bull_chain` 인자: `pred_hi_bull`, `pred_lo_bull`, `pred_dur_bull` (전체 구간용, 상위에서 한 번만 예측)
  - 체인 내 각 박스의 hi/lo는 **ease 보간으로만** 계산:
    - `positions = [_ease(i / n_boxes) for i in range(n_boxes + 1)]`
    - `bull_lo = bottom_lo + (peak_hi - bottom_lo) * pos_lo`
    - `bull_hi = bottom_lo + (peak_hi - bottom_lo) * pos_hi`
  - 박스별 기간은 `b_start`, `b_end`를 동일한 보간으로 나눔

즉, **Bear는 박스마다 모델 예측**, **Bull은 전체만 모델 예측 후 구간만 나눔**.

## 3. 경로 생성 (동일한 패턴)

| 구분 | Bear | Bull |
|------|------|------|
| **함수** | `build_bear_box_day_points()` | `build_bull_box_day_points()` |
| **순서** | 저점(시작) → 고점 → 다음 박스 저점 | 시작점(Bottom) → 고점 → 저점 → 다음 고점 |
| **호출 시점** | `run_bear_chain` 2단계: 스펙 수집 후 한 번에 반복 호출 | `build_bull_chain` 마지막: path_specs 수집 후 반복 호출 |

## 4. 요약

- **Bear**: `predict_box_bear_chain.run_bear_chain` → 스텝마다 **predict_bear_box(모델)** 로 박스 hi/lo/dur 예측 → row + path_spec 수집 → `build_bear_box_day_points` 반복.
- **Bull**: `build_bull_chain` 한 함수에서 박스 개수·구간만 정하고, **모델 없이** ease로 hi/lo 분배 → row + path_spec 수집 → `build_bull_box_day_points` 반복.

Bull을 Bear와 같게 하려면:
- **predict_box_bull_chain.py** 같은 체인 전용 모듈을 두고,
- 스텝마다 **Bull용 회귀 모델**(predict_bull_box 등)을 호출해 박스별 hi/lo/dur를 예측한 뒤,
- `run_bull_chain` → `run_bull_chain_step` 반복 + 2단계에서 `build_bull_box_day_points` 반복하는 구조로 맞추면 됨.
