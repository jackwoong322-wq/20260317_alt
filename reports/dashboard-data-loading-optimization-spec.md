# Dashboard Data Loading Optimization MVP Spec

## 목적

`03_frontend`의 초기 차트 로딩 시간을 줄인다.

현재 화면은 시작 시 `/api/dashboard-data`를 호출하고, backend는 Supabase에서 전체 dashboard 데이터를 매번 다시 조회한다. 데이터가 커지면서 초기 로딩이 느려졌기 때문에 이번 구현에서는 다음 MVP만 처리한다.

1. 기존 `/api/dashboard-data`에 backend cache 추가
2. 신규 API로 초기 payload를 BTC current cycle 중심으로 축소
3. 나머지 coin/cycle은 legacy chart에서 lazy load

이번 문서는 최종 아키텍처 문서가 아니다. 구현 가능한 MVP 기준으로 범위를 잠근다.

## MVP 원칙

- Supabase schema는 변경하지 않는다.
- `/api/dashboard-data`는 기존 legacy 호환 구조를 유지한다.
- 신규 `manifest`, `initial`, `cycle` API만 wrapper meta를 가진다.
- `data_version`은 DB run id가 아니라 backend snapshot version이다.
- partial update 완전 검증은 이번 범위 밖이다.
- 대신 032 완료 후 internal refresh, public `force_refresh` 금지, single snapshot cache, refresh lock으로 현실적인 안전장치를 둔다.
- `ALL_DATA`에는 `initialResponse.data` 또는 cycle merge 결과만 넣는다.
- meta와 manifest는 `window.__DASHBOARD_META__`, `window.__DASHBOARD_MANIFEST__`로 분리한다.
- frontend lazy load는 `ensureCycleLoaded()`와 `getCycleStatus()` 기준으로만 구현한다.
- `loadingCycles`는 `Map<string, Promise<void>>`를 사용한다.
- direct shell fallback은 개발용으로 제한하고, 배포는 React 주입과 `VITE_API_URL` 기준으로 동작한다.
- 커밋하지 않는다.

## 기존 API 유지

### `GET /api/dashboard-data`

기존 legacy 호환 API다.

정책:

- 응답 shape는 기존처럼 coin id keyed object를 유지한다.
- top-level에 `data_version`, `generated_at`, `cache_status`를 추가하지 않는다.
- public `force_refresh` query parameter를 제공하지 않는다.
- 이미 누군가 `?force_refresh=true`를 붙여 호출해도 cache bypass가 일어나면 안 된다.
- 이 API는 기존 화면 호환과 fallback 용도이며, MVP lazy load의 기본 경로가 아니다.

Cache:

- in-memory cache를 적용한다.
- cache miss 또는 TTL 만료 시 snapshot build를 수행한다.
- build가 성공한 뒤에만 cache를 교체한다.
- build 실패 시 기존 cache가 있으면 기존 cache를 유지한다.
- 기존 cache가 없고 build가 실패하면 오류를 반환한다.

권장 TTL:

- 10분

## Single Snapshot Cache

신규 API는 독립적으로 Supabase를 각각 조회하지 않는다.

정책:

- backend는 하나의 dashboard snapshot cache를 만든다.
- `/api/dashboard-manifest`, `/api/dashboard-initial-data`, `/api/dashboard-cycle-data`는 같은 snapshot에서 필요한 부분만 projection해서 반환한다.
- snapshot은 `data`, `manifest`, `data_version`, `generated_at`을 가진다.
- `data_version`은 snapshot build 시점의 backend 생성 version이다.
- DB row에 같은 `data_version`이 저장되어 있음을 검증하지 않는다.

예시:

```python
_DASHBOARD_SNAPSHOT_CACHE = {
    "snapshot": None,
    "created_at": 0.0,
}
```

snapshot 예시:

```python
{
    "data_version": "snapshot-20260507T001000Z",
    "generated_at": "2026-05-07T00:10:00Z",
    "data": {...},
    "manifest": {...},
}
```

### Refresh Lock

cache stampede를 막기 위해 process-local refresh lock을 둔다.

정책:

- cold cache에서 첫 요청이 build 중이면 다른 요청은 같은 build 완료를 기다린다.
- warm cache에서 refresh 중이면 다른 요청은 기존 stale cache를 반환할 수 있다.
- process-local lock만 보장한다.
- 다중 worker 전역 lock은 이번 범위 밖이다.

## 032 연동

