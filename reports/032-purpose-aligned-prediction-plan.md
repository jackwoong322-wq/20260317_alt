# 032 Purpose-Aligned Prediction Planning

## Goal

`01_pairUSDT/032_train_and_predict_box.py`를 `reports/program-purpose-critical-review.md`의 목적에 맞게 개선하기 위한 기획서다.

핵심 방향은 다음이다.

> 032는 확정 가격 예측기나 매매 신호 생성기가 아니라, BTC cycle 기준 current active box의 가능한 BEAR/BULL 완료 시나리오와 제한된 다음 박스 범위를 생성하여 차트 사용자가 현재 위치, 하방 위험, 상방 가능성, 시간 범위를 비교 판단하도록 돕는 분석 보조 배치다.

## Current Role of `032_train_and_predict_box.py`

현재 032는 다음 작업을 한 번에 수행한다.

1. Supabase의 기존 prediction 데이터를 삭제한다.
2. `coin_analysis_results`에서 `is_prediction = 0`인 실제 box rows를 가져온다.
3. DuckDB in-memory stage DB에 적재한다.
4. 완료된 box pair로 training data를 만든다.
5. XGBoost/scikit-learn 기반 box model과 bottom model을 학습한다.
6. current cycle의 active box를 기준으로 prediction rows, prediction paths, peak/bottom rows를 생성한다.
7. Supabase prediction tables에 저장한다.
8. dashboard cache refresh를 요청한다.

현재 구조는 batch pipeline으로는 타당하지만, 산출물이 사용자에게 **단일 정답 예측**처럼 보일 위험이 있다.

## Product Definition

032의 산출물은 다음처럼 정의한다.

- `prediction`이 아니라 `scenario`다.
- `price forecast`가 아니라 `box scenario`다.
- `buy/sell signal`이 아니라 `decision-support context`다.
- `exact daily path`가 아니라 `interpolated scenario path`다.
- `confirmed result`가 아니라 `observed active box 이후의 possible outcome`이다.

## User Questions 032 Should Answer

032는 차트 사용자가 다음 질문에 답하도록 도와야 한다.

- 현재 active box가 아직 진행 중인가?
- 현재 active box가 BEAR 쪽으로 더 내려가며 끝날 가능성이 있는가?
- 현재 active box가 BULL 전환으로 해석될 가능성이 있는가?
- 현재 box의 예상 high/low/end day 범위는 어디인가?
- 현재 box 이후 다음 한두 개 box의 high/low/duration은 어느 정도인가?
- bottom 후보가 있다면 지금보다 얼마나 아래이고, 며칠 뒤인가?
- peak 후보가 있다면 현재 cycle 기준 어느 위치이고, 며칠 뒤인가?
- 이 예측은 model 기반인가, heuristic/fallback/cap이 많이 들어간 결과인가?
- 기본 화면에서 볼 예측인가, `EXTENDED`에서만 볼 먼 미래 예측인가?

## Critical Design Principles

### 1. Observed Data and Prediction Must Stay Separate

관측 active row는 절대 prediction logic이 덮어쓰면 안 된다.

Observed active box:

| Field | Value |
|---|---|
| `is_prediction` | `0` |
| `is_completed` | `0` |
| `result` | `ACTIVE` |
| `box_index` | actual active box index |
| `start_x/end_x` | observed range |
| `hi/lo` | observed/provisional values |

Predicted active completion:

| Field | Value |
|---|---|
| `is_prediction` | `1` |
| `is_completed` | `0` |
| `result` | `PRED_BEAR_ACTIVE` or `PRED_BULL_ACTIVE` |
| `box_index` | same as observed active box |
| `start_x` | observed active `start_x` |
| `end_x` | predicted final active box end |
| `hi/lo` | predicted final active box high/low |

### 2. Prediction Starts From the Current Active Box

현재 active box가 있으면 032는 다음 box부터 예측하면 안 된다.

우선순위:

1. current active box의 최종 완료 형태 예측
2. 그 이후의 next box 예측
3. 필요 시 `EXTENDED` 영역의 future box 예측

### 3. Default Forecast Must Be Short and Interpretable

기본 화면은 멀리 있는 미래 forecast를 많이 보여주기보다, 현재 판단에 필요한 영역만 보여줘야 한다.

