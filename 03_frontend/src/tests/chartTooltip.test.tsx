/**
 * chartTooltip.test.tsx — 03_frontend ChartTooltip 유닛 테스트 (TypeScript)
 *
 * QA 에이전트 작성 | Loop 9
 * 대상: src/components/ChartTooltip.tsx
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChartTooltip from '../components/ChartTooltip'
import type { TooltipState } from '../components/ChartTooltip'

const sampleState: TooltipState = {
  x: 100,
  y: 50,
  dayLabel: 'Day 42',
  items: [
    { name: 'Cycle 2021', color: '#d8a544', value: '-45.20%', diff: '+1.2pp' },
  ],
}

describe('[QA] ChartTooltip — 렌더링 (TypeScript)', () => {
  it('tooltipState가 null이면 DOM은 유지되나 aria-hidden=true', () => {
    const { container } = render(<ChartTooltip tooltipState={null} />)
    const el = container.firstChild as HTMLElement
    expect(el).not.toBeNull()
    expect(el.getAttribute('aria-hidden')).toBe('true')
  })

  it('tooltipState가 있으면 aria-hidden=false', () => {
    render(<ChartTooltip tooltipState={sampleState} />)
    const tooltip = screen.getByRole('tooltip')
    expect(tooltip.getAttribute('aria-hidden')).toBe('false')
  })

  it('날짜 레이블을 표시한다', () => {
    render(<ChartTooltip tooltipState={sampleState} />)
    expect(screen.getByText('Day 42')).toBeDefined()
  })

  it('시리즈명을 표시한다', () => {
    render(<ChartTooltip tooltipState={sampleState} />)
    expect(screen.getByText('Cycle 2021')).toBeDefined()
  })

  it('현재값을 표시한다', () => {
    render(<ChartTooltip tooltipState={sampleState} />)
    expect(screen.getByText('-45.20%')).toBeDefined()
  })

  it('양수 등락값을 표시한다', () => {
    render(<ChartTooltip tooltipState={sampleState} />)
    expect(screen.getByText('+1.2pp')).toBeDefined()
  })

  it('diff=null이면 등락값 없음', () => {
    const state: TooltipState = {
      ...sampleState,
      items: [{ name: 'X', color: '#aaa', value: '5%', diff: null }],
    }
    const { container } = render(<ChartTooltip tooltipState={state} />)
    // diff span이 없어야 함 (색상으로 구분하는 span 없음)
    const spans = container.querySelectorAll('span')
    const diffValues = Array.from(spans).filter(
      (s) => s.textContent?.match(/^[+-]\d/)
    )
    expect(diffValues.length).toBe(0)
  })

  it('여러 시리즈를 모두 표시한다', () => {
    const state: TooltipState = {
      x: 60,
      y: 60,
      dayLabel: 'Day 100',
      items: [
        { name: 'Cycle A', color: '#111', value: '10%', diff: null },
        { name: 'Cycle B', color: '#222', value: '20%', diff: '+1pp' },
        { name: 'Cycle C', color: '#333', value: '30%', diff: null },
      ],
    }
    render(<ChartTooltip tooltipState={state} />)
    expect(screen.getByText('Cycle A')).toBeDefined()
    expect(screen.getByText('Cycle B')).toBeDefined()
    expect(screen.getByText('Cycle C')).toBeDefined()
  })

  it('role=tooltip 접근성 속성이 있다', () => {
    render(<ChartTooltip tooltipState={sampleState} />)
    expect(screen.getByRole('tooltip')).toBeDefined()
  })
})

// ── 아키텍처 규칙 검증 ────────────────────────────────────────────────

describe('[QA] ChartTooltip 아키텍처 규칙 (TypeScript)', () => {
  it('ChartTooltip이 fetch()를 호출하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../components/ChartTooltip.tsx')
    const content = fs.readFileSync(filePath, 'utf-8')
    expect(content).not.toContain('fetch(')
  })

  it('ChartTooltip이 API URL을 하드코딩하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../components/ChartTooltip.tsx')
    const content = fs.readFileSync(filePath, 'utf-8')
    expect(content).not.toContain('http://')
    expect(content).not.toContain('VITE_API_URL')
  })

  it('any 타입을 사용하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../components/ChartTooltip.tsx')
    const content = fs.readFileSync(filePath, 'utf-8')
    // as any 패턴 금지
    expect(content).not.toContain(': any')
    expect(content).not.toContain('as any')
  })
})
