# 오픈크루 100회 스프린트 — 실행 계획서

> PM 에이전트 작성 | 2026-05-17 | 상태: ACTIVE

---

## 현재 상태 진단

| 항목 | 04_frontend | 03_frontend |
|---|---|---|
| 테스트 | ✅ 76/76 | ✅ 26/26 |
| 빌드 | ✅ 355KB | ✅ 정상 |
| HTML 툴팁 | ✅ 완료 | ❌ 미구현 |
| 테마 토글 | ✅ 완료 | ❌ 미구현 |
| 스켈레톤 | ✅ 완료 | ❌ 미구현 |
| PNG 내보내기 | ✅ 완료 | ❌ 미구현 |
| Playwright E2E | ⚠️ 파일만 있음 | ❌ 없음 |

---

## 100회 루프 실행 계획

### Phase A (Loop 1~10): PRODUCT_SPEC v2 + ARCHITECTURE v2
- 03_frontend 포팅 요구사항 추가
- TypeScript 타입 설계 추가
- 공유 가능 유틸/훅 패턴 정의

### Phase B (Loop 11~40): 03_frontend 포팅
- 공통 훅: `useChartExport.ts`, `useTheme.ts`
- 공통 컴포넌트: `ChartTooltip.tsx`, `BearBoxTooltip.tsx`, `ChartSkeleton.tsx`
- 03_frontend 전용 통합

### Phase C (Loop 41~60): 04_frontend 고도화
- `useBearBoxTooltip` / `useBullBoxTooltip` 정밀도 개선
- 다크/라이트 테마 CSS 변수 정비
- 모바일 375px 완성도 향상

### Phase D (Loop 61~80): QA 강화
- 04_frontend 테스트 80+ 케이스 목표
- 03_frontend 테스트 40+ 케이스 목표
- Playwright 실행 가능 상태 구축

### Phase E (Loop 81~95): 성능 + 접근성 감사
- Lighthouse 지표 기준 최적화
- ARIA 패턴 전수 점검
- 번들 크기 최적화

### Phase F (Loop 96~100): 릴리즈 + 회고
- 최종 CREW REPORT v3
- PRODUCT_SPEC v2 FROZEN
- main 브랜치 배포 태그

---

## PM 우선순위 결정

1. **03_frontend 포팅** — 두 프로젝트 간 기능 패리티 확보
2. **테스트 케이스 확충** — 80%+ 커버리지 목표
3. **Playwright 실행 가능 상태** — 현재 파일만 있고 실행 안 됨

---

*PM 에이전트 서명: 2026-05-17 스프린트 계획 배포*