Default scope:

- observed active box
- predicted active completion
- next prediction box
- bottom/peak marker가 가까운 판단에 필요한 경우

Extended scope:

- 먼 미래 prediction chain
- later peak candidate
- long-range bull/bear path

### 4. Prediction Path Is Not Daily Price Forecast

`coin_prediction_paths`는 box scenario를 연결하는 시각화 path다.

기획서와 이후 UI/tooltip은 다음 의미를 분명히 해야 한다.

- line의 각 점은 정확한 daily close 예측이 아니다.
- path는 predicted box의 high/low/end day를 연결하는 보간선이다.
- 특정 day의 value를 매매 기준 가격으로 직접 해석하면 안 된다.

### 5. Scenario Evidence Should Be Preserved

현재 032 내부에는 판단 근거가 존재하지만 대부분 저장되지 않는다.

예:

- `prob_bear`
- `prob_bull`
- `force_bear`
- `force_bear_reason`
- bottom model 사용 여부
- peak model 사용 여부
- 2021 pattern reference
- BTC anchor influence
- cap/floor 적용 여부
- fallback model 사용 여부
- similar pattern symbol/cycle/box
- similarity score

목적에 맞게 개선하려면 이런 근거를 최소한 log나 sidecar output으로 남겨야 한다.

## Proposed Planning Scope

### MVP Scope

Supabase schema를 크게 바꾸지 않고, 현재 구조 안에서 032의 의미와 안정성을 개선한다.

MVP 목표:

1. active box 중심 시나리오 생성 원칙을 명확히 유지한다.
2. 관측 active row를 절대 mutation하지 않는지 테스트로 고정한다.
3. training label에 incomplete/active row가 섞이지 않는지 테스트로 고정한다.
4. prediction 결과를 default/extended 범위로 구분할 수 있는 기준을 문서화한다.
5. prediction rows와 paths가 같은 visibility scope를 따르도록 한다.
6. 예측 생성 후 저장 전에 sanity validation을 수행한다.
7. Supabase 저장 성공 후에만 dashboard cache refresh를 호출한다.
8. refresh 실패는 저장 성공을 실패로 만들지 않되 warning을 남긴다.

### Future Scope

다음은 목적에는 맞지만 MVP를 넘는 항목이다.

- prediction run id 추가
- scenario metadata table 추가
- quality flags 컬럼 추가
- probability/confidence interval 컬럼 추가
- delete-then-insert 대신 publish snapshot 방식 도입
- model evaluation report 저장
- dashboard tooltip에 prediction rationale 표시
- uncertainty band 시각화
- exact schema migration

## Required Functional Changes

### 1. Rename Mental Model From Prediction to Scenario

코드 파일명과 기존 DB 테이블명은 유지하되, 032 내부의 주석/log/summary에서 다음 표현을 우선 사용한다.

- `prediction` 단독 표현보다 `box scenario`
- `예측값`보다 `시나리오 값`
- `정답`처럼 보이는 문구 금지
- `확정` 대신 `candidate`, `scenario`, `forecast layer`

주의: 기존 table/column 이름은 호환성 때문에 유지한다.

### 2. Add Prediction Output Sanity Validation

Supabase 저장 전에 `pred_rows`, `path_rows`, `peak_rows`를 검증한다.

Validation rules:

- prediction row의 `is_prediction == 1`
- active completion row는 observed active row와 같은 `box_index`
- active completion row의 `start_x == observed active start_x`
- active completion row의 `end_x >= observed active end_x`
- future prediction row의 `start_x > predicted active completion start_x`
- `hi >= lo`
- `start_x <= hi_day <= end_x`
- `start_x <= lo_day <= end_x`
- `duration == end_x - start_x + 1`
- path row의 `day_x`가 해당 scenario의 allowed range 안에 있음
- peak/bottom marker의 `predicted_day`가 현재 observed end보다 과거로 가지 않음

검증 실패 시:

- Supabase에 저장하지 않는다.
- dashboard cache refresh를 호출하지 않는다.
- 실패 이유를 log에 남긴다.

### 3. Preserve Scenario Scope

032는 차트가 default/extended를 구분할 수 있도록 결과를 일관되게 생성해야 한다.

현재 DB schema상 별도 `horizon` 컬럼이 없다면 MVP에서는 다음 규칙을 사용한다.

