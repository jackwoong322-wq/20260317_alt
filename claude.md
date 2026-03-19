# 프로젝트 작업 규칙

> 세부 규칙은 workflow_rules.md / test_rules.md 참조

---

## 자동 승인
- 브랜치/커밋/코드수정/PR/머지, Jest실행, gh issue/pr

## 승인 필요
- API키·토큰·개인정보·외부전송·파일다운로드

---

## 이슈 처리 사이클 (게이트 방식)

### STEP 1 — 분석 & 계획
- git pull → 브랜치(feature/#N) 생성
- /temp/#N/context.md 생성 (TEMPLATE 복사)
- 이슈 분석 → 영향 범위 파악 → 계획서 작성
- 기능 삭제 감지 시 → ⚠️ 경고 코멘트 준비

> ✅ GATE 1: context.md 생성 완료 / 계획서 작성 완료 → STEP 2 진행

---

### STEP 2 — 코드 수정
- 계획서 기준 코드 수정
- 수정 중 결정사항·변경사항 즉시 context.md에 기록

> ✅ GATE 2: 코드 수정 완료 / context.md 수정 이력 업데이트 → STEP 3 진행

---

### STEP 3 — 품질 검사
- 린트·타입체크 자동 실행 → 오류 즉시 수정
- 이슈 테스트 20개 작성 및 실행 (커버리지 80% 이상)
- 실행 순서: 단위 → 전체(--passWithNoTests) → 커버리지(--coverage)
- unit-tests/ 실행 → 실패 시 사이드이펙트 수정

> ✅ GATE 3: 린트·타입체크 통과 / 이슈 테스트 20개 통과 / 커버리지 80%↑ / unit-tests 통과 / context.md 업데이트 → STEP 4 진행

---

### STEP 4 — 사양서 판단
- 품질관리팀 검토
- 사양서 업데이트 판단: 추가 / 유지 / 삭제 중 선택

> ✅ GATE 4: 사양서 업데이트 판단 완료 (추가/유지/삭제 명시) → STEP 5 진행

---

### STEP 5 — 보고서 & 마무리
- /reports/#N.md 저장
- gh issue comment 등록 (보고서 내용 동일)
- 커밋(Closes #N) → 푸시 → PR → 머지

> ✅ GATE 5: 보고서 저장 완료 / gh issue comment 등록 / PR 머지 완료 → 이슈 종료

---

## 파일 탐색
- Grep 우선, 전체 읽기는 Grep 실패 시만 허용
- 한 번 읽은 파일 재읽기 금지, 전체 읽기 시 이유 명시

## 임시 파일
- /temp/#이슈번호/ 에 저장 (예: /temp/86/analysis.md)
- 프로젝트 루트·src 내 임시 파일 금지, .gitignore 등록

## 작업 기억 시스템
- 이슈 시작 시 /temp/TEMPLATE/context.md 복사 → /temp/#N/context.md
- 작업 중 결정사항·변경사항·수정 이력 즉시 context.md 업데이트
- 체크리스트 항목 완료 시 즉시 체크 표시

## 셀프체크 리마인더
- 각 단계 완료 시 자문: 계획대로 진행됐는가? 빠진 항목 없는가?
- 다음 단계 진행 전 context.md 체크리스트 확인 필수
- 예상과 다른 결과 발생 시 즉시 맥락 노트에 기록 후 재판단

## 자동 메뉴얼 시스템
- 작업 키워드·의도·위치 감지 시 tech_stack.md 자동 참조 후 진행

## Claude 메모리
- workflow_rules.md / tech_stack.md / MEMORY.md
