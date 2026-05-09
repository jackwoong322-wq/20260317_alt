# 01_pairUSDT Program Purpose Critical Review

## Summary

`01_pairUSDT`는 단순한 코인 가격 수집기나 차트 뷰어가 아니다.

코드와 관련 사양서를 기준으로 보면, 이 프로그램은 **BTC 사이클을 공통 시간축으로 삼아 USDT 마켓 코인들의 상대 가격 흐름을 정규화하고, 그 안에서 BEAR/BULL 박스권을 탐지한 뒤, 현재 사이클의 다음 박스·저점·고점 시나리오를 예측해서 시각적으로 검토하기 위한 암호화폐 사이클 분석 시스템**으로 보는 것이 가장 타당하다.

다만 이것을 **자동매매 시스템**, **완전한 가격 예측 엔진**, **확정적인 매수/매도 신호 생성기**로 부르는 것은 코드 근거에 비해 과장이다. 현재 구조는 거래 실행보다 **리서치, 비교 분석, 시나리오 검토, 대시보드 시각화**에 더 가깝다.

## Most Likely User Goal

이 프로그램이 답하려는 핵심 질문은 다음으로 보인다.

> 현재 코인, 특히 알트코인이 BTC current cycle 기준으로 어느 위치에 있고, 과거 BTC 사이클의 유사한 박스권 흐름과 비교했을 때 다음 고점·저점·바닥·피크는 어느 날짜와 가격대일 가능성이 있는가?

이를 더 구체적으로 나누면 다음 질문들이다.

- 지금 BTC current cycle에서 이 코인은 몇 번째 박스권에 있는가?
- 현재 박스는 아직 진행 중인가, 확정된 박스인가?
- 현재 active box가 BEAR 쪽으로 끝날 가능성이 큰가, BULL 쪽으로 전환될 가능성이 큰가?
- 현재 박스가 끝난 뒤 다음 박스의 예상 고점, 저점, 기간은 어느 정도인가?
- 과거 `Cycle 2017`, `Cycle 2021` 등과 비교했을 때 현재 위치가 빠른 편인가, 느린 편인가?
- 이전 사이클의 저점, 고점, 회복 기간과 비교했을 때 현재 가격대가 어느 정도 수준인가?
- 먼 미래 예측까지 볼 것인가, 아니면 현재/다음 박스만 집중해서 볼 것인가?

## What Can Be Said With High Confidence

### 1. Market Data Pipeline

`011`, `012` 계열 스크립트는 Binance USDT 마켓의 OHLCV 데이터를 Supabase에 저장하고 갱신하기 위한 수집 파이프라인이다.

- `coins` 테이블에는 분석 대상 코인 메타데이터가 저장된다.
- `ohlcv` 테이블에는 일봉 가격 데이터가 저장된다.
- 업데이트 스크립트는 코인별 마지막 저장 일자 이후 데이터를 이어서 받는 구조다.
- 당일 미완성 캔들은 저장하지 않는 방향으로 관리된다.

즉, 이 시스템은 일회성 분석 파일이 아니라 매일 갱신되는 데이터 기반 분석 흐름을 전제로 한다.

### 2. BTC Cycle Template

`021_altCycleAnalysisUsdt.py`의 핵심 의미는 “각 알트코인의 자체 고점 사이클”이 아니라 **BTC 피크 날짜를 기준으로 한 공통 사이클 템플릿**이다.

중요한 의미 변화:

- `cycle_number`: 알트 자체 사이클 번호가 아니라 BTC 사이클 번호다.
- `cycle_name`: BTC 사이클 이름이다.
- `peak_date`: 해당 코인의 고점 날짜가 아니라 BTC 사이클 시작 기준 날짜다.
- `peak_price`: 알트 자체 고점 가격이 아니라 BTC 사이클 시작일의 해당 코인 close 기준가다.
- `days_since_peak`: 해당 코인 고점 이후 일수가 아니라 BTC cycle 시작 이후 경과일이다.
- `close_rate/high_rate/low_rate`: 해당 코인의 실제 가격을 BTC cycle 시작일의 해당 코인 close 대비 비율로 정규화한 값이다.

이 구조 때문에 BTC, ETH, BNB, ZEC처럼 가격 단위가 완전히 다른 코인을 같은 `days_since_peak` 축과 같은 rate 축에서 비교할 수 있다.

### 3. Box-Based Market Structure

`031_box_analyzer_to_supabase.py`와 `lib/analyzer/box_detector.py`는 정규화된 사이클 데이터를 박스권 단위로 분해한다.

여기서 box는 단순한 화면용 사각형이 아니라 분석과 예측의 기본 단위다.

주요 필드:

