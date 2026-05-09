# Sub-Box Prediction Planning

## Goal

사용자가 말한 “박스권 안에서 다시 박스예측” 요구를 기존 `01_pairUSDT` 구조와 비교해 비판적으로 검토하고, 구현 전에 필요한 기획을 정리한다.

이 문서의 결론은 다음이다.

> Sub-box 예측은 기존 macro box 예측의 작은 복사본이 아니다. 기존 `coin_analysis_results`의 box는 BTC cycle 안의 큰 BEAR/BULL 구조를 나타내는 macro layer이고, sub-box는 현재 active macro box 내부에서 사용자가 무엇을 감시해야 하는지 보여주는 별도 해석 레이어여야 한다.

## Current Box Meaning

현재 `031_box_analyzer_to_supabase.py`와 `lib/analyzer/box_detector.py`가 만드는 box는 cycle-level macro box다.

현재 macro box의 특징:

- BTC cycle 기준 `alt_cycle_data` 위에서 생성된다.
- cycle 전체 저점을 기준으로 BEAR phase와 BULL phase를 나눈다.
- current cycle은 저점이 확정되지 않았으므로 전체를 BEAR 구간으로 보고 마지막 box를 `ACTIVE`로 둔다.
- `coin_analysis_results.box_index`는 cycle 안에서의 macro box 순서다.
- `032_train_and_predict_box.py`는 이 macro box sequence를 학습해 current active box completion, next box, bottom/peak scenario를 만든다.

따라서 현재 box는 “횡보 박스 안의 작은 박스”가 아니라 “BTC cycle 안의 큰 구조 구간”이다.

## User Intent Interpretation

사용자의 요구는 다음으로 해석된다.

> 현재 active macro box가 아직 끝나지 않았으므로, 그 안의 더 짧은 가격 구조를 sub-box로 나누고, 다음 내부 움직임을 예측하거나 감시하고 싶다.

예시:

```text
BTC Current Cycle
└─ Macro BEAR Box #3  day 100~현재
   ├─ Sub-box 3-A  day 100~118
   ├─ Sub-box 3-B  day 119~143
   ├─ Sub-box 3-C  day 144~현재
   └─ Next internal candidate: upper test or lower retest
```

이 요구는 “다음 macro box 예측”과 다르다.

Macro prediction 질문:

- 현재 BEAR Box #3이 언제 끝나는가?
- 다음 macro box는 어디까지 오르고/내리는가?
- bottom/peak 후보는 어디인가?

Sub-box 질문:

- 현재 Box #3 내부에서 가격은 상단을 다시 테스트 중인가?
- 내부 하단을 다시 확인할 가능성이 있는가?
- 박스 안에서 압축이 진행 중인가?
- 내부 이탈/돌파 감시선은 어디인가?
- macro box가 끝나기 전 단기적으로 무엇을 봐야 하는가?

## Critical Warning

Sub-box를 기존 `coin_analysis_results`에 섞으면 안 된다.

이유:

1. `box_index` 의미가 깨진다.
   - 기존 `box_index=3`은 cycle 안의 3번째 macro box다.
   - sub-box를 같은 테이블에 넣으면 `box_index=4`가 다음 macro box인지, Box #3 내부의 작은 박스인지 모호해진다.

2. `build_training_pairs()`가 오염된다.
   - 현재 학습은 macro box `curr -> next`를 전제로 한다.
   - macro와 sub-box가 섞이면 학습 pair가 macro->sub, sub->sub, sub->macro를 섞어 학습할 수 있다.

3. 차트 해석이 혼란스러워진다.
   - 현재 chart는 `box_zones`, `prediction_paths`, `peak_predictions`를 같은 cycle 객체에 합쳐 그린다.
   - sub-box를 같은 `is_prediction=1` 박스로 넣으면 “다음 box 예측”과 “active box 내부 해석”이 구분되지 않는다.

4. 예측 신뢰도가 달라야 한다.
   - macro prediction은 cycle pattern 기반 시나리오다.
   - sub-box는 단기 내부 구조 해석에 가깝다.
   - 같은 라벨/색/툴팁을 쓰면 사용자가 둘을 같은 수준의 예측으로 오해할 수 있다.

## Proposed Terminology

| Term | Meaning |
|---|---|
| `macro_box` | 현재 `coin_analysis_results`에 저장되는 cycle-level BEAR/BULL box |
| `active_macro_box` | current cycle에서 아직 완료되지 않은 macro box |
| `sub_box` | 특정 macro box 내부에서 감지한 하위 박스 |
| `sub_box_prediction` | active macro box 내부의 다음 내부 구간 후보 |
| `active_internal` | sub-box prediction의 scope. 다음 macro box가 아니라 active box 내부 해석 |
| `macro_prediction` | 기존 032가 만드는 active completion / next box / peak / bottom scenario |

