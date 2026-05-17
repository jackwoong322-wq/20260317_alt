# 대시보드 2.0 — 제품 기획서 (PRODUCT_SPEC.md) v2

> 작성: PM 에이전트 | 버전: 2.0 | 날짜: 2026-05-17 | 상태: **FROZEN**
> 변경: v1 → v2 — 03_frontend 포팅 요구사항 추가, TypeScript 스펙 명시

---

## 1. 제품 비전

비트코인 사이클 분석 대시보드를 "단순 차트 뷰어"에서 **인터랙티브 분석 플랫폼**으로 격상한다.  
사용자는 차트 위에서 마우스를 움직이는 것만으로 각 사이클의 핵심 지표를 즉시 파악하고,  
모바일(375px)에서 데스크탑(1440px)까지 끊김 없는 경험을 제공한다.

**v2 추가**: `04_frontend`(JavaScript)와 `03_frontend`(TypeScript) 두 프로젝트 간 기능 패리티(Feature Parity)를 확보한다.

---

## 2. 목표 사용자

| 페르소나 | 특징 | 핵심 니즈 |
|---|---|---|
| 비트코인 장기 투자자 | 사이클 고점/저점 비교 필요 | 현재 사이클이 과거 대비 어느 위치인지 즉시 확인 |
| 단기 트레이더 | 분봉/일봉 패턴 분석 | 박스존 레이블과 예측 라인 명확성 |
| 모바일 사용자 | 이동 중 확인 | 375px 뷰포트에서 차트 미잘림, 탭/터치 친화적 UI |

---

## 3. 기능 목록 (전체 스프린트 범위)

### P0 — 반드시 구현 (MVP 차단)
| ID | 기능 | 04_frontend | 03_frontend |
|---|---|---|---|
| F-01 | HTML 오버레이 툴팁 | ✅ | ⬜ 포팅 필요 |
| F-02 | 크로스헤어 툴팁 데이터 | ✅ | ⬜ 포팅 필요 |
| F-03 | Bear/Bull Box 툴팁 | ✅ | ⬜ 포팅 필요 |

### P1 — 중요 (스프린트 내 완성 목표)
| ID | 기능 | 04_frontend | 03_frontend |
|---|---|---|---|
| F-04 | 모바일 375px 적응 | ✅ | ⬜ 포팅 필요 |
| F-05 | 다크/라이트 테마 토글 | ✅ | ⬜ 포팅 필요 |
| F-06 | 차트 로딩 스켈레톤 | ✅ | ⬜ 포팅 필요 |

### P2 — 개선
| ID | 기능 | 04_frontend | 03_frontend |
|---|---|---|---|
| F-07 | 사이클 전환 애니메이션 | ✅ | ⬜ |
| F-08 | PNG 내보내기 | ✅ | ⬜ 포팅 필요 |

### TECH — 엔지니어링
| ID | 기능 | 상태 |
|---|---|---|
| TECH-01 | BullBox 툴팁 | ✅ |
| TECH-02 | Playwright E2E | ⚠️ 파일만 있음 |
| TECH-03 | 커버리지 임계값 | ✅ |
| TECH-04 | 03_frontend 테스트 확충 | ⬜ 필요 |

---

## 4. 수락 기준 (Acceptance Criteria) v2

### 04_frontend (JavaScript)
- [x] 모든 차트에 HTML 오버레이 툴팁 동작
- [x] 테마 토글 (localStorage 영속)
- [x] 스켈레톤 로딩
- [x] PNG 내보내기 (전 3개 차트)
- [x] 76개 유닛 테스트 통과
- [ ] Playwright E2E 실행 가능 상태

### 03_frontend (TypeScript)
- [ ] `useChartExport.ts` — TypeScript 포팅
- [ ] `useTheme.ts` — TypeScript 포팅  
- [ ] `ChartTooltip.tsx` — HTML 오버레이 툴팁
- [ ] `ChartSkeleton.tsx` — 스켈레톤 로딩
- [ ] 40개 이상 유닛 테스트

---

## 5. 기술 제약

### 공통
- **API**: `VITE_API_URL` 환경 변수 (하드코딩 절대 금지)
- **목 데이터**: 백엔드 미연결 시 `src/mocks/dashboardMock.[js|ts]` 활용
- **테스트**: Vitest (유닛), Playwright (시각 검증)

### 04_frontend (JavaScript)
- React 18 + Vite 5 (JS/JSX)
- lightweight-charts v4.x
- CSS 변수 + OKLCH 색상 시스템

### 03_frontend (TypeScript)
- React 18 + Vite 5 (TS/TSX)
- TypeScript strict mode
- 인라인 스타일 (CSSProperties) — CSS 모듈 없음

---

## 6. 마일스톤 (100회 루프)

| 회차 | 단계 | 담당 | 목표 |
|---|---|---|---|
| 1~10 | 기획-설계 동기화 v2 | PM + Tech Lead | PRODUCT_SPEC v2, ARCHITECTURE v2 FROZEN |
| 11~40 | 03_frontend 포팅 | Developer | TypeScript 훅/컴포넌트 완성 |
| 41~60 | 04_frontend 고도화 | Developer + Tech Lead | 코드 품질, 성능 |
| 61~80 | QA 강화 | QA + Developer | 80+케이스, Playwright 실행 |
| 81~95 | 성능+접근성 감사 | Tech Lead + Developer | Lighthouse 기준 |
| 96~100 | 릴리즈 + 회고 | PM 주도 전원 | CREW REPORT v3, 배포 태그 |

---

*PM 에이전트 서명: v2 기획서 배포 — Tech Lead 검토 대기*