- `phase`: `BEAR` 또는 `BULL`
- `result`: `DOWN`, `UP`, `BOTTOM`, `ACTIVE`, 예측 계열 결과 등
- `box_index`: 사이클 안에서 몇 번째 박스인지
- `start_x`, `end_x`: BTC cycle 시작 이후 박스 시작/종료 day
- `hi`, `lo`: 박스 내 정규화 고점/저점
- `hi_day`, `lo_day`: 고점/저점이 발생한 day
- `duration`, `range_pct`: 박스 기간과 변동폭
- `is_completed`: 확정 박스인지, 현재 진행 중 박스인지
- `is_prediction`: 실측 분석 결과인지, 예측 결과인지

특히 current cycle은 저점과 종료가 아직 확정되지 않았기 때문에 마지막 박스가 `ACTIVE`로 남는다. 이 점이 이후 예측 로직의 출발점이다.

### 4. Prediction Is Scenario-Based

`032_train_and_predict_box.py`와 `lib/predictor` 모듈들은 다음 값을 예측하려고 한다.

- 다음 또는 현재 active box의 최종 고점
- 다음 또는 현재 active box의 최종 저점
- 박스 기간
- 다음 phase가 BEAR인지 BULL인지
- bottom 후보
- peak 후보
- bear/bull prediction path

하지만 이 예측은 “특정 날짜의 정확한 종가”를 예보하는 구조가 아니다. 더 정확히는 **박스 단위의 시나리오 생성기**다.

`coin_prediction_paths`의 점선 경로도 실제 일별 종가 예측이라기보다, 예측 박스의 고점/저점/기간을 시각적으로 연결하기 위한 보간 경로로 해석하는 것이 안전하다.

### 5. Visualizer Is a Decision-Support Dashboard

`033_visualizer_html.py`와 `templates` 아래 차트 코드는 다음 데이터를 한 화면에서 비교하게 만든다.

- 실제 cycle line
- high/low label
- box zone
- BEAR/BULL phase
- active box
- prediction box
- prediction path
- bottom/peak marker
- current cycle과 과거 cycle 비교
- 기본 예측 범위와 `EXTENDED` 먼 미래 예측 범위

따라서 visualizer의 목적은 “예측 결과를 저장했다”에서 끝나는 것이 아니라, 사람이 현재 위치와 다음 시나리오를 눈으로 검토하게 만드는 것이다.

## What Is Likely But Still an Inference

다음은 코드만으로 100% 확정할 수는 없지만, 전체 구조상 가장 자연스러운 해석이다.

### 1. Investment Timing Support

이 시스템은 매수/매도 주문을 직접 실행하지 않는다. 하지만 현재 박스, 예상 고점, 예상 저점, 바닥 후보, 피크 후보를 보여주는 구조상 **투자 타이밍 판단을 보조하려는 목적**은 강하게 추정된다.

예상 사용 방식:

- 현재 가격이 과거 사이클 대비 낮은 구간인지 확인
- 현재 active box의 하방 위험과 상방 가능성을 비교
- 다음 저점 후보를 분할 매수 관심 구간으로 검토
- 예측 고점/피크 후보를 익절 또는 리스크 관리 참고 구간으로 검토
- BTC current cycle에서 알트코인의 상대적 회복 강도를 비교

### 2. Altcoin Rotation Analysis

BTC cycle을 기준으로 모든 알트코인을 정렬하는 구조는 “개별 코인의 독립 차트”보다 **BTC cycle 안에서 알트들이 언제 강해지고 약해지는지**를 보려는 목적에 가깝다.

즉, 단일 코인 예측뿐 아니라 다음 질문도 포함된 것으로 보인다.

- 현재 cycle에서 어떤 알트가 이전 cycle 대비 강한가?
- 어떤 알트가 아직 회복이 늦은가?
- BTC 기준 같은 day에서 특정 알트가 과거보다 높은 위치인가, 낮은 위치인가?
- 알트별 BEAR/BULL box 전환 속도가 다른가?

### 3. Research and Model Experimentation

`lib/predictor`에는 XGBoost 모델뿐 아니라 휴리스틱, fallback, cap, interpolation, 유사 패턴 매칭이 섞여 있다. 이는 완성된 단일 이론이라기보다 **예측 방법을 계속 실험하고 개선하는 리서치 코드**의 성격이 강하다.

특히 최근 변경 흐름을 보면 다음 관심사가 반복된다.

- 현재 active box부터 예측해야 한다.
- 먼 미래 예측은 기본 화면에서 줄이고 `EXTENDED`로 분리해야 한다.
- 예측 라벨에는 가격, 변동률, 걸린 일수를 같이 보여야 한다.
- BTC current cycle이 먼저 빠르게 보여야 한다.
- lazy load로 전체 대시보드 로딩을 줄여야 한다.

이는 예측 정확도뿐 아니라 “사람이 해석 가능한 화면”을 계속 다듬는 흐름이다.

## What Would Be an Overstatement

### 1. It Is Not an Auto-Trading Bot

코드상 다음 요소가 보이지 않는다.

