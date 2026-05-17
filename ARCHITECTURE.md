# 대시보드 2.0 — 기술 설계서 (ARCHITECTURE.md) v2

> 작성: Tech Lead 에이전트 | 버전: 2.0 | 날짜: 2026-05-17 | 상태: **FROZEN**
> 변경: v1 → v2 — 03_frontend TypeScript 포팅 설계 추가, 공유 패턴 정의

---

## 1. 아키텍처 원칙

1. **백엔드 로직 분리**: 모든 API 호출은 `src/lib/api.[js|ts]` 단일 진입점 경유. 컴포넌트에서 `fetch` 직접 호출 금지.
2. **환경 변수 필수**: API 베이스 URL은 반드시 `import.meta.env.VITE_API_URL` 사용. 문자열 하드코딩 즉시 반려.
3. **단방향 데이터 흐름**: `useChartData.[js|ts]` hook → 컴포넌트 Props → UI 렌더링.
4. **오버레이 분리**: HTML 툴팁 레이어는 `ChartTooltip.[jsx|tsx]`에 캡슐화. 차트 컴포넌트가 직접 DOM 조작 금지.
5. **목 데이터 격리**: `src/mocks/dashboardMock.[js|ts]`는 개발/테스트 환경에서만 활성화.
6. **언마운트 안전**: 비동기 완료 콜백에서 `cancelledRef.current` 확인 필수. (BUG-06/11 재발 방지)
7. **TypeScript strict**: 03_frontend는 `strict: true` + `noImplicitAny: true` 준수. `any` 타입 사용 반려.

---

## 2. 디렉터리 구조

### 04_frontend_0222fb (JavaScript)
```
src/
├── components/
│   ├── ChartTooltip.jsx          [완료] HTML 오버레이 툴팁 (BUG-05/08 수정)
│   ├── BearBoxTooltip.jsx        [완료] Bear/Bull 박스 전용 툴팁
│   ├── ChartSkeleton.jsx         [완료] F-06 스켈레톤 (BUG-10 수정)
│   ├── BearBoxChart.jsx          [완료] PNG 버튼 통합
│   ├── BullBoxChart.jsx          [완료] PNG 버튼 통합
│   └── CycleComparisonChart.jsx  [완료] useMemo 메모이제이션(BUG-04)
├── hooks/
│   ├── useChartTooltip.js        [완료] 크로스헤어 툴팁 훅
│   ├── useBearBoxTooltip.js      [완료] Bear 전용 툴팁
│   ├── useBullBoxTooltip.js      [완료] Bull 전용 툴팁
│   ├── useChartExport.js         [완료] PNG 내보내기 (BUG-06 수정)
│   ├── useTheme.js               [완료] 테마 토글 (BUG-07 수정)
│   ├── useChartData.js           [완료] cancelledRef 전환(BUG-11)
│   └── useResizeChart.js         [완료] height 가드(BUG-09)
├── lib/api.js                    [완료] GATE-1/2 통과
├── mocks/dashboardMock.js        [완료]
├── styles/
│   ├── Tooltip.css               [완료] transition 기반 애니메이션(BUG-08)
│   ├── Chart.css                 [완료]
│   └── theme.css                 [완료] OKLCH 40개 변수
└── tests/
    ├── *.test.jsx                [완료] 76케이스
    └── e2e/visual.spec.js        [⚠️] 파일 있으나 실행 미완
```

### 03_frontend (TypeScript) — 포팅 대상
```
src/
├── components/
│   ├── SummaryCard.tsx           [기존] Props 기반, API 미사용 ✓
│   ├── SignalBadge.tsx           [기존] ✓
│   ├── WakingBanner.tsx          [기존] ✓
│   ├── ChartTooltip.tsx          [신규 포팅] ← ChartTooltip.jsx 기반
│   ├── BearBoxTooltip.tsx        [신규 포팅] ← BearBoxTooltip.jsx 기반
│   └── ChartSkeleton.tsx         [신규 포팅] ← ChartSkeleton.jsx 기반
├── hooks/
│   ├── useChartExport.ts         [신규 포팅] ← useChartExport.js 기반
│   └── useTheme.ts               [신규 포팅] ← useTheme.js 기반
├── utils/
│   └── chartHelpers.ts           [신규] 공통 순수 함수
└── tests/
    ├── issue101_dropdown.test.ts [기존] 26케이스 ✓
    ├── summaryCard.test.tsx      [신규] SummaryCard 테스트
    ├── chartTooltip.test.tsx     [신규] ChartTooltip 테스트
    └── chartHelpers.test.ts      [신규] 유틸 테스트
```

---

## 3. TypeScript 타입 설계 (03_frontend 포팅용)

### 3.1 툴팁 타입
```ts
export interface TooltipItem {
  name: string
  color: string
  value: string
  diff: string | null
}

export interface TooltipState {
  x: number
  y: number
  dayLabel: string
  items: TooltipItem[]
}

export interface BearBoxTooltipState {
  x: number
  y: number
  dateLabel: string
  currentValue: string | null
  nearestBox: {
    label: string
    price: string
    dist: string | null
    isPrediction: boolean
    endDate: string | null
  } | null
}
```

### 3.2 차트 내보내기 타입
```ts
export interface UseChartExportReturn {
  exportPng: () => Promise<void>
  exporting: boolean
  exportError: string | null
}
```

---

## 4. HTML 오버레이 툴팁 설계 (F-01/02/03)

### 4.1 동작 원리
```
lightweight-charts 인스턴스
  └─ subscribeCrosshairMove(param)
        ├─ param.point  → { x, y } 픽셀 좌표
        ├─ param.time   → 날짜(Day index)
        └─ param.seriesData.get(seriesRef.current)
            ↓
      useChartTooltip 훅 (상태 계산, BUG-04 useMemo 적용)
            ↓
      ChartTooltip 컴포넌트 (HTML 렌더링)
            ↓
      visibility:hidden → chart-tooltip--visible 클래스 전환
      (BUG-05: DOM 유지, BUG-08: transition 애니메이션)
```

---

## 5. 아키텍처 GATE (코드 반려 기준) v2

| GATE | 규칙 | 검사 방법 |
|---|---|---|
| GATE-1 | API URL 하드코딩 금지 | grep `http://\|localhost` |
| GATE-2 | 컴포넌트 내 `fetch()` 직접 호출 금지 | grep `await\s+fetch\s*\(` |
| GATE-3 | `chartRef.current` null 체크 | grep `chartRef.current` 이후 조건 확인 |
| GATE-4 | TypeScript `any` 사용 금지 (03_frontend) | tsc --noEmit |
| GATE-5 | 언마운트 후 state 업데이트 | `cancelledRef` 패턴 확인 |

---

## 6. 테스트 전략 v2

| 레이어 | 도구 | 대상 | 기준 |
|---|---|---|---|
| 유닛 | Vitest | 04_frontend 전체 | 76케이스 통과 |
| 유닛 | Vitest | 03_frontend | 40케이스+ |
| 시각 | Playwright | 375px / 1280px | 가로 스크롤 없음 |
| 아키텍처 | grep 정적 분석 | 두 프로젝트 GATE 1~5 | 0건 |

---

*Tech Lead 에이전트 서명: PRODUCT_SPEC v2 기반 기술 설계 완료. FROZEN.*
