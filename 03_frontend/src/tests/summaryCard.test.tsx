/**
 * summaryCard.test.tsx — 03_frontend SummaryCard 유닛 테스트
 *
 * QA 에이전트 작성 | Loop 10
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SummaryCard from '../components/SummaryCard'
import type { BearBoxesData } from '../components/SummaryCard'

const mockData: BearBoxesData = {
  lineData: [
    { value: 0.5 },
    { value: 0.6 },
    { value: 0.73 },  // 마지막 값 = currentRate
  ],
  boxes: [
    { Start_Rate: 0.3, Peak_Rate: 1.2 },
    { Start_Rate: 0.5, Peak_Rate: 0.9 },  // 마지막 박스 = hiRate/loRate
  ],
  predictions: [
    { Peak_Rate: 1.5 },  // nextPred
  ],
}

describe('[QA] SummaryCard — 렌더링', () => {
  it('data=null 시 스켈레톤을 표시한다', () => {
    const { container } = render(<SummaryCard data={null} />)
    const skel = container.querySelector('[aria-label="Loading summary..."]')
    expect(skel).not.toBeNull()
  })

  it('lineData=[] 시 스켈레톤을 표시한다', () => {
    const { container } = render(
      <SummaryCard data={{ lineData: [], boxes: [], predictions: [] }} />
    )
    const skel = container.querySelector('[aria-label="Loading summary..."]')
    expect(skel).not.toBeNull()
  })

  it('정상 데이터 시 BTC 레이블이 표시된다', () => {
    render(<SummaryCard data={mockData} />)
    expect(screen.getByText('BTC')).toBeDefined()
  })

  it('CURRENT CYCLE 레이블이 표시된다', () => {
    render(<SummaryCard data={mockData} />)
    expect(screen.getByText('CURRENT CYCLE (2025)')).toBeDefined()
  })

  it('CURRENT 통계 레이블이 표시된다', () => {
    render(<SummaryCard data={mockData} />)
    expect(screen.getByText('CURRENT')).toBeDefined()
  })

  it('SignalBadge가 렌더링된다 (레이블 텍스트 확인)', () => {
    render(<SummaryCard data={mockData} />)
    // SignalBadge는 'ACCUMULATE ZONE', 'HOLD / OBSERVE', 'DISTRIBUTION ZONE' 중 하나 표시
    const labels = ['ACCUMULATE ZONE', 'HOLD / OBSERVE', 'DISTRIBUTION ZONE']
    const found = labels.some((label) => {
      try {
        return screen.getByText(label) !== null
      } catch {
        return false
      }
    })
    expect(found).toBe(true)
  })

  it('aria-label="Cycle summary"가 있다', () => {
    render(<SummaryCard data={mockData} />)
    expect(screen.getByLabelText('Cycle summary')).toBeDefined()
  })
})

describe('[QA] SummaryCard — 계산 로직', () => {
  it('currentRate는 lineData 마지막 값', () => {
    // currentRate = 0.73x
    render(<SummaryCard data={mockData} />)
    expect(screen.getByText('0.73x')).toBeDefined()
  })

  it('NEXT PRED 레이블이 표시된다', () => {
    render(<SummaryCard data={mockData} />)
    expect(screen.getByText('NEXT PRED')).toBeDefined()
  })
})
