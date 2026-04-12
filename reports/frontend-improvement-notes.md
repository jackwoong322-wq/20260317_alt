# Frontend Improvement Notes

## Goal

`03_frontend` 화면을 `01_pairUSDT/033_visualizer_html.py` 실행 결과와 최대한 가깝게 맞추되, 현재 프로젝트의 프런트 구조 안에서 유지보수 가능한 형태로 정리한다.

기준 방향:

- 차트가 화면의 주인공이어야 한다.
- 분석 도구처럼 보이되, 과장된 트레이딩 UI처럼 보이지 않아야 한다.
- 사이드바, 사이클 토글, 오버레이, 툴팁, 통계 바가 서로 경쟁하지 않고 차트를 보조해야 한다.
- 모바일에서도 기능을 잃지 않으면서 밀도만 조정되어야 한다.

## Current Status

- `03_frontend`는 legacy shell + 기존 `033` 차트 엔진을 iframe으로 렌더링하는 구조로 전환됨
- `chart-shell-v2.html` / `chart-v2.css` 기준으로 1차 디자인 정리 완료
- `npm run build` 통과
- 실제 최종 완성도는 백엔드 데이터 연결 상태에서 시각 확인 후 추가 조정 필요

## Improvement Areas

### 1. Layout Alignment

- 헤더 높이와 좌우 패딩을 `033_visualizer_html.py` 결과 화면과 더 정밀하게 맞추기
- 사이드바 폭과 메인 차트 비율을 실제 캡처 기준으로 미세 조정
- 차트 툴바의 세로 정렬과 버튼 간격 통일
- 통계 바 높이와 내부 패딩을 더 얇고 밀도 있게 조정
- 데스크톱에서 차트 영역이 최대한 넓게 보이도록 불필요한 wrapper 여백 제거

### 2. Typography

- 헤더 타이틀의 자간과 서브타이틀 크기를 실제 기준 화면과 더 가깝게 조정
- 사이드바 코인 심볼과 코인명 대비를 더 명확하게 분리
- 툴바 라벨과 토글 버튼 텍스트의 시각 밀도를 통일
- 툴팁, 박스 라벨, 통계 바의 작은 텍스트 크기를 한 단계씩 재검토
- 숫자 영역은 `tabular-nums` 적용 여부를 전체 점검

### 3. Color and Contrast

- 배경색, 패널색, 테두리색의 차이를 더 미세하게 조정해서 깊이감은 유지하고 번잡함은 줄이기
- 활성 상태의 cyan 강조를 조금 더 절제해서 "하이라이트"만 되도록 정리
- bear/bull, high/low, prediction 관련 강조색의 역할을 명확히 분리
- 통계 바와 툴바의 비활성 상태 색이 너무 죽지 않도록 가독성 보정
- 툴팁 내부 텍스트 대비를 높여 정보 읽기성을 강화

### 4. Sidebar Interaction

- 코인 선택 행의 hover / active / checked 상태를 더 또렷하게 정리
- 검색 input의 focus 상태를 더 정교하게 다듬기
- 코인명이 긴 경우 잘림 방식과 최대 폭 재조정
- 선택된 코인이 여러 개인 경우에도 리스트 가독성이 유지되도록 spacing 점검

### 5. Toolbar and Cycle Toggles

- cycle 버튼의 inactive / active 상태 대비를 더 명확하게 만들기
- 현재 cycle 강조 방식이 기준 화면과 얼마나 차이나는지 시각 비교 후 조정
- SHOW 토글 버튼의 디자인을 부가 컨트롤처럼 더 가볍게 만들지 검토
- 모바일에서 툴바가 줄바꿈될 때 우선순위와 순서를 정리

### 6. Chart Framing

- 차트 canvas 여백, legend 위치, overlay 위치를 실제 `033` 결과와 더 세밀하게 맞추기
- legend box의 크기와 blur 강도를 조정해 차트 위에 얹혔을 때 덜 무겁게 보이게 만들기
- overlay label이 겹칠 때 시각적으로 덜 지저분하게 보이도록 스타일 단순화 검토
- crosshair tooltip의 박스 크기와 내부 리듬을 더 정리

### 7. Mobile and Responsive

- 모바일에서 sidebar를 상단 패널로 접는 방식 개선 검토
- 모바일 차트 최소 높이 재조정
- 작은 화면에서 coin list와 toolbar가 차트를 과도하게 밀어내지 않도록 조정
- 터치 환경에서 버튼과 코인 행의 hit area 점검

### 8. Technical Cleanup

- 현재 legacy shell이 `chart-shell.html`과 `chart-shell-v2.html`로 이원화되어 있어 정리 필요
- `chart.css`와 `chart-v2.css` 중 실제 사용 자산만 남기고 정리
- 사용하지 않는 초기 React 차트 컴포넌트(`App.tsx`, `CryptoChart.tsx`, `CoinSelector.tsx`, `useChartData.ts`)의 역할 재정의 또는 정리 검토
- iframe 기반 구조를 계속 유지할지, 이후 React native 구조로 다시 흡수할지 결정 필요

## Recommended Next Steps

1. 백엔드와 프런트를 함께 실행한 상태에서 실제 데이터가 들어간 화면을 기준 캡처와 직접 비교한다.
2. 레이아웃 비율과 타이포 크기부터 먼저 맞춘다.
3. 그 다음 색/상태 표현을 다듬는다.
4. 마지막으로 모바일과 기술 정리를 진행한다.

## Run Commands

### Backend

```powershell
cd E:\source\20260317_alt\02_backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd E:\source\20260317_alt\03_frontend
npm run dev -- --host 127.0.0.1 --port 4173
```

## File References

- `E:\source\20260317_alt\03_frontend\src\LegacyAnalyzerApp.tsx`
- `E:\source\20260317_alt\03_frontend\public\legacy\chart-shell-v2.html`
- `E:\source\20260317_alt\03_frontend\public\legacy\chart-v2.css`
- `E:\source\20260317_alt\01_pairUSDT\033_visualizer_html.py`
- `E:\source\20260317_alt\01_pairUSDT\templates\chart.html`
- `E:\source\20260317_alt\01_pairUSDT\templates\chart.css`
