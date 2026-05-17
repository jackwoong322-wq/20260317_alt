/**
 * dashboardMock.js — 백엔드 미연결 시 목 데이터
 *
 * 사용 조건: import.meta.env.DEV === true 환경에서만 활성화
 * 프로덕션 빌드에서는 트리-쉐이킹으로 제외됨 (DEV 조건부 import)
 *
 * 아키텍처 규칙 준수:
 *   - API URL 하드코딩 없음
 *   - 컴포넌트 직접 참조 없음
 *   - useChartData.js 훅을 통해서만 접근
 */

// ── SummaryCard 목 데이터 (기존 dashboardMock.test.js 인터페이스 유지) ──
export const MOCK_DASHBOARD_SUMMARY = {
  cycleNumber: 4,
  currentPrice: 67241,
  highPrice: 108400,
  lowPrice: 15460,
  positionPercent: 88.9,
  signal: 'SELL',
  nextPredictedPrice: 71500,
  updatedAt: new Date(Date.UTC(2025, 9, 6)).toISOString(),
}

/**
 * fetchDashboardSummary — 200ms 지연 후 목 데이터 반환
 * 테스트 및 DEV 환경에서 API 대체 사용
 */
export async function fetchDashboardSummary() {
  await new Promise((resolve) => setTimeout(resolve, 200))
  return MOCK_DASHBOARD_SUMMARY
}

// ── 사이클 비교 목 데이터 ────────────────────────────────────────────
export const mockCycleComparison = {
  series: [
    {
      name: 'Cycle 2013',
      startDate: '2013-11-29',
      minRate: -85.7,
      dayCount: 414,
      data: Array.from({ length: 414 }, (_, i) => ({
        day: i,
        rate: -85.7 * Math.sin((Math.PI * i) / 207) * (i / 414),
      })),
    },
    {
      name: 'Cycle 2017',
      startDate: '2017-12-17',
      minRate: -83.5,
      dayCount: 364,
      data: Array.from({ length: 364 }, (_, i) => ({
        day: i,
        rate: -83.5 * Math.sin((Math.PI * i) / 182) * (i / 364),
      })),
    },
    {
      name: 'Cycle 2021',
      startDate: '2021-11-10',
      minRate: -77.2,
      dayCount: 376,
      data: Array.from({ length: 376 }, (_, i) => ({
        day: i,
        rate: -77.2 * Math.sin((Math.PI * i) / 188) * (i / 376),
      })),
    },
    {
      name: 'Current Cycle (2025)',
      startDate: '2025-10-06',
      minRate: -50.5,
      dayCount: 221,
      data: Array.from({ length: 221 }, (_, i) => ({
        day: i,
        rate: -50.5 * Math.sin((Math.PI * i) / 110) * (i / 221),
      })),
    },
  ],
}

// ── Bear Box 목 데이터 팩토리 ────────────────────────────────────────
export function mockBearBoxData(cycleNumber = 4) {
  const configs = {
    1: { peak: 1163, bottom: 170, days: 414, label: 'Cycle 1 (2013)' },
    2: { peak: 19666, bottom: 3191, days: 364, label: 'Cycle 2 (2017)' },
    3: { peak: 69000, bottom: 15460, days: 376, label: 'Cycle 3 (2021)' },
    4: { peak: 108400, bottom: 73794, days: 221, label: 'Cycle 4 (2025)' },
  }
  const cfg = configs[cycleNumber] || configs[4]

  return {
    cycleInfo: {
      cycleNumber,
      label: cfg.label,
      peakPrice: cfg.peak,
      bottomPrice: cfg.bottom,
      totalDays: cfg.days,
      currentDay: Math.min(cfg.days, 221),
    },
    lineData: Array.from({ length: cfg.days }, (_, i) => ({
      day: i,
      price: cfg.peak * Math.exp((-Math.log(cfg.peak / cfg.bottom) * i) / cfg.days),
    })),
    boxes: [
      { id: 1, hi: cfg.peak * 0.95, lo: cfg.peak * 0.80, label: 'H1' },
      { id: 2, hi: cfg.peak * 0.78, lo: cfg.peak * 0.62, label: 'H2' },
      { id: 3, hi: cfg.peak * 0.60, lo: cfg.peak * 0.45, label: 'H3' },
    ],
    maxDays: cfg.days,
    config: {
      peakPrice: cfg.peak,
      bottomPrice: cfg.bottom,
    },
  }
}

// ── Bull Box 목 데이터 팩토리 ────────────────────────────────────────
export function mockBullBoxData(cycleNumber = 3) {
  const configs = {
    1: { base: 170, peak: 1163, days: 300 },
    2: { base: 3191, peak: 19666, days: 360 },
    3: { base: 15460, peak: 69000, days: 400 },
  }
  const cfg = configs[cycleNumber] || configs[3]

  return {
    cycleInfo: {
      cycleNumber,
      label: `Bull Cycle ${cycleNumber}`,
      peakPrice: cfg.peak,
      bottomPrice: cfg.base,
    },
    lineData: Array.from({ length: cfg.days }, (_, i) => ({
      day: i,
      price: cfg.base * Math.exp((Math.log(cfg.peak / cfg.base) * i) / cfg.days),
    })),
    boxes: [
      { id: 1, hi: cfg.base * 1.5, lo: cfg.base * 1.2, label: 'L1' },
      { id: 2, hi: cfg.base * 2.5, lo: cfg.base * 1.8, label: 'L2' },
    ],
    maxDays: cfg.days,
    config: { peakPrice: cfg.peak, bottomPrice: cfg.base },
  }
}
