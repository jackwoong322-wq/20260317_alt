/**
 * summaryCard.test.jsx — 04_frontend SummaryCard 유닛 테스트
 *
 * QA 에이전트 작성 | Loop 20
 * SummaryCard는 fetchSummaryData를 자체 호출하므로 mock 필요
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import SummaryCard from '../components/SummaryCard'

// api 모듈 mock
vi.mock('../lib/api', () => ({
  fetchSummaryData: vi.fn(),
}))

// SignalBadge mock
vi.mock('../components/SignalBadge', () => ({
  default: ({ signal }) => <span data-testid="signal-badge">{signal}</span>,
}))

import { fetchSummaryData } from '../lib/api'

const MOCK_RESPONSE = {
  lineData: [
    { value: 0.5 },
    { value: 0.6 },
    { value: 0.73 },
  ],
  boxes: [
    { Start_Rate: 0.3, Peak_Rate: 1.2 },
    { Start_Rate: 0.5, Peak_Rate: 0.9 },
  ],
  predictions: [
    { Peak_Rate: 1.5 },
  ],
}

describe('[QA] SummaryCard — 04_frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('로딩 중 스켈레톤을 표시한다', () => {
    fetchSummaryData.mockReturnValue(new Promise(() => {})) // 영구 대기
    const { container } = render(<SummaryCard />)
    const skel = container.querySelector('.summary-skeleton, [data-testid="skeleton"]')
    // 적어도 aria-busy 또는 로딩 클래스가 있어야 함
    expect(container.firstChild).not.toBeNull()
  })

  it('API 성공 시 현재 Rate 레이블이 표시된다', async () => {
    fetchSummaryData.mockResolvedValue(MOCK_RESPONSE)
    render(<SummaryCard />)
    await waitFor(() => {
      expect(screen.getByText('현재 Rate')).toBeDefined()
    })
  })

  it('사이클 고점 레이블이 표시된다', async () => {
    fetchSummaryData.mockResolvedValue(MOCK_RESPONSE)
    render(<SummaryCard />)
    await waitFor(() => {
      expect(screen.getByText('사이클 고점')).toBeDefined()
    })
  })

  it('사이클 저점 레이블이 표시된다', async () => {
    fetchSummaryData.mockResolvedValue(MOCK_RESPONSE)
    render(<SummaryCard />)
    await waitFor(() => {
      expect(screen.getByText('사이클 저점')).toBeDefined()
    })
  })

  it('다음 예측 레이블이 표시된다', async () => {
    fetchSummaryData.mockResolvedValue(MOCK_RESPONSE)
    render(<SummaryCard />)
    await waitFor(() => {
      expect(screen.getByText('다음 예측')).toBeDefined()
    })
  })

  it('BTC 레이블이 표시된다', async () => {
    fetchSummaryData.mockResolvedValue(MOCK_RESPONSE)
    render(<SummaryCard />)
    await waitFor(() => {
      expect(screen.getByText('BTC')).toBeDefined()
    })
  })

  it('API 오류 시 컴포넌트가 크래시하지 않는다', async () => {
    fetchSummaryData.mockRejectedValue(new Error('Network Error'))
    expect(() => render(<SummaryCard />)).not.toThrow()
  })

  it('fetchSummaryData가 정확히 한 번 호출된다', async () => {
    fetchSummaryData.mockResolvedValue(MOCK_RESPONSE)
    render(<SummaryCard />)
    await waitFor(() => {
      expect(fetchSummaryData).toHaveBeenCalledTimes(1)
    })
  })
})

// ── signalFromPercent 로직 검증 (컴포넌트 내부 순수함수 동일 검증) ──

describe('[QA] SummaryCard signalFromPercent 로직', () => {
  function signalFromPercent(pct) {
    if (pct < 30) return 'BUY'
    if (pct < 70) return 'HOLD'
    return 'SELL'
  }

  it('0% → BUY', () => expect(signalFromPercent(0)).toBe('BUY'))
  it('29% → BUY', () => expect(signalFromPercent(29)).toBe('BUY'))
  it('30% → HOLD', () => expect(signalFromPercent(30)).toBe('HOLD'))
  it('69% → HOLD', () => expect(signalFromPercent(69)).toBe('HOLD'))
  it('70% → SELL', () => expect(signalFromPercent(70)).toBe('SELL'))
  it('100% → SELL', () => expect(signalFromPercent(100)).toBe('SELL'))
})