화면 라벨도 구분해야 한다.

- Macro observed: `BEAR Box #3`
- Macro predicted: `Predicted BEAR Box #3`
- Sub observed: `Sub-box 3-A`
- Sub predicted: `Sub candidate 3-D`

## Product Definition

Sub-box prediction은 다음으로 정의한다.

> 현재 active macro box 내부에서 가격이 어떤 내부 range를 만들고 있는지, 상단/하단 테스트 또는 이탈 감시선이 어디인지 보여주는 단기 구조 해석 레이어다.

아닌 것:

- 다음 macro box 예측이 아니다.
- 확정 가격 예보가 아니다.
- 매수/매도 신호가 아니다.
- 기존 `prediction_paths`의 더 촘촘한 일별 경로가 아니다.

## Recommended Architecture

### Option A: Separate Script and Separate Result Layer

권장안이다.

새 파일:

```text
01_pairUSDT/034_analyze_and_predict_sub_box.py
```

또는 모듈 분리:

```text
01_pairUSDT/lib/subbox/detect.py
01_pairUSDT/lib/subbox/features.py
01_pairUSDT/lib/subbox/predict.py
01_pairUSDT/lib/subbox/schema.py
```

역할:

1. `alt_cycle_data`를 읽는다.
2. `coin_analysis_results`에서 current active macro box를 찾는다.
3. active macro box의 `start_x~end_x` 내부 데이터만 잘라낸다.
4. sub-box detector로 내부 구조를 감지한다.
5. 마지막 active sub-box의 다음 내부 후보를 생성한다.
6. 별도 result로 저장하거나 visualizer payload에 별도 key로 전달한다.

장점:

- 기존 031/032 macro pipeline을 오염시키지 않는다.
- 실패해도 기존 macro prediction이 유지된다.
- 차트에서 독립 토글/레이어로 표시하기 쉽다.

### Option B: 031 안에 Sub-Box Detector 추가

비권장 초기안이다.

장점:

- 031이 이미 `alt_cycle_data`와 macro box를 다룬다.

문제:

- 031은 macro observed box 생성 책임이 명확하다.
- sub-box까지 넣으면 책임이 커진다.
- `coin_analysis_results`에 섞고 싶은 유혹이 생긴다.

### Option C: 032 안에 Sub-Box Prediction 추가

초기 구현으로는 비권장이다.

문제:

- 032는 macro box sequence 학습/예측 배치다.
- sub-box는 데이터 단위, feature, target, UI 의미가 다르다.
- 032에 넣으면 macro prediction과 sub-box prediction의 publish/validation이 뒤섞인다.

## Data Contract

초기에는 Supabase schema 변경 없이 JSON/HTML payload에만 넣는 MVP도 가능하다. 하지만 장기적으로는 별도 테이블이 안전하다.

### Recommended Table: `coin_sub_box_results`

필드 초안:

| Column | Meaning |
|---|---|
| `coin_id` | coin id |
| `symbol` | coin symbol |
| `cycle_number` | BTC cycle number |
| `cycle_name` | BTC cycle name |
| `parent_box_index` | macro box index |
| `parent_phase` | macro `BEAR` / `BULL` |
| `parent_result` | usually `ACTIVE` for MVP |
| `sub_box_index` | internal sequence, integer or label |
| `layer` | fixed `sub_box` |
| `scope` | `active_internal` |
| `scenario_role` | `range_continuation`, `upper_test`, `lower_test`, `compression`, `breakout_watch`, `breakdown_watch` |
| `start_x` | sub-box start day |
| `end_x` | sub-box end day |
| `upper` | internal upper band |
| `lower` | internal lower band |
| `pivot_high_day` | local high day |
| `pivot_low_day` | local low day |
| `breakout_up_level` | level invalidating upper range |
| `breakdown_level` | level invalidating lower range |
| `duration` | sub-box duration |
| `range_pct` | internal range percent |
| `is_completed` | observed sub-box completed |
| `is_prediction` | predicted candidate |
| `source` | `observed`, `model`, `heuristic`, `mixed` |
| `visibility` | `default` or `extended` |
| `invalidated_by` | level/time invalidation text or code |

### Visualizer Payload Shape

Do not merge into `box_zones`.

Recommended cycle payload:

