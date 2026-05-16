/**
 * issue102_chart_clip.test.jsx
 * 이슈 #102: BearBoxChart / BullBoxChart 하단 클리핑 수정 검증
 */
import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import fs from 'fs'
import path from 'path'

// ── Mocks ─────────────────────────────────────────────

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addLineSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    addBaselineSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => ({ fitContent: vi.fn(), applyOptions: vi.fn() })),
    resize: vi.fn(),
    remove: vi.fn(),
  })),
  LineStyle: { Solid: 0, Dotted: 1, Dashed: 2 },
  CrosshairMode: { Normal: 0 },
  ColorType: { Solid: 'solid' },
}))

vi.mock('../hooks/useChartData', () => ({
  useBearBoxData: vi.fn(() => ({
    lineData: [], boxes: [], predictions: [],
    loading: false, error: null, retryInfo: null,
    cycleInfo: { startDate: '', endDate: '', maxDays: 0 }, config: {},
  })),
  useBullBoxData: vi.fn(() => ({
    lineData: [], boxes: [],
    loading: false, error: null, retryInfo: null,
    cycleInfo: { startDate: '', endDate: '', maxDays: 0 }, config: {},
  })),
}))

vi.mock('../hooks/useResizeChart', () => ({ useResizeChart: vi.fn() }))

import BearBoxChart from '../components/BearBoxChart'
import BullBoxChart from '../components/BullBoxChart'

// ── CSS 파일 직접 검증 ────────────────────────────────

const cssPath = path.resolve(__dirname, '../styles/Chart.css')
const cssContent = fs.readFileSync(cssPath, 'utf-8')

const appCssPath = path.resolve(__dirname, '../styles/App.css')
const appCssContent = fs.readFileSync(appCssPath, 'utf-8')

// ── App.css 레이아웃 체인 검증 ─────────────────────────