032 예측 저장 완료 후 dashboard snapshot cache를 갱신한다.

Canonical 환경변수:

```text
DASHBOARD_CACHE_REFRESH_URL
DASHBOARD_CACHE_REFRESH_SECRET
```

정책:

- 032는 모든 Supabase delete/insert가 성공한 뒤에만 refresh endpoint를 호출한다.
- 환경변수가 없으면 warning만 남기고 032 자체는 실패 처리하지 않는다.
- refresh 실패도 예측 저장 성공을 되돌리지 않는다.
- 실패는 log에 명확히 남긴다.

Internal endpoint:

```text
POST /api/internal/dashboard-cache/refresh
```

요구사항:

- `X-Internal-Secret` header를 검증한다.
- secret은 환경변수에서만 읽는다.
- 인증 실패 시 403 또는 404를 반환한다.
- public API나 CORS 문서에 refresh endpoint를 일반 사용자용으로 노출하지 않는다.

성공 응답 예:

```json
{
  "ok": true,
  "data_version": "snapshot-20260507T001000Z",
  "generated_at": "2026-05-07T00:10:00Z",
  "cache_status": "refreshed",
  "build_duration_ms": 842
}
```

실패 응답 예:

```json
{
  "ok": false,
  "error": "dashboard snapshot refresh failed",
  "cache_status": "stale_kept"
}
```

## 신규 API

신규 API는 wrapper meta를 가진다.

공통 meta:

```json
{
  "data_version": "snapshot-20260507T001000Z",
  "generated_at": "2026-05-07T00:10:00Z",
  "cache_status": "hit"
}
```

### `GET /api/dashboard-manifest`

목표:

- 전체 coin metadata
- 각 coin의 사용 가능한 cycle 목록
- default coin/cycle
- initial payload 포함 여부
- lazy load 가능 여부

응답 예:

```json
{
  "data_version": "snapshot-20260507T001000Z",
  "generated_at": "2026-05-07T00:10:00Z",
  "cache_status": "hit",
  "default_coin_id": "bitcoin",
  "default_cycle_number": 5,
  "coins": [
    {
      "coin_id": "bitcoin",
      "symbol": "BTC",
      "name": "Bitcoin",
      "rank": 1,
      "cycles": [
        {
          "cycle_number": 5,
          "cycle_name": "Current Cycle (2025)",
          "is_current": true,
          "is_initially_loaded": true,
          "can_lazy_load": true,
          "has_data": true
        }
      ]
    }
  ]
}
```

Manifest 규칙:

- manifest는 coin/cycle 존재 여부와 lazy-load 가능 여부의 single source of truth다.
- UI는 `ALL_DATA`의 `cycles` 유무만으로 coin/cycle 목록을 만들지 않는다.
- `coins` 테이블 metadata는 가능한 한 전체를 포함한다.
- 기존 full payload builder의 “cycle 없는 coin 제외” 규칙을 manifest에는 적용하지 않는다.

Current cycle 선택:

1. 명시적인 `is_current` 판단이 가능하면 사용
2. 없으면 해당 coin의 최대 `cycle_number` 사용
3. `Current Cycle (2025)` 문자열은 label fallback으로만 사용

### `GET /api/dashboard-initial-data`

목표:

- 초기 화면에 필요한 최소 chart data만 반환한다.
- BTC current cycle은 실제 chart data를 포함한다.
- 다른 coin은 metadata container만 포함한다.

응답 예:

```json
{
  "data_version": "snapshot-20260507T001000Z",
  "generated_at": "2026-05-07T00:10:00Z",
  "cache_status": "hit",
  "data": {
    "bitcoin": {
      "symbol": "BTC",
      "name": "Bitcoin",
      "rank": 1,
      "cycles": [
        {
          "cycle_number": 5,
          "cycle_name": "Current Cycle (2025)",
          "data": [],
          "box_zones": [],
          "prediction_paths": {"bull": [], "bear": []},
          "peak_predictions": []
        }
      ]
    },
    "ethereum": {
      "symbol": "ETH",
      "name": "Ethereum",
      "rank": 2,
      "cycles": []
    }
  }
}
```

중요:

- legacy `ALL_DATA`에는 wrapper 전체가 아니라 `response.data`만 들어간다.
- `data_version`, `generated_at`, `cache_status`는 `window.__DASHBOARD_META__`에 저장한다.
- metadata-only coin의 `cycles: []`는 “아직 로드하지 않음”이다.
- “실제 데이터 없음”은 `getCycleStatus()`에서 `empty`로 따로 판정한다.