```json
{
  "box_zones": [],
  "prediction_paths": {"bear": [], "bull": []},
  "peak_predictions": [],
  "sub_boxes": [],
  "sub_box_candidates": []
}
```

Important:

- `box_zones`: macro boxes only
- `prediction_paths`: macro forecast paths only
- `sub_boxes`: observed internal structures only
- `sub_box_candidates`: internal candidates only

## Detection Strategy

Do not reuse `detect_box_zones()` directly.

Current macro detector:

- uses cycle low to split BEAR/BULL;
- assumes macro trend phase;
- uses macro rebound/breakout rules;
- treats current cycle as all BEAR.

Sub-box detector should be local and parent-aware.

### MVP Detector Proposal

Input:

- active macro box data slice
- parent `start_x`, `end_x`, `hi`, `lo`
- OHLCV rate points from `alt_cycle_data`

Rules:

1. Slice data to parent active macro box:

```text
parent.start_x <= days_since_peak <= latest observed day
```

2. Find local pivot highs/lows:

- local high: high greater than nearby `N` bars
- local low: low lower than nearby `N` bars
- default pivot window: 2 or 3 days

3. Build internal range:

- upper = recent pivot high cluster
- lower = recent pivot low cluster
- minimum duration: 3~7 days, configurable
- minimum range: avoid tiny noise boxes

4. Mark role:

- price near upper: `upper_test`
- price near lower: `lower_test`
- range narrowing: `compression`
- close above upper: `breakout_watch`
- close below lower: `breakdown_watch`
- otherwise: `range_continuation`

5. Last internal range is active:

- `is_completed = 0`
- `source = observed`

6. Candidate prediction:

- next likely internal movement:
  - upper retest candidate
  - lower retest candidate
  - compression continuation
  - breakout/breakdown watch

The MVP can be heuristic-only. ML should come later after the detector is stable.

## Prediction Strategy

### MVP: Heuristic Candidate

처음부터 XGBoost를 붙이지 않는다.

MVP는 다음 후보만 생성한다.

| Candidate | Meaning |
|---|---|
| `upper_test` | current internal range upper band retest |
| `lower_test` | current internal range lower band retest |
| `range_continuation` | internal range likely continues |
| `breakout_watch` | close/structure near upper invalidation |
| `breakdown_watch` | close/structure near lower invalidation |

MVP output:

- candidate upper/lower
- expected watch window, not exact day forecast
- invalidation level
- source: `heuristic`

### Future: ML Sub-Box Model

ML은 observed sub-box history가 충분히 쌓인 뒤에 한다.

별도 training pairs:

```text
sub_box_i -> sub_box_i+1
```

Potential targets:

- `next_sub_upper_change_pct`
- `next_sub_lower_change_pct`
- `next_sub_duration`
- `next_sub_direction`
- `next_sub_role`

Potential features:

- parent macro phase
- parent macro result
- parent box range position
- current price position inside parent
- distance to parent upper/lower
- current sub-box range_pct
- current sub-box duration
- compression ratio
- recent volatility
- BTC current cycle day
- macro prediction direction, if available

## Chart Design

Sub-box must be visually distinct from macro prediction.

Recommended visual hierarchy:

1. Observed macro active box
   - existing strong box zone
2. Macro active completion prediction
   - existing prediction box style
3. Macro next box prediction
   - existing forecast style
4. Sub-box
   - thin inner bracket, narrow band, or subtle internal line
   - no large filled rectangle
   - no bull/bear prediction path line

Sub-box should have its own toggle:

```text
SHOW: HIGH/LOW | BOX ZONE | PREDICT | SUB-BOX | EXTENDED
```

Do not reuse `PREDICT` only.

Sub-box tooltip should say:

- `Active Box 내부 후보`
- `다음 박스 예측 아님`
- `상단 테스트 / 하단 이탈 감시`
- `무효화: level X 이탈`
- `보간 경로가 아니라 현재 박스 내부 구조 해석`

Avoid strong language:

- Do not use `TREND CHANGING`
- Do not use `BUY`
- Do not use `SELL`
- Do not use `confirmed`

## Critical Invariants

Sub-box invariants:

- A sub-box must have a parent macro box.
- MVP only uses current active macro box.
- `start_x/end_x` must be inside parent active macro box observed range, unless candidate uses a short watch window beyond latest day.
- `upper >= lower`.
- `sub_box_index` must not be confused with macro `box_index`.
- observed sub-box and predicted candidate must be separate.
- `is_prediction=1` sub-box candidate is not a macro next-box prediction.
- sub-box must not be fed into existing macro `build_training_pairs()`.

No leakage rules:

