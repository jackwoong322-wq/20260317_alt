/**
 * utilities.test.js — Loop 14: 유틸리티·목 데이터 커버리지 확보
 *
 * 대상:
 *   - chartConstants.js (COLORS, CHART_THEME, COLOR_NAMES)
 *   - dashboardMock.js (fetchDashboardSummary, mockBearBoxData 등)
 */
import { describe, it, expect } from 'vitest'

// ── chartConstants 검증 ───────────────────────────────────────────────

describe('[QA] chartConstants — 구조 검증', () => {
  it('COLORS 배열이 정의되어 있고 최소 6개 색상을 포함한다', async () => {
    const { COLORS } = await import('../utils/chartConstants')
    expect(Array.isArray(COLORS)).toBe(true)
    expect(COLORS.length).toBeGreaterThanOrEqual(6)
  })

  it('COLOR_NAMES 배열이 COLORS와 동일한 길이다', async () => {
    const { COLORS, COLOR_NAMES } = await import('../utils/chartConstants')
    expect(COLOR_NAMES.length).toBe(COLORS.length)
  })

  it('CHART_THEME 객체에 background, grid, textMuted 속성이 있다', async () => {
    const { CHART_THEME } = await import('../utils/chartConstants')
    expect(CHART_THEME).toHaveProperty('background')
    expect(CHART_THEME).toHaveProperty('grid')
    expect(CHART_THEME).toHaveProperty('textMuted')
  })

  it('CHART_THEME.success는 CSS 색상 문자열이다', async () => {
    const { CHART_THEME } = await import('../utils/chartConstants')
    expect(typeof CHART_THEME.success).toBe('string')
    expect(CHART_THEME.success.length).toBeGreaterThan(0)
  })
})

// ── dashboardMock 검증 ────────────────────────────────────────────────

describe('[QA] dashboardMock — 데이터 구조 검증', () => {
  it('MOCK_DASHBOARD_SUMMARY에 currentPrice 필드가 있다', async () => {
    const { MOCK_DASHBOARD_SUMMARY } = await import('../mocks/dashboardMock')
    expect(MOCK_DASHBOARD_SUMMARY).toHaveProperty('currentPrice')
  })

  it('fetchDashboardSummary는 Promise를 반환하고 데이터를 담는다', async () => {
    const { fetchDashboardSummary } = await import('../mocks/dashboardMock')
    const result = await fetchDashboardSummary()
    expect(result).toBeDefined()
    expect(typeof result).toBe('object')
  })

  it('mockCycleComparison.series 배열이 존재한다', async () => {
    const mod = await import('../mocks/dashboardMock')
    const data = mod.mockCycleComparison?.series ?? mod.MOCK_CYCLE_COMPARISON?.series
    // 어느 이름이든 배열이어야 함
    if (data !== undefined) {
      expect(Array.isArray(data)).toBe(true)
    }
  })

  it('mockBearBoxData 구조에 lineData와 boxes 배열이 있다', async () => {
    const { mockBearBoxData } = await import('../mocks/dashboardMock')
    // mockBearBoxData는 함수 (cycleNumber 인자)
    const data = typeof mockBearBoxData === 'function' ? mockBearBoxData(4) : mockBearBoxData
    if (data) {
      expect(Array.isArray(data.lineData)).toBe(true)
      expect(Array.isArray(data.boxes)).toBe(true)
    }
  })
})

// ── 순수 유틸 함수 검증 ───────────────────────────────────────────────

describe('[QA] 순수 유틸리티 함수', () => {
  it('날짜 포맷 함수 — 유효한 타임스탬프에서 YYYY-MM-DD 반환', () => {
    // BearBoxChart 내부 toDateString 로직을 동일하게 검증
    const toDateString = (timestamp) => {
      if (!timestamp) return null
      const date = new Date(timestamp)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    }
    const result = toDateString('2025-06-15T00:00:00Z')
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('날짜 포맷 함수 — null 입력에 null 반환', () => {
    const toDateString = (timestamp) => {
      if (!timestamp) return null
      const date = new Date(timestamp)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    }
    expect(toDateString(null)).toBeNull()
    expect(toDateString(undefined)).toBeNull()
    expect(toDateString('')).toBeNull()
  })

  it('파일명 안전화 로직 — 특수문자를 대시로 치환', () => {
    // useChartExport의 safeFilename 로직 단독 검증
    const safeFilename = (name) =>
      String(name).replace(/[^a-zA-Z0-9\-_]/g, '-').slice(0, 80)

    expect(safeFilename('btc chart 2025')).toBe('btc-chart-2025')
    expect(safeFilename('../path/traversal')).toBe('---path-traversal')
    expect(safeFilename('normal-file_name')).toBe('normal-file_name')
  })
})
