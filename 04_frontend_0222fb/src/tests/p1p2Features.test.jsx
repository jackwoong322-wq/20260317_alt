/**
 * p1p2Features.test.jsx — P1·P2 신규 기능 유닛 테스트
 *
 * QA 에이전트 작성
 * F-05(테마), F-06(스켈레톤), F-07(애니메이션CSS), F-08(내보내기), TECH-01
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'

// ── F-05: useTheme 훅 ─────────────────────────────────────────────────

describe('[QA] F-05 useTheme', () => {
  let originalGetItem, originalSetItem, originalMatchMedia

  beforeEach(() => {
    // localStorage mock
    originalGetItem = Storage.prototype.getItem
    originalSetItem = Storage.prototype.setItem
    Storage.prototype.getItem = vi.fn(() => null)
    Storage.prototype.setItem = vi.fn()

    // matchMedia mock
    originalMatchMedia = window.matchMedia
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
  })

  afterEach(() => {
    Storage.prototype.getItem = originalGetItem
    Storage.prototype.setItem = originalSetItem
    window.matchMedia = originalMatchMedia
    document.documentElement.removeAttribute('data-theme')
  })

  it('초기 테마는 dark이다 (시스템이 light가 아닐 때)', async () => {
    const { useTheme } = await import('../hooks/useTheme')
    let theme
    const TestComp = () => {
      const result = useTheme()
      theme = result.theme
      return null
    }
    render(<TestComp />)
    expect(theme).toBe('dark')
  })

  it('toggleTheme 호출 시 dark → light 로 전환된다', async () => {
    const { useTheme } = await import('../hooks/useTheme')
    let toggleFn
    const TestComp = () => {
      const { theme, toggleTheme } = useTheme()
      toggleFn = toggleTheme
      return <div data-testid="theme">{theme}</div>
    }
    render(<TestComp />)
    expect(screen.getByTestId('theme').textContent).toBe('dark')

    act(() => toggleFn())
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })

  it('localStorage에 테마가 저장된다', async () => {
    const { useTheme } = await import('../hooks/useTheme')
    let toggleFn
    const TestComp = () => {
      const { toggleTheme } = useTheme()
      toggleFn = toggleTheme
      return null
    }
    render(<TestComp />)
    act(() => toggleFn())
    expect(Storage.prototype.setItem).toHaveBeenCalledWith('btc-dashboard-theme', 'light')
  })
})

// ── F-06: ChartSkeleton ───────────────────────────────────────────────

describe('[QA] F-06 ChartSkeleton', () => {
  it('line 타입으로 렌더링되면 SVG가 존재한다', async () => {
    const { default: ChartSkeleton } = await import('../components/ChartSkeleton')
    const { container } = render(<ChartSkeleton type="line" />)
    expect(container.querySelector('svg')).not.toBeNull()
  })

  it('bar 타입으로 렌더링되면 bands 클래스가 존재한다', async () => {
    const { default: ChartSkeleton } = await import('../components/ChartSkeleton')
    const { container } = render(<ChartSkeleton type="bar" />)
    expect(container.querySelector('.chart-skeleton__bands')).not.toBeNull()
  })

  it('role=status 접근성 속성이 있다', async () => {
    const { default: ChartSkeleton } = await import('../components/ChartSkeleton')
    render(<ChartSkeleton />)
    expect(screen.getByRole('status')).toBeDefined()
  })

  it('sr-only 텍스트가 존재한다', async () => {
    const { default: ChartSkeleton } = await import('../components/ChartSkeleton')
    render(<ChartSkeleton />)
    const srOnly = document.querySelector('.sr-only')
    expect(srOnly).not.toBeNull()
    expect(srOnly.textContent.length).toBeGreaterThan(0)
  })
})

// ── F-08: useChartExport 아키텍처 검증 ───────────────────────────────

describe('[QA] F-08 useChartExport — 정적 검증', () => {
  it('useChartExport가 fetch()를 포함하지 않는다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const content = fs.readFileSync(
      path.resolve(__dirname, '../hooks/useChartExport.js'),
      'utf-8'
    )
    expect(content).not.toContain('fetch(')
    expect(content).not.toContain('http://')
  })

  it('takeScreenshot() API를 사용한다', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const content = fs.readFileSync(
      path.resolve(__dirname, '../hooks/useChartExport.js'),
      'utf-8'
    )
    expect(content).toContain('takeScreenshot')
  })

  it('내보내기 훅이 exporting 상태를 반환한다', async () => {
    const { useChartExport } = await import('../hooks/useChartExport')
    const chartRef = { current: null }
    let result
    const TestComp = () => {
      result = useChartExport(chartRef)
      return null
    }
    render(<TestComp />)
    expect(typeof result.exportPng).toBe('function')
    expect(result.exporting).toBe(false)
  })
})

// ── TECH-01: BullBoxTooltip 구조 검증 ────────────────────────────────

describe('[QA] TECH-01 BearBoxTooltip (BullBox 재사용) 렌더링', () => {
  it('Bull 박스 툴팁이 currentValue를 표시한다', async () => {
    const { default: BearBoxTooltip } = await import('../components/BearBoxTooltip')
    const state = {
      x: 50,
      y: 50,
      dateLabel: '2025.06.15',
      currentValue: '78.50%',
      nearestBox: null,
    }
    render(<BearBoxTooltip tooltipState={state} />)
    expect(screen.getByText('78.50%')).toBeDefined()
  })

  it('근접 박스 정보가 있으면 레이블이 표시된다', async () => {
    const { default: BearBoxTooltip } = await import('../components/BearBoxTooltip')
    const state = {
      x: 50,
      y: 50,
      dateLabel: '2025.06.15',
      currentValue: '80.00%',
      nearestBox: {
        label: 'H2',
        price: '82.50%',
        dist: '+2.50pp',
        isPrediction: false,
        endDate: null,
      },
    }
    render(<BearBoxTooltip tooltipState={state} />)
    expect(screen.getByText('H2')).toBeDefined()
    expect(screen.getByText('+2.50pp')).toBeDefined()
  })
})
