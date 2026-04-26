# Claude Code 작업 규칙

> 코딩 규칙·기술스택·프로젝트 구조는 **AGENTS.md** 참조
> 테스트 규칙은 **test_rules.md**, 워크플로우 세부 규칙은 **workflow_rules.md** 참조

---

## 자동 승인
- 브랜치/커밋/코드수정/PR/머지, Jest실행, gh issue/pr

## 승인 필요
- API키·토큰·개인정보·외부전송·파일다운로드
- **배포 (Vercel/Render 등) — 명시적 요청 시에만 실행**
- **PR 머지 전 Vercel/Render 자동 배포 연동 여부 확인 후 사용자 승인 필요**

---

## 작업 스타일

- 코드를 먼저 수정한 뒤 이슈를 등록하는 후등록 방식
- "이슈 등록하고 PR 머지까지 해" 한 마디로 아래 전체를 처리:
  1. 이슈 생성
  2. 브랜치 생성
  3. 커밋 (Closes #N 포함)
  4. PR 생성
  5. 머지
  6. 이슈 코멘트 추가 (변경 내용)
  7. 이슈 closed 확인

---

## 이슈 처리 사이클 (게이트 방식)

### STEP 1 — 분석 & 계획
- git pull → 브랜치(feature/#N) 생성
- /temp/#N/context.md 생성 (TEMPLATE 복사)
- 이슈 분석 → 영향 범위 파악 → 계획서 작성

> ✅ GATE 1: context.md 생성 완료 / 계획서 작성 완료 → STEP 2 진행

### STEP 2 — 코드 수정
- 계획서 기준 코드 수정
- 수정 중 결정사항·변경사항 즉시 context.md에 기록

> ✅ GATE 2: 코드 수정 완료 / context.md 업데이트 → STEP 3 진행

### STEP 3 — 품질 검사
- 린트·타입체크 자동 실행 → 오류 즉시 수정
- 테스트 작성 및 실행 (test_rules.md 기준)

> ✅ GATE 3: 린트·타입체크 통과 / 테스트 통과 → STEP 4 진행

### STEP 4 — 사양서 판단
- 사양서 업데이트 판단: 추가 / 유지 / 삭제 중 선택

> ✅ GATE 4: 판단 완료 → STEP 5 진행

### STEP 5 — 보고서 & 마무리
- /reports/#N.md 저장
- gh issue comment 등록
- 커밋(Closes #N) → 푸시 → PR → 머지

> ✅ GATE 5: 보고서 저장 / issue comment 등록 확인 후 PR 생성

---

## 파일 탐색
- Grep 우선, 전체 읽기는 Grep 실패 시만 허용
- 한 번 읽은 파일 재읽기 금지

## 임시 파일
- /temp/#이슈번호/ 에 저장
- 프로젝트 루트·src 내 임시 파일 금지

## Claude 메모리
- MEMORY.md / workflow_rules.md / test_rules.md