### `GET /api/dashboard-cycle-data`

요청:

```text
GET /api/dashboard-cycle-data?coin_id=ethereum&cycle_number=5
```

응답 예:

```json
{
  "data_version": "snapshot-20260507T001000Z",
  "generated_at": "2026-05-07T00:10:00Z",
  "cache_status": "hit",
  "coin_id": "ethereum",
  "symbol": "ETH",
  "cycle": {
    "cycle_number": 5,
    "cycle_name": "Current Cycle (2025)",
    "data": [],
    "box_zones": [],
    "prediction_paths": {"bull": [], "bear": []},
    "peak_predictions": []
  }
}
```

오류 정책:

- parameter 형식 오류: 400 또는 422
- manifest에 없는 coin/cycle: 404
- manifest에는 있지만 실제 chart row가 없는 경우: 200 + 빈 배열 + frontend `empty` 상태
- public refresh parameter는 제공하지 않는다.

## Frontend 상태 모델

### Window 객체

React 주입 후 shell 내부 상태:

```ts
window.__LEGACY_CHART_DATA__ = initialResponse.data;
window.__DASHBOARD_META__ = {
  data_version: initialResponse.data_version,
  generated_at: initialResponse.generated_at,
  cache_status: initialResponse.cache_status,
};
window.__DASHBOARD_MANIFEST__ = manifestResponse;
window.__API_BASE_URL__ = baseUrl;
```

legacy chart module 내부:

```ts
const ALL_DATA = window.__LEGACY_CHART_DATA__;
```

### Load State

```ts
window.__DASHBOARD_LOAD_STATE__ = {
  loadedCycles: new Set<string>(),
  loadingCycles: new Map<string, Promise<void>>(),
  loadError: new Map<string, string>(),
}
```

cycle key:

```ts
const cycleKey = `${coinId}:${cycleNumber}`;
```

초기화:

- initial payload에 포함된 BTC current cycle은 `loadedCycles`에 등록한다.
- metadata-only coin은 `loadedCycles`에 등록하지 않는다.

## `getCycleStatus()`

모든 UI는 cycle 상태를 이 함수 기준으로 판단한다.

```ts
type CycleStatus = "unloaded" | "loading" | "error" | "empty" | "loaded";

function getCycleStatus(coinId: string, cycleNumber: number): CycleStatus {
  ...
}
```

판정 규칙:

1. manifest에 coin/cycle이 없거나 `can_lazy_load=false`이면 UI에서는 unavailable로 표시한다. 이 값은 `CycleStatus`가 아니라 manifest capability다.
2. `loadingCycles.has(key)`이면 `loading`
3. `loadError.has(key)`이면 `error`
4. `loadedCycles.has(key)`이고 chart series가 있으면 `loaded`
5. `loadedCycles.has(key)`이고 API 성공 payload는 있으나 chart series가 비어 있으면 `empty`
6. 그 외에는 `unloaded`

Toggle 표시:

- `available`: manifest에 있고 lazy load 가능하지만 아직 `unloaded`
- `unavailable`: manifest에 없거나 `can_lazy_load=false`
- `loading`: `getCycleStatus() === "loading"`
- `error`: `getCycleStatus() === "error"`
- `empty`: `getCycleStatus() === "empty"`
- `loaded`: `getCycleStatus() === "loaded"`

## `ensureCycleLoaded()`

모든 coin/cycle 선택 경로는 반드시 이 함수를 통과한다.

```ts
async function ensureCycleLoaded(coinId: string, cycleNumber: number): Promise<void> {
  ...
}
```

책임:

- manifest 검증
- 중복 요청 방지
- `loadingCycles` promise 공유
- cycle API 호출
- `data_version` mismatch 처리
- `ALL_DATA` 병합
- `loadedCycles`/`loadError` 갱신
- redraw trigger

동작:

1. manifest에 없는 coin/cycle이면 요청하지 않고 unavailable 상태로 둔다.
2. 이미 `loaded` 또는 `empty`이면 추가 API 호출 없이 반환한다.
3. `loadingCycles`에 promise가 있으면 그 promise를 반환한다.
4. 새 fetch promise를 만들고 `loadingCycles.set(key, promise)`로 등록한다.
5. 성공 시 `ALL_DATA[coinId].cycles`에 cycle을 추가하거나 교체한다.
6. 성공 시 `loadedCycles.add(key)`, `loadError.delete(key)`를 수행한다.
7. 실패 시 `loadError.set(key, message)`를 수행한다.
8. finally에서 `loadingCycles.delete(key)`를 수행한다.
9. 상태 변경 후 `drawChart()`와 필요한 UI 갱신을 호출한다.

