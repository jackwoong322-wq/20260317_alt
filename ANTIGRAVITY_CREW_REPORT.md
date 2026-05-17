# ANTIGRAVITY_CREW_REPORT.md — 대시보드 2.0 오픈크루 스프린트 최종 보고서

> 작성일: 2026-05-17 | 브랜치: `feature/dashboard-2.0` | 서명: PM · Tech Lead · Developer · QA

---

## 1. 스프린트 개요

| 항목 | 내용 |
|---|---|
| 목표 | 비트코인 사이클 대시보드 2.0 — HTML 오버레이 툴팁 및 아키텍처 정비 |
| 기간 | 2026-05-17 (단일 세션) |
| 브랜치 | `feature/dashboard-2.0` ← `main` |
| 최종 커밋 | `e16affb` |
| 빌드 결과 | ✅ 성공 (346KB gzip 109KB) |
| 테스트 결과 | ✅ **53 / 53 통과** (4개 파일) |

---

## 2. 크루별 수행 내역

### 2.1 PM 에이전트 (회차 1~2, 29~30)

**산출물:**
- `PRODUCT_SPEC.md` 작성 및 FROZEN 처리
- 기능 우선순위 결정: P0(F-01~03), P1(F-04~06), P2(F-07~08)
- 최종 회고 주도

**결정 사항:**
- F-04(모바일), F-05(테마), F-06(스켈레톤) → 다음 스프린트 이관

---

### 2.2 Tech Lead 에이전트 (회차 2~3, 16~19)

**산출물:**
- `ARCHITECTURE.md` 작성 및 FROZEN 처리
- 아키텍처 GATE 3개 정의 및 코드 리뷰 수행

**리뷰 결과:**

| GATE | 위반 내용 | 처리 결과 |
|---|---|---|
| GATE-1 | API URL 하드코딩 | ✅ 위반 없음 |
| GATE-2 | `SummaryCard.jsx`에서 `fetch()` 직접 호출 발견 | 🔴 **반려 → Developer 수정** |
| GATE-3 | `chartRef.current` null 체크 | ✅ 확인됨 |

**반려 사유서 (1회, 회차 16):**
> `SummaryCard.jsx` 81번 줄에서 `fetch(\`\${API_BASE}/api/bear-boxes...\`)` 직접 호출 확인.
> 아키텍처 원칙 2번(백엔드 로직 분리) 위반. `api.js`에 `fetchSummaryData` 함수 추가 후
> 컴포넌트는 해당 함수만 호출하도록 리팩토링 요구. 루프 카운트 +1.

**재검증:** Developer 수정 후 PASS ✅

---

### 2.3 Developer 에이전트 (회차 4~15, 17~18)

**구현 파일:**

| 파일 | 분류 | 설명 |
|---|---|---|
| `src/mocks/dashboardMock.js` | 신규 | 목 데이터: MOCK_DASHBOARD_SUMMARY, fetchDashboardSummary, mockCycleComparison, mockBearBoxData, mockBullBoxData |
| `src/hooks/useChartTooltip.js` | 신규 | 크로스헤어 이벤트 → 툴팁 상태 계산 커스텀 훅 (뷰포트 클리핑 보정 포함) |
| `src/components/ChartTooltip.jsx` | 신규 | HTML 오버레이 툴팁 UI (position:absolute, pointer-events:none) |
| `src/styles/Tooltip.css` | 신규 | 툴팁 전용 스타일 + 등장 애니메이션 + 모바일 적응 |
| `src/components/CycleComparisonChart.jsx` | 수정 | useChartTooltip + ChartTooltip 통합 (seriesRefsRef 도입) |
| `src/lib/api.js` | 수정 | `fetchSummaryData()` 추가 |
| `src/components/SummaryCard.jsx` | 수정 | 직접 fetch 제거 → fetchSummaryData 경유 (GATE-2 해소) |

