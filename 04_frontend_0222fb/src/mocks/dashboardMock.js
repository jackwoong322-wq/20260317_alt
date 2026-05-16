/**
 * dashboardMock.js
 * API 연동 실패 또는 로컬 개발 환경 격리 시 사용하는 목 데이터
 * 실제 운용 시에는 백엔드 API 응답으로 대체된다.
 */

/** @typedef {'BUY' | 'HOLD' | 'SELL'} Signal */

/**
 * @typedef {Object} DashboardSummary
 * @property {number} cycleNumber       - 현재 사이클 차수 (예: 4)
 * @property {number} currentPrice      - 현재 BTC 가격 (USD)
 * @property {number} highPrice         - 사이클 고점 (USD)
 * @property {number} lowPrice          - 사이클 저점 (USD)
 * @property {number} positionPercent   - 고점 대비 현재가 위치 (%, 0~100)
 * @property {Signal} signal            - 매수/보유/매도 신호
 * @property {number} nextPredictedPrice - 다음 예측 가격 (USD)
 * @property {string} updatedAt         - 데이터 갱신 시각 (ISO 8601)
 */

/** @type {DashboardSummary} */
export const MOCK_DASHBOARD_SUMMARY = {
  cycleNumber: 4,
  currentPrice: 67_240.5,
  highPrice: 73_794.0,
  lowPrice: 15_460.0,
  positionPercent: 88.9,  // (currentPrice - lowPrice) / (highPrice - lowPrice) * 100
  signal: 'HOLD',
  nextPredictedPrice: 71_500.0,
  updatedAt: new Date().toISOString(),
}

/**
 * fetchDashboardSummary
 * 실제 API 연동 시 이 함수를 lib/api.js 의 실제 fetch 함수로 대체한다.
 * @returns {Promise<DashboardSummary>}
 */
export async function fetchDashboardSummary() {
  // 200ms 지연으로 API 호출 시뮬레이션
  await new Promise((resolve) => setTimeout(resolve, 200))
  return MOCK_DASHBOARD_SUMMARY
}