`data_version` mismatch:

- cycle 응답의 `data_version`이 `window.__DASHBOARD_META__.data_version`과 다르면 해당 응답을 버린다.
- MVP에서는 manifest/initial을 한 번 재요청하고 화면을 갱신한다.
- 반복 mismatch는 error 상태로 표시한다.

## UI Trigger

Coin 선택:

- 선택된 coin과 현재 `activeCycles` 조합을 확인한다.
- 필요한 cycle을 `ensureCycleLoaded()`로 병렬 로딩한다.
- 일부 실패해도 성공한 series는 유지한다.

Cycle toggle:

- 선택된 cycle과 현재 selected coins 조합을 확인한다.
- 필요한 cycle을 `ensureCycleLoaded()`로 병렬 로딩한다.

Stats/Legend:

- `unloaded`: 아직 로드 전
- `loading`: `데이터를 불러오는 중입니다.`
- `error`: `데이터를 불러오지 못했습니다. 다시 시도해 주세요.`
- `empty`: `선택한 cycle의 데이터가 없습니다.`
- `loaded`: 기존 chart/legend 표시

## React Iframe / Shell 계약

### Placeholder

`chart-shell-v2.html`은 다음 placeholder를 가진다.

```html
<script>
window.__LEGACY_CHART_DATA__ = "__LEGACY_CHART_DATA__";
window.__DASHBOARD_META__ = "__DASHBOARD_META__";
window.__DASHBOARD_MANIFEST__ = "__DASHBOARD_MANIFEST__";
window.__API_BASE_URL__ = "__API_BASE_URL__";
</script>
```

React `LegacyAnalyzerApp.tsx`는 다음 값을 주입한다.

```ts
html
  .replace('"__LEGACY_CHART_DATA__"', JSON.stringify(initialResponse.data))
  .replace('"__DASHBOARD_META__"', JSON.stringify({
    data_version: initialResponse.data_version,
    generated_at: initialResponse.generated_at,
    cache_status: initialResponse.cache_status,
  }))
  .replace('"__DASHBOARD_MANIFEST__"', JSON.stringify(manifestResponse))
  .replace('"__API_BASE_URL__"', JSON.stringify(baseUrl));
```

검증:

- 주입 후 placeholder 문자열이 남아 있으면 렌더링을 중단하고 오류 상태를 표시한다.
- shell과 React의 변수명을 반드시 일치시킨다.

### API Base URL

배포:

- React가 `import.meta.env.VITE_API_URL`을 읽어 `window.__API_BASE_URL__`로 주입한다.
- 배포 환경에서 shell 내부에 Render URL을 하드코딩하지 않는다.

개발 direct shell fallback:

- `/legacy/chart-shell-v2.html`을 직접 열었을 때만 fallback을 사용한다.
- fallback 우선순위:
  1. 이미 주입된 `window.__API_BASE_URL__`
  2. query parameter `apiBaseUrl`, 단 allowlist 통과 시에만 사용
  3. local dev fallback `http://127.0.0.1:8000`
- production direct shell 동작 보장은 이번 MVP 범위 밖이다.

Direct shell에서 주입 데이터가 없으면:

1. fallback API base URL 결정
2. `/api/dashboard-manifest` fetch
3. `/api/dashboard-initial-data` fetch
4. `window.__LEGACY_CHART_DATA__ = initialResponse.data`
5. 이후 동일한 lazy load 상태 모델 사용

## Build / Dist Sync

source of truth:

- `01_pairUSDT/templates/*.ts`

generated/runtime files:

- `01_pairUSDT/templates/dist/*.js`
- `03_frontend/public/legacy/dist/*.js`
- `03_frontend/dist/**`

원칙:

- legacy chart 변경은 `01_pairUSDT/templates/*.ts`를 수정한다.
- `03_frontend/public/legacy/dist/*.js`만 직접 수정하지 않는다.
- source와 dist가 불일치한 상태로 배포하지 않는다.

명령:

```powershell
cd 01_pairUSDT
npm run build:ts
```