- default: active prediction row + active 이후 첫 future prediction row
- extended: 그 이후 future prediction rows

032에서 보장할 것:

- path rows도 같은 row scope와 맞게 생성된다.
- peak/bottom rows가 먼 미래 marker라면 visualizer가 extended에서만 보이도록 해석 가능해야 한다.
- default path가 extended box까지 길게 이어져 보이지 않도록 한다.

### 4. Keep Training Data Strictly Historical

`build_training_pairs()`는 이미 `curr`와 `nxt` 모두 `is_completed = 1`이어야 한다는 원칙을 가져야 한다.

032 기획상 이 규칙은 P0이다.

검증:

- `curr.is_completed != 1`이면 skip
- `nxt.is_completed != 1`이면 skip
- `is_prediction = 1` row는 학습 대상에서 제외
- current active row는 feature input으로는 사용할 수 있지만 label로는 사용할 수 없다.

### 5. Keep Both Directional Possibilities Visible Where Useful

현재 내부 모델은 `prob_bull`, `prob_bear`를 계산하지만 최종적으로는 `pred_is_bull` 또는 `force_bear`로 접힌다.

MVP에서는 기존 DB 구조 때문에 완전한 병렬 시나리오 저장까지 강제하지 않는다.

다만 기획 방향은 다음이다.

- `force_bear`는 “확정 방향”이 아니라 “보수적 판단 보정”으로 취급한다.
- 가능하면 bear continuation과 bull reversal 정보를 둘 다 summary/log에 남긴다.
- 이후 schema 확장 시 `scenario_family`, `prob_bear`, `prob_bull`, `force_reason`을 저장한다.

### 6. Avoid Deleting Valid Old Predictions Before New Output Is Valid

현재 032는 시작 시 `reset_predictions_supabase()`를 호출한다.

이 구조는 다음 문제가 있다.

- 학습/예측/insert 중간 실패 시 dashboard에서 예측이 사라질 수 있다.
- 의사결정 보조 도구에서 stale prediction보다 no prediction이 더 혼란스러울 수 있다.

MVP 현실안:

- 당장 schema 변경 없이 유지할 수는 있다.
- 대신 reset 이후 실패할 수 있는 구간을 최대한 앞에서 검증한다.
- dependency/import/env 오류는 reset 전에 발생해야 한다.
- output validation 실패 시 insert하지 않는다.

Future ideal:

- 새 prediction을 temp/run 단위로 생성한다.
- validation 성공 후 publish한다.
- publish 성공 후 old run을 정리한다.

### 7. Better Run Summary

032 실행 마지막 summary는 단순 row count보다 목적 중심이어야 한다.

권장 summary:

- 대상 coin 수
- current active box가 있는 coin 수
- active completion scenario 생성 수
- next box scenario 생성 수
- skipped coin 수와 skip reason top N
- fallback/cap/clip 사용 건수
- default-visible prediction row 수
- extended-only prediction row 수
- peak/bottom marker 수
- dashboard cache refresh 결과

## Proposed Implementation Phases

### Phase 1: Safety and Meaning Lock

목표: 기존 schema를 유지하면서 032 결과가 목적과 어긋나지 않도록 안전장치를 추가한다.

작업:

- output sanity validator 추가
- active row mutation 방지 테스트 보강
- training pair에서 active label 유입 금지 테스트 보강
- active completion row invariants 테스트 추가
- summary log 개선
- cache refresh policy 테스트 유지/보강

완료 기준:

- 잘못된 prediction row는 Supabase에 저장되지 않는다.
- active observed row는 prediction으로 변경되지 않는다.
- current active box부터 예측한다는 규칙이 테스트로 고정된다.

### Phase 2: Scenario Interpretability

목표: 예측 결과가 차트에서 단일 정답처럼 보이지 않도록 해석 정보를 늘린다.

작업:

- 내부 scenario summary object 생성
- `prob_bear/prob_bull`, `force_bear_reason`, fallback 여부를 log와 summary에 포함
- default/extended scope 계산을 032 summary에 포함
- visualizer와 맞춰 prediction label/tooltip 의미 정리

완료 기준:

- 사용자는 예측이 왜 나왔는지 최소한 log/report에서 확인할 수 있다.
- 기본 화면과 extended 화면의 예측 범위가 일관된다.

