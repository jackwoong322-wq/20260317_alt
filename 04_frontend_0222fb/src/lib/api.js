/*
 * Backend API client
 *
 * The frontend reads all chart data through the backend API rather than
 * talking directly to Supabase from the browser.
 *
 * Render cold-start 대응:
 *   - Render 무료 플랜은 비활성 시 Sleep → 첫 요청 시 30~60초 재부팅
 *   - 네트워크 실패 시 최대 MAX_RETRIES 회 재시도 (RETRY_INTERVAL_MS 간격)
 *   - onRetry 콜백으로 UI에 재시도 상태를 실시간 전달
 */

function formatApiDetail(detail) {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  try {
    return JSON.stringify(detail)
  } catch {
    return String(detail)
  }
}

/*
 * API base URL rules:
 *  - VITE_API_LOCAL_URL 가 있으면 로컬 dev 환경 (로컬 uvicorn)
 *  - 없으면 VITE_API_URL (Render 배포 서버) 를 항상 사용
 */
function resolveApiBaseUrl() {
  if (import.meta.env.DEV && import.meta.env.VITE_API_LOCAL_URL) {
    return import.meta.env.VITE_API_LOCAL_URL
  }
  return import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
}

const API_BASE_URL = resolveApiBaseUrl()

// ── Render cold-start 재시도 설정 ──────────────────────────────────
const MAX_RETRIES = 8          // 최대 재시도 횟수 (총 최대 ~80초 대기)
const RETRY_INTERVAL_MS = 10_000  // 재시도 간격 (10초)

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Render 서버가 Sleep 상태일 때 재부팅될 때까지 자동 재시도
 *
 * @param {string} path       - API 경로 (e.g. '/api/bear-boxes')
 * @param {Object} params     - Query parameters
 * @param {Function} onRetry  - (attempt, maxRetries) => void  재시도 상태 콜백
 */
async function apiFetch(path, params = {}, onRetry = null) {
  const url = new URL(`${API_BASE_URL}${path}`)
  Object.entries(params).forEach(([key, val]) => {
    if (val !== null && val !== undefined) {
      url.searchParams.set(key, val)
    }
  })
  const urlStr = url.toString()

  let lastError = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(urlStr)

      if (!response.ok) {
        // HTTP 에러 (5xx 포함) — 재시도
        const errorData = await response.json().catch(() => ({}))
        const msg = formatApiDetail(errorData.detail) || `API error: ${response.status}`
        throw new Error(msg)
      }

      return response.json()

    } catch (err) {
      lastError = err

      // 마지막 시도였으면 바로 던짐
      if (attempt === MAX_RETRIES) break

      // onRetry 콜백으로 UI에 재시도 상태 전달
      if (typeof onRetry === 'function') {
        onRetry(attempt + 1, MAX_RETRIES)
      }

      await sleep(RETRY_INTERVAL_MS)
    }
  }

  throw lastError
}

/* Cycle comparison chart data */
export async function fetchCycleComparison(onRetry) {
  return apiFetch('/api/cycle-comparison', {}, onRetry)
}

/* Bear box data and predictions */
export async function fetchBearBoxes(cycleNumber = 4, onRetry) {
  return apiFetch('/api/bear-boxes', { cycle: cycleNumber }, onRetry)
}

/* Bull box data */
export async function fetchBullBoxes(cycleNumber = 3, onRetry) {
  return apiFetch('/api/bull-boxes', { cycle: cycleNumber }, onRetry)
}

/* OHLCV data for the trading chart */
export async function fetchOhlcvData(onRetry) {
  return apiFetch('/api/ohlcv', {}, onRetry)
}

/* Sidebar cycle list for Bear/Bull navigation */
export async function fetchCycleMenu(onRetry) {
  return apiFetch('/api/cycle-menu', {}, onRetry)
}

/* SummaryCard — 현재 사이클 요약 데이터 */
export async function fetchSummaryData(cycleNumber = 4, onRetry) {
  return apiFetch('/api/bear-boxes', { cycle: cycleNumber }, onRetry)
}

