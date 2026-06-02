/*
 * Backend API client
 *
 * The frontend reads all chart data through the backend API rather than
 * talking directly to Supabase from the browser.
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
 * API base URL rules
 * - 로컬 개발 시(localhost/127.0.0.1) 로컬 백엔드 기본값(http://localhost:8000) 강제 사용
 * - 그 외 환경은 VITE_API_URL 환경변수를 사용하고 없으면 기본값 사용
 */
function resolveApiBaseUrl() {
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return 'http://localhost:8000'
  }
  return import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
}

let API_BASE_URL = resolveApiBaseUrl()

async function apiFetch(path, params = {}) {
  const url = new URL(`${API_BASE_URL}${path}`)
  Object.entries(params).forEach(([key, val]) => {
    if (val !== null && val !== undefined) {
      url.searchParams.set(key, val)
    }
  })

  const response = await fetch(url.toString())

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const msg = formatApiDetail(errorData.detail) || `API error: ${response.status}`
    throw new Error(msg)
  }

  return response.json()
}

/* Dashboard summary card data */
export async function fetchDashboardSummary() {
  return apiFetch('/api/dashboard-summary')
}

/* Cycle comparison chart data */
export async function fetchCycleComparison() {
  return apiFetch('/api/cycle-comparison')
}

/* Bear box data and predictions */
export async function fetchBearBoxes(cycleNumber = 4) {
  return apiFetch('/api/bear-boxes', { cycle: cycleNumber })
}

/* Bull box data */
export async function fetchBullBoxes(cycleNumber = 3) {
  return apiFetch('/api/bull-boxes', { cycle: cycleNumber })
}

/* OHLCV data for the trading chart */
export async function fetchOhlcvData() {
  return apiFetch('/api/ohlcv')
}

/* Sidebar cycle list for Bear/Bull navigation */
export async function fetchCycleMenu() {
  return apiFetch('/api/cycle-menu')
}

/* BTC 투자 신호 — ACCUMULATE/WATCH/CAUTION/EXIT */
export async function fetchBtcSignal() {
  return apiFetch('/api/btc-signal')
}