### Phase 3: Scenario Metadata Schema

목표: 해석 정보를 DB와 frontend까지 전달한다.

작업:

- `coin_prediction_scenarios` 또는 유사 metadata table 설계
- scenario id/run id 도입
- quality flags 저장
- probability/interval 저장
- prediction rows/paths/peaks와 scenario metadata 연결

완료 기준:

- dashboard tooltip에서 scenario basis와 caution을 보여줄 수 있다.
- stale/low-quality prediction을 화면에서 구분할 수 있다.

### Phase 4: Publish-Safe Prediction Runs

목표: 배치 실패 시 기존 정상 prediction을 잃지 않는다.

작업:

- run id 기반 generation
- validation 성공 후 publish
- old run cleanup
- dashboard snapshot refresh와 run id 연결

완료 기준:

- 032 중간 실패 시 기존 dashboard prediction이 유지된다.
- partial prediction publish가 발생하지 않는다.

## Testing Plan

### Unit Tests

필수 테스트:

- active box가 있으면 prediction anchor가 active `box_index/start_x`를 사용한다.
- active box completion row는 observed active row와 같은 `box_index`를 가진다.
- observed active row는 update/delete/mutate되지 않는다.
- incomplete `nxt` row는 training label로 들어가지 않는다.
- validation 실패 시 `_post_rows_supabase()`가 호출되지 않는다.
- Supabase insert 실패 시 dashboard refresh가 호출되지 않는다.
- Supabase insert 성공 후 dashboard refresh가 호출된다.
- refresh 실패는 prediction 저장 성공을 실패로 바꾸지 않는다.
- default scope row/path와 extended row/path가 서로 어긋나지 않는다.

### Integration-Like Tests With Mocked Supabase

외부 API는 mock 처리한다.

검증:

- `reset_predictions_supabase()` 호출 순서
- fetch stage data
- train/predict mocked output
- validation
- insert rows
- refresh call
- failure path

### Visual Regression Checks

032 단독 테스트는 아니지만 목적상 필요하다.

확인 화면:

- BTC current cycle default view
- active box prediction visible
- next prediction visible
- extended off일 때 먼 미래 prediction hidden
- extended on일 때 먼 미래 prediction visible
- prediction label/tooltip이 exact price forecast처럼 보이지 않는지

## Non-Goals

이번 기획에서 제외한다.

- 자동매매 기능
- 주문 실행
- 매수/매도 추천 문구
- 포트폴리오 비중 계산
- 수익률 백테스트 완성
- 확정 confidence score 제공
- Supabase schema 대규모 변경을 전제로 한 즉시 구현

## Risks

### Risk 1: Existing DB Schema Is Too Thin

현재 tables는 prediction rows/path/peaks 중심이라 scenario rationale을 담기 어렵다.

대응:

- MVP에서는 log/summary/test로 의미를 고정한다.
- 후속 단계에서 metadata table을 설계한다.

### Risk 2: Prediction Can Still Look Too Certain

차트에 점선과 라벨이 있으면 사용자는 실제 forecast처럼 받아들일 수 있다.

대응:

- label/tooltip에서 scenario 표현을 사용한다.
- default scope를 짧게 유지한다.
- extended forecast를 명시적으로 분리한다.

### Risk 3: Historical BTC Cycle Similarity May Break

BTC cycle 기반 비교는 강력하지만 반복 보장은 없다.

대응:

- pattern similarity와 fallback/cap 여부를 기록한다.
- low-quality scenario는 화면에서 구분하는 후속 개선을 계획한다.

## Acceptance Criteria

기획에 맞게 032를 수정했다고 볼 수 있는 기준:

- current active box가 예측 출발점이다.
- observed active row는 절대 prediction으로 덮이지 않는다.
- training label은 completed historical box만 사용한다.
- prediction output은 저장 전 sanity validation을 통과해야 한다.
- 예측 결과는 default/extended 해석 범위를 갖는다.
- Supabase 저장 성공 후에만 dashboard refresh가 호출된다.
- 실행 summary가 단순 row count가 아니라 scenario 관점 정보를 제공한다.
- 문서와 테스트가 “이것은 매매 신호가 아니라 박스 시나리오”라는 의미를 유지한다.

