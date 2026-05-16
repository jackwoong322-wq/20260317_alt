/**
 * dashboardMock.test.js
 * mock 데이터 구조 및 fetchDashboardSummary 유닛 테스트
 */
import { describe, it, expect } from 'vitest'
import { MOCK_DASHBOARD_SUMMARY, fetchDashboardSummary } from '../mocks/dashboardMock'

describe('MOCK_DASHBOARD_SUMMARY', () => {
  it('cycleNumber가 양의 정수여야 한다', () => {
    expect(typeof MOCK_DASHBOARD_SUMMARY.cycleNumber).toBe('number')
    expect(MOCK_DASHBOARD_SUMMARY.cycleNumber).toBeGreaterThan(0)
  })

  it('currentPrice가 0보다 커야 한다', () => {
    expect(MOCK_DASHBOARD_SUMMARY.currentPrice).toBeGreaterThan(0)
  })

  it('highPrice >= currentPrice >= lowPrice 관계가 성립해야 한다', () => {
    const { highPrice, currentPrice, lowPrice } = MOCK_DASHBOARD_SUMMARY
    expect(highPrice).toBeGreaterThanOrEqual(currentPrice)
    expect(currentPrice).toBeGreaterThanOrEqual(lowPrice)
  })

  it('positionPercent가 0~100 범위여야 한다', () => {
    expect(MOCK_DASHBOARD_SUMMARY.positionPercent).toBeGreaterThanOrEqual(0)
    expect(MOCK_DASHBOARD_SUMMARY.positionPercent).toBeLessThanOrEqual(100)
  })

  it("signal이 'BUY' | 'HOLD' | 'SELL' 중 하나여야 한다", () => {
    expect(['BUY', 'HOLD', 'SELL']).toContain(MOCK_DASHBOARD_SUMMARY.signal)
  })

  it('nextPredictedPrice가 0보다 커야 한다', () => {
    expect(MOCK_DASHBOARD_SUMMARY.nextPredictedPrice).toBeGreaterThan(0)
  })

  it('updatedAt이 ISO 8601 형식의 문자열이어야 한다', () => {
    expect(typeof MOCK_DASHBOARD_SUMMARY.updatedAt).toBe('string')
    expect(() => new Date(MOCK_DASHBOARD_SUMMARY.updatedAt)).not.toThrow()
    expect(new Date(MOCK_DASHBOARD_SUMMARY.updatedAt).toISOString()).toBe(
      MOCK_DASHBOARD_SUMMARY.updatedAt
    )
  })
})

describe('fetchDashboardSummary', () => {
  it('Promise를 반환하며 MOCK_DASHBOARD_SUMMARY와 동일한 데이터를 resolve한다', async () => {
    const result = await fetchDashboardSummary()
    expect(result).toEqual(MOCK_DASHBOARD_SUMMARY)
  })

  it('약 200ms 지연 후 resolve된다', async () => {
    const start = Date.now()
    await fetchDashboardSummary()
    const elapsed = Date.now() - start
    // 200ms 지연 ± 100ms 허용 오차
    expect(elapsed).toBeGreaterThanOrEqual(150)
    expect(elapsed).toBeLessThan(500)
  })
})
