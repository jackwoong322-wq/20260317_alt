# 대시보드 2.0 — 기술 설계서 (ARCHITECTURE.md)

> 작성: Tech Lead 에이전트 | 버전: 1.0 | 날짜: 2026-05-17 | 상태: **FROZEN**  
> PM 기획서(PRODUCT_SPEC.md) 기반 기술 실현 가능성 검토 완료

---

## 1. 아키텍처 원칙

1. **백엔드 로직 분리**: 모든 API 호출은 `src/lib/api.js` 단일 진입점 경유. 컴포넌트에서 `fetch` 직접 호출 금지.
2. **환경 변수 필수**: API 베이스 URL은 반드시 `import.meta.env.VITE_API_URL` 사용. 문자열 하드코딩 즉시 반려.
3. **단방향 데이터 흐름**: `useChartData.js` hook → 컴포넌트 Props → UI 렌더링.
4. **오버레이 분리**: HTML 툴팁 레이어는 `ChartOverlay.jsx`에 캡슐화. 차트 컴포넌트가 직접 DOM 조작 금지.
5. **목 데이터 격리**: `src/mocks/dashboardMock.js`는 개발/테스트 환경에서만 활성화. 프로덕션 빌드에 포함 금지 (`import.meta.env.DEV` 조건부).

---

## 2. 디렉터리 구조 (변경 대상)

```
04_frontend_0222fb/src/
├── components/
│   ├── ChartOverlay.jsx          ← [기존 개선] 범용 HTML 오버레이 툴팁
│   ├── ChartTooltip.jsx          ← [신규] 데이터 툴팁 UI 컴포넌트
│   ├── CycleComparisonChart.jsx  ← [수정] subscribeCrosshairMove 연동
│   ├── BearBoxChart.jsx          ← [수정] ChartOverlay 통합
│   └── ChartSkeleton.jsx         ← [신규] 로딩 스켈레톤 (F-06)
├── hooks/
│   ├── useChartTooltip.js        ← [신규] 툴팁 상태 관리 커스텀 훅
│   └── useChartData.js           ← [기존] 유지
├── mocks/
│   └── dashboardMock.js          ← [신규] 백엔드 미연결 시 목 데이터
├── styles/
│   ├── Chart.css                 ← [수정] 툴팁·스켈레톤 스타일
│   └── Tooltip.css               ← [신규] 툴팁 전용 스타일
└── tests/
    ├── chartTooltip.test.jsx     ← [신규] 툴팁 Vitest 유닛 테스트
    └── visual/                   ← [신규] Playwright 스크린샷 저장
```

---

## 3. HTML 오버레이 툴팁 설계 (F-01/02/03)

### 3.1 동작 원리

```
lightweight-charts 인스턴스
  └─ subscribeCrosshairMove(param)
        ├─ param.point  → { x, y } 픽셀 좌표
        ├─ param.time   → 날짜(Day index)
        └─ series.seriesType().dataByIndex() → 가격값
            ↓
      useChartTooltip 훅 (상태 계산)
            ↓
      ChartTooltip 컴포넌트 (HTML 렌더링)
            ↓
      position:absolute, z-index:20, pointer-events:none
```

### 3.2 ChartTooltip 컴포넌트 인터페이스

```js
// Props 타입 정의
ChartTooltip.propTypes = {
  visible: bool,        // 표시 여부
  x: number,            // 픽셀 X
  y: number,            // 픽셀 Y
  containerWidth: number, // 컨테이너 폭 (뷰포트 클리핑 계산용)
  data: {
    dayLabel: string,   // "Day 42"
    items: [{
      name: string,     // "Current Cycle (2025)"
      value: string,    // "63.46%"
      color: string,    // "#d8a544"
      diff: string,     // "+2.3pp" (기준선 대비)
    }]
  }
}
```

### 3.3 뷰포트 클리핑 방지 로직

```
if (x + TOOLTIP_WIDTH > containerWidth) → x 축 왼쪽으로 offset
if (y + TOOLTIP_HEIGHT > containerHeight) → y 축 위로 offset
```

---

## 4. 목 데이터 설계 (백엔드 미연결 시)

```js
// src/mocks/dashboardMock.js
// 조건: import.meta.env.DEV === true 일 때만 활성화
export const mockCycleComparison = { series: [...] }
export const mockBearBoxData = (cycleNumber) => ({ lineData: [...], boxes: [...] })
```

`useChartData.js`의 각 훅은 API 실패 시 자동으로 목 데이터 fallback.

---

## 5. 테스트 전략

| 레이어 | 도구 | 대상 | 기준 |
|---|---|---|---|
| 유닛 | Vitest | ChartTooltip 렌더링, useChartTooltip 상태 | 커버리지 80%+ |
| 시각 | Playwright | 375px / 1280px / 1440px 스크린샷 | 가로 스크롤 없음, 잘림 없음 |
| 아키텍처 | 정적 분석 (grep) | VITE_API_URL 하드코딩 여부 | 0건 |

---

## 6. 아키텍처 리뷰 체크리스트 (코드 반려 기준)

- [ ] API URL 문자열 직접 사용 (`http://`, `localhost:` 포함)
- [ ] 컴포넌트 내 `fetch()` 직접 호출
- [ ] `useEffect` 의존성 배열 누락
- [ ] `chartRef.current` null 체크 누락
- [ ] 목 데이터 프로덕션 빌드 포함

---

*Tech Lead 에이전트 서명: PM 기획서와 기술 정합성 확인 완료. 설계서 FROZEN.*