- 주문 실행
- 거래소 API key를 통한 매매
- 포지션 크기 산정
- 손절/익절 주문 관리
- 레버리지 관리
- 슬리피지/수수료 반영
- 실거래 체결 이력 관리

따라서 이것을 자동매매 봇이라고 부르는 것은 부정확하다.

### 2. It Is Not a Complete Financial Decision Engine

이 시스템은 예상 구간과 경로를 보여주지만, 다음까지 완성되어 있다고 보기는 어렵다.

- 예측 신뢰구간
- 예측별 확률
- 모델별 성능 평가
- 수익률 백테스트
- 최대 낙폭 검증
- 기대값 계산
- 포트폴리오 비중 결정

따라서 “최종 투자 결정을 자동으로 내려주는 시스템”보다는 “사람이 의사결정할 때 참고할 분석 도구”가 더 정확하다.

### 3. It Is Not Pure ML

XGBoost가 쓰이지만 전체 예측은 순수 ML만으로 구성되지 않는다.

섞여 있는 요소:

- XGBoost classification/regression
- BTC/ALT 분리 모델
- BEAR/BULL 분리 모델
- 휴리스틱 fallback
- bottom/peak 보정
- path interpolation
- cap/floor 제한
- 유사 패턴 참조

그래서 “AI가 가격을 예측한다”보다는 “ML과 규칙 기반 보정을 섞어 박스 시나리오를 만든다”가 더 정확하다.

## More Precise One-Line Definition

가장 정확한 한 줄 정의는 다음이다.

> `01_pairUSDT`는 Binance USDT 코인의 OHLCV를 수집하고, BTC 피크 사이클을 공통 기준축으로 삼아 각 코인의 정규화된 가격 사이클과 BEAR/BULL 박스권을 만들며, 현재 active box 이후의 저점·고점·박스 경로를 ML과 휴리스틱으로 예측해 Supabase와 차트 대시보드에 제공하는 사이클 기반 암호화폐 분석 파이프라인이다.

## Practical Interpretation

이 프로그램은 다음 판단을 돕기 위해 만들어진 것으로 보인다.

| 판단 영역 | 프로그램이 제공하는 단서 |
|---|---|
| 현재 위치 | BTC cycle 기준 `days_since_peak`, current cycle line |
| 상대 가격 수준 | `close_rate/high_rate/low_rate`, 과거 cycle 비교 |
| 박스 구조 | BEAR/BULL box, active box, completed box |
| 하방 위험 | 예측 low, bottom marker, bear path |
| 상방 가능성 | 예측 high, peak marker, bull path |
| 시간 감각 | 박스 duration, 고점/저점까지 걸린 일수 |
| 비교 분석 | BTC와 알트, 과거 cycle과 current cycle 비교 |
| 화면 해석 | 기본 forecast 범위와 EXTENDED forecast 분리 |

## Critical Caveats

### 1. Current Cycle Is Not Fully Known

현재 사이클은 아직 종료되지 않았고, 바닥도 확정되지 않았을 수 있다. 따라서 current cycle의 `ACTIVE` box와 그 예측값은 관측 확정값이 아니라 진행 중인 데이터와 모델 추정이 섞인 상태다.

### 2. Historical Similarity May Not Repeat

BTC cycle 기준으로 과거와 현재를 맞추는 것은 강력한 비교 프레임이지만, 시장 구조는 매 cycle 달라질 수 있다.

예를 들면:

- 상장 코인 수 변화
- 유동성 변화
- ETF/기관 자금 유입
- 거래소 구조 변화
- 규제 변화
- 특정 코인의 서사 변화

따라서 과거 box pattern은 참고 자료이지 반복 보장은 아니다.

### 3. Prediction Paths Should Not Be Read as Exact Daily Forecasts

예측선은 box scenario를 연결하기 위한 시각화다. 특정 day의 line value를 그대로 “그날의 예상 종가”로 읽으면 과해석이다.

### 4. Column Names Can Mislead

BTC template 적용 이후에도 기존 컬럼명을 유지했기 때문에, 이름만 보고 의미를 해석하면 틀릴 수 있다.

특히 주의:

- `peak_price`: 알트 자체 피크 가격이 아니다.
- `peak_date`: 알트 자체 고점 날짜가 아니다.
- `cycle_number`: 알트 독자 사이클 번호가 아니다.
- `days_since_peak`: 알트 고점 이후 일수가 아니다.

## Final Judgment

처음 추정한 “BTC 사이클 기반 알트코인 박스권/예측 분석 시스템”이라는 표현은 큰 방향에서 맞다.

다만 비판적으로 보정하면 다음이 더 정확하다.

> 이 시스템은 자동매매나 확정적 가격 예측기가 아니라, BTC 사이클을 공통 기준으로 여러 USDT 코인의 현재 위치와 과거 유사 패턴을 비교하고, 미완성 active box 이후의 가능한 BEAR/BULL 경로를 시각적으로 검토하기 위한 리서치/의사결정 보조 파이프라인이다.