**빌드 오류 1건 자체 수정:**
> `ChartTooltip.jsx`에서 `prop-types` 패키지 import 시도 → 미설치 패키지.
> PropTypes 선언 제거 후 JSDoc `@param` 주석으로 대체. 빌드 성공.

---

### 2.4 QA 에이전트 (회차 20~26)

**테스트 파일:**
- `src/tests/chartTooltip.test.jsx` (13개 케이스)
  - ChartTooltip 렌더링 9개
  - 아키텍처 규칙 정적 검증 4개

**최종 테스트 결과:**

| 파일 | 케이스 | 결과 |
|---|---|---|
| `issue102_chart_clip.test.jsx` | 25 | ✅ 전체 통과 |
| `SignalBadge.test.jsx` | 6 | ✅ 전체 통과 |
| `chartTooltip.test.jsx` | 13 | ✅ 전체 통과 |
| `dashboardMock.test.js` | 9 | ✅ 전체 통과 |
| **합계** | **53** | **✅ 53/53** |

**결함 발견 이력:**

| 결함 ID | 발견 시점 | 내용 | 처리 |
|---|---|---|---|
| BUG-01 | 회차 19 | `prop-types` 미설치로 빌드 실패 | Developer 자체 수정 (회차 19) |
| BUG-02 | 회차 24 | `dashboardMock.js` 기존 테스트 인터페이스 불일치 | Developer 수정 (회차 25) |

---

## 3. 구현된 기능 (F-01~03)

### F-01: HTML 오버레이 툴팁 시스템

```
lightweight-charts.subscribeCrosshairMove(param)
  └─ useChartTooltip.js (훅)
       ├─ 뷰포트 클리핑 보정 (calcClippedPosition)
       └─ tooltipState { x, y, dayLabel, items[] }
           └─ ChartTooltip.jsx (UI)
               └─ position:absolute, z-index:20, pointer-events:none
```

### F-02: 크로스헤어 툴팁 데이터 (CycleComparisonChart)
- `seriesRefsRef`로 각 시리즈 lightweight-charts 인스턴스 추적
- `param.seriesData.get(seriesRef)`로 해당 시점 값 추출
- Day 레이블: epoch 기준 상대 일수 계산

### F-03: 뷰포트 클리핑 방지
- 툴팁이 컨테이너 우측 경계 초과 시 → 커서 왼쪽에 표시
- 하단 경계 초과 시 → 컨테이너 하단 8px 위에 고정

---

## 4. 다음 스프린트 이관 백로그

| ID | 기능 | 우선순위 | 이유 |
|---|---|---|---|
| F-04 | 모바일 375px 완전 적응 | P1 | Playwright 시각 검증 미완료 |
| F-05 | 다크/라이트 테마 토글 | P1 | UI 기획 추가 협의 필요 |
| F-06 | 차트 로딩 스켈레톤 | P1 | ChartSkeleton 컴포넌트 미구현 |
| F-07 | 사이클 전환 애니메이션 | P2 | P0 완료 후 착수 |
| F-08 | PNG 내보내기 | P2 | P0 완료 후 착수 |
| TECH-01 | BearBoxChart 툴팁 통합 | P1 | CycleComparison만 적용됨 |
| TECH-02 | Playwright 시각 검증 | P1 | 환경 미구축 |
| TECH-03 | 커버리지 측정 정확도 | P2 | v8 커버리지 설정 검토 필요 |

---

## 5. 크루 합의 서명

```
PM 에이전트      : 기획-설계 동기화 완료. 마일스톤 P0 달성 확인.
Tech Lead 에이전트: 아키텍처 GATE 3개 검증 완료. 반려 1회 → 수정 후 승인.
Developer 에이전트: F-01/02/03 구현 완료. 빌드 오류 2건 자체 수정.
QA 에이전트      : 53/53 테스트 통과. BUG-01/02 결함 발견 및 수정 확인.
```

---

*본 보고서는 `feature/dashboard-2.0` 브랜치 커밋 `e16affb` 기준으로 작성되었습니다.*