describe('[#102] App.css — chart-fullscreen 레이아웃', () => {
  it('App.css 파일이 존재해야 한다', () => {
    expect(fs.existsSync(appCssPath)).toBe(true)
  })

  it('.chart-fullscreen이 display:flex를 가져야 한다', () => {
    const blockMatch = appCssContent.match(/\.chart-fullscreen\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toContain('display: flex')
  })

  it('.chart-fullscreen이 flex-direction:column을 가져야 한다', () => {
    const blockMatch = appCssContent.match(/\.chart-fullscreen\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toContain('flex-direction: column')
  })

  it('.chart-fullscreen이 overflow:hidden을 가져야 한다', () => {
    const blockMatch = appCssContent.match(/\.chart-fullscreen\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toContain('overflow: hidden')
  })

  it('.chart-shell에 min-height:100%가 없어야 한다 (overflow 유발)', () => {
    const blockMatch = appCssContent.match(/\.chart-shell\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).not.toContain('min-height: 100%')
  })

  it('.chart-shell이 flex:1을 가져야 한다', () => {
    const blockMatch = appCssContent.match(/\.chart-shell\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toContain('flex: 1')
  })
})

describe('[#102] Chart.css — chart-area-compact 높이', () => {
  it('.chart-area-compact의 min-height가 400px 이하여야 한다 (과도한 높이 방지)', () => {
    const blockMatch = cssContent.match(/\.chart-area-compact\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    const minHeightMatch = block.match(/min-height:\s*(\d+)px/)
    const value = minHeightMatch ? parseInt(minHeightMatch[1]) : 9999
    expect(value).toBeLessThanOrEqual(400)
  })

  it('.chart-page에 height:100%가 없어야 한다 (flex 환경)', () => {
    const blockMatch = cssContent.match(/\.chart-page\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).not.toContain('height: 100%')
  })

  it('.chart-page에 flex:1이 있어야 한다', () => {
    const blockMatch = cssContent.match(/\.chart-page\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toContain('flex: 1')
  })
})

describe('[#102] Chart.css — chart-overlay-wrapper', () => {
  it('CSS 파일이 존재해야 한다', () => {
    expect(fs.existsSync(cssPath)).toBe(true)
  })

  it('.chart-overlay-wrapper가 정의되어 있어야 한다', () => {
    expect(cssContent).toContain('.chart-overlay-wrapper')
  })

  it('.chart-overlay-wrapper에 overflow: hidden이 없어야 한다 (클리핑 버그)', () => {
    const blockMatch = cssContent.match(/\.chart-overlay-wrapper\s*\{([^}]+)\}/)
    expect(blockMatch).not.toBeNull()
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).not.toContain('overflow: hidden')
  })

  it('.chart-overlay-wrapper에 overflow: visible이 설정되어야 한다', () => {
    const blockMatch = cssContent.match(/\.chart-overlay-wrapper\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toContain('overflow: visible')
  })
})

describe('[#102] Chart.css — chart-area-fill', () => {
  it('.chart-area-fill이 정의되어 있어야 한다', () => {
    expect(cssContent).toContain('.chart-area-fill')
  })

  it('.chart-area-fill에 min-height: 0이 없어야 한다', () => {
    const blockMatch = cssContent.match(/\.chart-area-fill\s*\{([^}]+)\}/)
    expect(blockMatch).not.toBeNull()
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).not.toContain('min-height: 0')
  })

  it('.chart-area-fill에 min-height가 양수로 설정되어야 한다', () => {
    const blockMatch = cssContent.match(/\.chart-area-fill\s*\{([^}]+)\}/)
    const block = blockMatch ? blockMatch[1] : ''
    expect(block).toMatch(/min-height:\s*[1-9]/)
  })
})

// ── BearBoxChart 컴포넌트 렌더링 검증 ─────────────────

describe('[#102] BearBoxChart 렌더링', () => {
  it('cycleNumber=4 (기본값)으로 렌더링되어야 한다', () => {
    const { container } = render(<BearBoxChart cycleNumber={4} />)
    expect(container).toBeTruthy()
  })

  it('loading=true 상태에서 렌더링이 실패하지 않아야 한다', async () => {
    const { useBearBoxData } = await import('../hooks/useChartData')
    vi.mocked(useBearBoxData).mockReturnValueOnce({
      lineData: [], boxes: [], predictions: [],
      loading: true, error: null, retryInfo: null,
    })
    const { container } = render(<BearBoxChart cycleNumber={1} />)
    expect(container).toBeTruthy()
  })

  it('error 상태에서 렌더링이 실패하지 않아야 한다', async () => {
    const { useBearBoxData } = await import('../hooks/useChartData')
    vi.mocked(useBearBoxData).mockReturnValueOnce({
      lineData: [], boxes: [], predictions: [],
      loading: false, error: 'Network error', retryInfo: null,
    })
    const { container } = render(<BearBoxChart cycleNumber={1} />)
    expect(container).toBeTruthy()
  })

  it('Cycle 1 ~ 4 모두 렌더링이 실패하지 않아야 한다', () => {
    [1, 2, 3, 4].forEach((cycle) => {
      expect(() => render(<BearBoxChart cycleNumber={cycle} />)).not.toThrow()
    })
  })

  it('.chart-overlay-wrapper 클래스가 소스에 있어야 한다', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../components/BearBoxChart.jsx'), 'utf-8'
    )
    expect(src).toContain('chart-overlay-wrapper')
  })
})

// ── BullBoxChart 컴포넌트 검증 ────────────────────────

describe('[#102] BullBoxChart 렌더링', () => {
  it('기본값으로 렌더링되어야 한다', () => {
    expect(() => render(<BullBoxChart />)).not.toThrow()
  })

  it('Cycle 1 ~ 4 모두 렌더링이 실패하지 않아야 한다', () => {
    [1, 2, 3, 4].forEach((cycle) => {
      expect(() => render(<BullBoxChart cycleNumber={cycle} />)).not.toThrow()
    })
  })

  it('.chart-area-fill 클래스를 사용해야 한다', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../components/BullBoxChart.jsx'), 'utf-8'
    )
    expect(src).toContain('chart-area-fill')
  })

  it('.chart-overlay-wrapper를 사용하지 않아야 한다 (BullBox 클리핑 무관)', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../components/BullBoxChart.jsx'), 'utf-8'
    )
    expect(src).not.toContain('chart-overlay-wrapper')
  })
})