- Do not use parent macro final `hi/lo/end_x` if it is not known at that time.
- For historical training, simulate what would have been known at each sub-box point.
- Do not use future pivot confirmation when producing current active candidate.

## MVP Scope

MVP should be small.

1. Create planning/spec only.
2. Implement detector later in a new module, not inside 031/032.
3. Start with BTC current cycle active macro box only.
4. Generate observed sub-boxes and one candidate using heuristic rules.
5. Render as an optional chart layer.
6. Do not train ML yet.
7. Do not modify `coin_analysis_results`.
8. Do not change macro prediction behavior.

## Implementation Phases

### Phase 1: Data Exploration

Goal:

- Confirm that current active macro boxes contain enough internal structure to justify sub-boxes.

Tasks:

- Write an offline notebook/script or report generator.
- Use BTC current cycle first.
- Slice current active macro box.
- Print local pivot highs/lows.
- Compare candidate sub-box ranges visually.

Output:

- no DB write
- report screenshot or JSON sample

### Phase 2: Heuristic Detector

Goal:

- Build deterministic sub-box detector.

Files:

```text
01_pairUSDT/lib/subbox/detect.py
unit_tests/01_pairUSDT/lib/subbox/test_detect.py
```

Output:

- list of observed sub-box dicts
- no prediction yet

### Phase 3: Candidate Generator

Goal:

- Produce one internal candidate from the latest active sub-box.

Files:

```text
01_pairUSDT/lib/subbox/predict.py
unit_tests/01_pairUSDT/lib/subbox/test_predict.py
```

Output:

- `sub_box_candidates`
- source: `heuristic`

### Phase 4: Visualizer Integration

Goal:

- Show sub-box layer without confusing it with macro prediction.

Files:

```text
01_pairUSDT/033_visualizer_html.py
01_pairUSDT/templates/chart-series-subbox.ts
01_pairUSDT/templates/chart-render-tooltip.ts
01_pairUSDT/templates/chart-ui.ts
```

Rules:

- Add separate `SUB-BOX` toggle.
- Use inner bracket/band style.
- Tooltip must explicitly say it is active box internal structure.

### Phase 5: DB Contract

Goal:

- Persist sub-boxes after the visual/logic semantics are stable.

Options:

- New Supabase table `coin_sub_box_results`
- Or backend-only generated payload for current active cycle

Do not use `coin_analysis_results` for sub-boxes.

### Phase 6: ML Model

Goal:

- Train sub-box transition model only after enough observed sub-box data exists.

Out of MVP.

## Testing Plan

### Detector Tests

- no data -> empty list
- fewer than minimum bars -> empty list
- clean range -> one sub-box
- range breakout -> completed sub-box
- active range -> active sub-box
- parent boundary respected
- upper >= lower
- pivot day inside range

### Prediction Candidate Tests

- active sub-box near upper -> `upper_test`
- active sub-box near lower -> `lower_test`
- narrowing range -> `compression`
- close above upper -> `breakout_watch`
- close below lower -> `breakdown_watch`
- candidate does not exceed parent boundary unless marked as watch window

### Integration Tests

- macro `coin_analysis_results` unchanged
- macro 032 output unchanged
- sub-box payload appears under `sub_boxes`, not `box_zones`
- `PREDICT` toggle does not control sub-box layer
- `SUB-BOX` toggle controls only sub-box layer

## Non-Goals

Do not include in first implementation:

- automatic buy/sell signals
- exact daily price forecast
- reusing macro XGBoost model for sub-boxes
- storing sub-boxes in `coin_analysis_results`
- changing 031 macro box semantics
- changing 032 macro prediction semantics
- drawing sub-boxes as full prediction paths
- treating sub-box as a new macro box

## Open Questions

Need user confirmation before implementation:

1. Do you want sub-boxes only inside the current active macro box first?
2. Should sub-boxes be shown for BTC only first, or all selected coins?
3. Should MVP be visual-only without Supabase schema change?
4. What is the preferred minimum internal range duration: 3 days, 5 days, or 7 days?
5. Should candidate output focus on upper/lower test levels rather than exact future dates?

## Final Recommendation

Do not modify `031` or `032` directly for this feature at first.

Recommended first implementation:

1. Add a separate sub-box detector module.
2. Run it only on current active macro box data.
3. Produce observed internal ranges and one heuristic candidate.
4. Add a separate `SUB-BOX` visual layer.
5. Keep macro box prediction untouched.

This keeps the system aligned with the core purpose: **BTC cycle macro scenario remains the main decision-support layer, while sub-boxes become a short-term internal structure aid inside the active macro box.**