그 다음 `01_pairUSDT/templates/dist/*.js`를 `03_frontend/public/legacy/dist/*.js`로 동기화한다.

```powershell
Copy-Item -Path .\templates\dist\*.js -Destination ..\03_frontend\public\legacy\dist\ -Force
```

그 다음:

```powershell
cd ..\03_frontend
npm run build
```

검증:

- `git diff`에서 `templates/*.ts` 변경과 대응되는 dist 변경이 있는지 확인한다.
- shell의 `chart.js?v=...` cache bust 값은 legacy dist가 변경될 때 갱신한다.

## Test Plan

### Backend

AGENTS.md 기준을 따른다.

- 테스트 작성은 `unittest` + `unittest.mock` 기준
- `pytest`는 runner로만 사용 가능
- Supabase client와 외부 API 호출은 mock 처리
- mock 선언은 파일 상단 또는 `setUp`
- coverage 80% 이상 목표

명령:

```powershell
python -m pytest unit_tests/02_backend -q
```

필수 테스트:

- `/api/dashboard-data` 기존 response shape 유지
- public `GET /api/dashboard-data?force_refresh=true`가 cache bypass를 하지 않음
- internal refresh secret 성공/실패
- refresh build 성공 시 atomic swap
- refresh build 실패 시 기존 cache 유지
- cold cache build 실패 시 오류 반환
- concurrent cold cache 요청에서 process-local full build 1회
- snapshot에서 manifest/initial/cycle projection 반환
- 신규 API wrapper meta 포함
- `data_version` mismatch 대응
- 032 저장 성공 후 refresh 호출
- 032 저장 실패 시 refresh 미호출
- 032 refresh env 누락 시 warning

### Frontend

명령:

```powershell
cd 03_frontend
npm run build
npm run dev
```

수동 확인:

- 초기 BTC current cycle 표시
- ETH 선택 시 lazy load 후 표시
- 과거 cycle 선택 시 lazy load 후 표시
- 이미 로드한 cycle 재선택 시 추가 API 호출 없음
- lazy load 실패 시 error 상태 표시
- empty cycle은 데이터 없음 상태 표시
- current active prediction box/path 표시 유지

Playwright 권장 기준:

- `route.fulfill`로 manifest/initial/cycle API mock
- iframe은 `frameLocator` 또는 frame handle로 접근
- 초기 로드에서 `/api/dashboard-data` 호출 없음
- 초기 로드에서 `/api/dashboard-manifest`, `/api/dashboard-initial-data` 호출 확인
- 동일 cycle 재선택 시 `/api/dashboard-cycle-data` 중복 호출 없음
- version mismatch mock 시 initial 재요청 또는 error 상태 확인
- lazy load 실패 mock 시 error 상태 확인
- empty payload mock 시 empty 상태 확인
- canvas nonblank pixel ratio 1% 이상
- placeholder 문자열 미잔존

스크린샷:

- `screenshots/dashboard-initial-btc-current.png`
- `screenshots/dashboard-lazy-eth-current.png`
- `screenshots/dashboard-lazy-btc-2021.png`
- `screenshots/dashboard-lazy-load-error.png`

## 성능 목표

- warm cache `/api/dashboard-data`: 500ms 이하 권장
- `/api/dashboard-manifest`: 300ms 이하 권장
- `/api/dashboard-initial-data`: 1초 이하 권장
- initial payload: 기존 full payload보다 명확히 작아야 함
- lazy cycle API: 1초 이하 권장
- 이미 로드한 cycle 재선택 시 추가 network 요청 없음

## MVP 비범위

- Supabase schema 변경
- DB run id 또는 table-level `data_version` 추가
- partial update 완전 검증
- 다중 worker 전역 lock
- Redis 같은 외부 cache
- DB materialized view
- production direct shell 완전 보장
- `/api/dashboard-data` wrapper 구조 변경
- 033 standalone HTML 대규모 변경

## 후속 개선

팀 검토에서 나온 다음 항목은 MVP 이후로 미룬다.

- Supabase schema에 prediction run id 또는 `data_version` 추가
- 세 예측 테이블의 동일 run 검증
- 032 delete/insert를 DB transaction 또는 staging table 방식으로 개선
- 다중 worker/global cache invalidation
- Redis 또는 외부 cache 도입
- Vercel rewrite로 direct shell production API base URL 보장
- dashboard snapshot을 정적 JSON으로 생성해 CDN/Vercel에서 제공
- Playwright 정식 test suite 추가
