/**
 * chartTooltip.test.jsx — ChartTooltip 컴포넌트 + useChartTooltip 훅 유닛 테스트
 *
 * QA 에이전트 작성 | 커버리지 목표: 80%+
 * Vitest + @testing-library/react
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChartTooltip from '../components/ChartTooltip'

// ── ChartTooltip 렌더링 테스트 ────────────────────────────────────────

describe('[QA] ChartTooltip — 렌더링', () => {
  it('tooltipState가 null이면 DOM은 유지되지만 visibility:hidden으로 숨겨진다 (BUG-05)', () => {
    const { container } = render(<ChartTooltip tooltipState={null} />)
    const el = container.querySelector('.chart-tooltip')
    // BUG-05: aria-live 호환을 위해 DOM 유지, visibility로 숨김
    expect(el).not.toBeNull()
    expect(el.style.visibility).toBe('hidden')
    expect(el.getAttribute('aria-hidden')).toBe('true')
  })

  it('tooltipState가 있으면 날짜 레이블을 표시한다', () => {
    const state = {
      x: 100,
      y: 50,
      dayLabel: 'Day 42',
      items: [
        { name: 'Cycle 2021', color: '#d8a544', value: '-45.20%', diff: '+1.2pp' },
      ],
    }
    render(<ChartTooltip tooltipState={state} />)
    expect(screen.getByText('Day 42')).toBeDefined()
  })

  it('tooltipState가 있으면 시리즈명을 표시한다', () => {
    const state = {
      x: 100,
      y: 50,
      dayLabel: 'Day 10',
      items: [
        { name: 'Current Cycle (2025)', color: '#90c5a4', value: '-10.50%', diff: null },
      ],
    }
    render(<ChartTooltip tooltipState={state} />)
    expect(screen.getByText('Current Cycle (2025)')).toBeDefined()
  })

  it('툴팁이 x, y 위치에 배치된다', () => {
    const state = {
      x: 200,
      y: 80,
      dayLabel: 'Day 5',
      items: [{ name: 'Test', color: '#fff', value: '0.00%', diff: null }],
    }
    const { container } = render(<ChartTooltip tooltipState={state} />)
    const tooltip = container.querySelector('.chart-tooltip')
    expect(tooltip).not.toBeNull()
    expect(tooltip.style.left).toBe('200px')
    expect(tooltip.style.top).toBe('80px')
  })

  it('상승 등락은 --up 클래스가 적용된다', () => {
    const state = {
      x: 50,
      y: 50,
      dayLabel: 'Day 1',
      items: [{ name: 'X', color: '#aaa', value: '5.00%', diff: '+2.3pp' }],
    }
    const { container } = render(<ChartTooltip tooltipState={state} />)
    const diffEl = container.querySelector('.chart-tooltip__diff--up')
    expect(diffEl).not.toBeNull()
    expect(diffEl.textContent).toBe('+2.3pp')
  })

  it('하락 등락은 --down 클래스가 적용된다', () => {
    const state = {
      x: 50,
      y: 50,
      dayLabel: 'Day 2',
      items: [{ name: 'Y', color: '#bbb', value: '-3.00%', diff: '-1.5pp' }],
    }
    const { container } = render(<ChartTooltip tooltipState={state} />)
    const diffEl = container.querySelector('.chart-tooltip__diff--down')
    expect(diffEl).not.toBeNull()
  })

  it('diff가 null이면 등락 요소를 렌더링하지 않는다', () => {
    const state = {
      x: 50,
      y: 50,
      dayLabel: 'Day 3',
      items: [{ name: 'Z', color: '#ccc', value: '1.00%', diff: null }],
    }
    const { container } = render(<ChartTooltip tooltipState={state} />)
    expect(container.querySelector('.chart-tooltip__diff')).toBeNull()
  })

  it('여러 시리즈를 모두 표시한다', () => {
    const state = {
      x: 60,
      y: 60,
      dayLabel: 'Day 100',
      items: [
        { name: 'Cycle A', color: '#111', value: '10.00%', diff: null },
        { name: 'Cycle B', color: '#222', value: '20.00%', diff: '+1pp' },
        { name: 'Cycle C', color: '#333', value: '30.00%', diff: null },
      ],
    }
    render(<ChartTooltip tooltipState={state} />)
    expect(screen.getByText('Cycle A')).toBeDefined()
    expect(screen.getByText('Cycle B')).toBeDefined()
    expect(screen.getByText('Cycle C')).toBeDefined()
  })

  it('role=tooltip 접근성 속성이 있다', () => {
    const state = {
      x: 10,
      y: 10,
      dayLabel: 'Day 0',
      items: [{ name: 'A', color: '#aaa', value: '0%', diff: null }],
    }
    render(<ChartTooltip tooltipState={state} />)
    expect(screen.getByRole('tooltip')).toBeDefined()
  })
})

// ── 아키텍처 규칙 검증 (정적 분석 수준) ────────────────────────────────

describe('[QA] 아키텍처 규칙 — 정적 검증', () => {
  it('ChartTooltip이 api.js를 직접 import하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../components/ChartTooltip.jsx')
    const content = fs.readFileSync(filePath, 'utf-8')
    expect(content).not.toContain("from '../lib/api'")
    expect(content).not.toContain('fetch(')
  })

  it('useChartTooltip이 API URL을 하드코딩하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../hooks/useChartTooltip.js')
    const content = fs.readFileSync(filePath, 'utf-8')
    expect(content).not.toContain('http://localhost')
    expect(content).not.toContain('VITE_API_URL')
    expect(content).not.toContain('fetch(')
  })

  it('dashboardMock.js가 API URL을 포함하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../mocks/dashboardMock.js')
    const content = fs.readFileSync(filePath, 'utf-8')
    expect(content).not.toContain('http://')
    expect(content).not.toContain('fetch(')
  })

  it('SummaryCard가 fetch()를 직접 호출하지 않는다 (GATE-2)', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const filePath = path.resolve(__dirname, '../components/SummaryCard.jsx')
    const content = fs.readFileSync(filePath, 'utf-8')
    // fetch( 패턴이 없어야 함
    const hasFetch = /await\s+fetch\s*\(/.test(content)
    expect(hasFetch).toBe(false)
  })
})
