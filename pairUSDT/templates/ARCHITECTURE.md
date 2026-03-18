# Chart Module Architecture & Best Practices

## 프로젝트 상황 판단

| 구분 | 판단 | 근거 |
|------|------|------|
| **도메인** | Crypto/Finance | BTC·알트코인 사이클 분석, 퍼센트 기반 가격 시각화 |
| **스택** | Frontend (Vanilla TS) | Lightweight Charts, DOM 기반 오버레이 |
| **현재 상태** | 전역 → chartState 래퍼로 부분 이전 | 모듈화 진행 중, DI 미완성 |

## 적용 규칙 요약

### Core Principles (5대 원칙)
1. **전역 상태 금지** → `chartState` 싱글톤 제거, `drawChart(state)` 등 명시적 DI
2. **리터럴/매직 넘버 금지** → `chart-constants.ts`에 상수 집중 정의
3. **조기 귀환** → Guard clause로 예외 상황 선처리
4. **단일 책임 (SRP)** → 함수당 20줄 이내, 한 가지 일만 수행
5. **순수 함수 지향** → 데이터 변환은 부수효과 없이, 렌더링만 명시적 분리

### Context-Specific (금융 + 프론트엔드)
- **정밀도**: 퍼센트 표시용이므로 `number` 유지 (Decimal 도입 시 Lightweight Charts 호환성 검토 필요)
- **방어적 설계**: `setSeriesDataSafe`, `filterValidPoints` 등 null/NaN 검증
- **로직 분리**: 시리즈 추가/오버레이 렌더링을 Service 계층으로 분리
- **상태 최소화**: `legendItems` 등 파생 데이터는 계산 함수로 추출

## 설계 결정 (Design Decisions)

### 1. ChartState를 DI로 전달
- **이유**: 전역 `chartState`는 테스트·재사용 불가, 숨은 의존성
- **방향**: `drawChart(state: ChartState)` 등 모든 진입점에서 state 인자 필수

### 2. 상수 모듈 분리
- **이유**: 색상, 라인 두께, 비율 등이 여러 파일에 산재
- **방향**: `chart-constants.ts`에 `LINE_WIDTH_*`, `EMPHASIS_COLOR` 등 정의

### 3. 순수 함수 vs 부수효과
- **순수**: `buildMainLineData`, `findCycleMinLowIdx` → 입력만으로 출력 결정
- **부수효과**: `addMainLineSeries`, `clearAllSeries` → chart/state 변경, 명시적 호출

### 4. Early Return 패턴
- `if (!coinData) return;` → 중첩 감소
- `if (state.selectedCoins.length === 0) { ... return; }` → 정상 흐름이 메인

### 5. 상수 모듈 (chart-constants.ts)
- `LINE_WIDTH_*`, `EMPHASIS_COLOR`, `MIN_BOX_DAYS`, `*_RATIO` 등
- chart-logic, chart-series-main에서 import하여 일원화
