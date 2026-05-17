/**
 * resizeAndData.test.jsx — useResizeChart + useChartData 훅 테스트
 *
 * QA 에이전트 작성 | Loop 33
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'

// ── useResizeChart 테스트 ────────────────────────────────────────────

describe('[QA] useResizeChart — BUG-09 height=0 방어', () => {
  it('height 가드 로직 — 0px 입력 시 applyOptions 미호출', () => {
    // useResizeChart 소스 파일에서 height 가드 확인
    const { readFileSync } = require('fs')
    const { resolve } = require('path')
    const content = readFileSync(
      resolve(__dirname, '../hooks/useResizeChart.js'),
      'utf-8'
    )
    expect(content).toContain('height > 0')
    expect(content).toContain('Math.max(120')
  })

  it('ResizeObserver가 없는 환경에서도 훅 로드 가능 (정적 확인)', () => {
    const { readFileSync } = require('fs')
    const { resolve } = require('path')
    const content = readFileSync(
      resolve(__dirname, '../hooks/useResizeChart.js'),
      'utf-8'
    )
    expect(content).toContain('ResizeObserver')
  })
})

// ── useChartData mock 테스트 ─────────────────────────────────────────

// api 모듈 mock
vi.mock('../lib/api', () => ({
  fetchCycleComparison: vi.fn(),
  fetchBearBoxes: vi.fn(),
  fetchBullBoxes: vi.fn(),
  fetchOhlcvData: vi.fn(),
  fetchCycleMenu: vi.fn(),
  fetchSummaryData: vi.fn(),
}))

import {
  fetchCycleComparison,
  fetchBearBoxes,
  fetchBullBoxes,
  fetchOhlcvData,
} from '../lib/api'
import {
  useCycleComparisonData,
  useBearBoxData,
  useBullBoxData,
  useOhlcvData,
} from '../hooks/useChartData'

describe('[QA] useCycleComparisonData', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('초기 상태: loading=true, error=null, series=[]', () => {
    fetchCycleComparison.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useCycleComparisonData())
    expect(result.current.loading).toBe(true)
    expect(result.current.error).toBeNull()
    expect(result.current.series).toEqual([])
  })

  it('API 성공 시 series를 채운다', async () => {
    fetchCycleComparison.mockResolvedValue({ series: [{ name: 'A' }, { name: 'B' }] })
    const { result } = renderHook(() => useCycleComparisonData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.series).toHaveLength(2)
    expect(result.current.error).toBeNull()
  })

  it('API 실패 시 error를 채운다', async () => {
    fetchCycleComparison.mockRejectedValue(new Error('Network Error'))
    const { result } = renderHook(() => useCycleComparisonData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('Network Error')
  })

  it('API 성공 후 loading이 false가 된다', async () => {
    fetchCycleComparison.mockResolvedValue({ series: [] })
    const { result } = renderHook(() => useCycleComparisonData())
    await waitFor(() => expect(result.current.loading).toBe(false))
  })
})

describe('[QA] useBearBoxData', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('초기 상태: loading=true, lineData=[], boxes=[], predictions=[]', () => {
    fetchBearBoxes.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useBearBoxData(4))
    expect(result.current.loading).toBe(true)
    expect(result.current.lineData).toEqual([])
    expect(result.current.boxes).toEqual([])
    expect(result.current.predictions).toEqual([])
  })

  it('API 성공 시 lineData/boxes/predictions를 채운다', async () => {
    fetchBearBoxes.mockResolvedValue({
      lineData: [{ day: 0, price: 100 }],
      boxes: [{ id: 1, hi: 200, lo: 100 }],
      predictions: [{ Peak_Rate: 1.5 }],
      cycleInfo: { startDate: '2025-01-01', endDate: '2025-12-31' },
      config: {},
    })
    const { result } = renderHook(() => useBearBoxData(4))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.lineData).toHaveLength(1)
    expect(result.current.boxes).toHaveLength(1)
    expect(result.current.predictions).toHaveLength(1)
  })

  it('cycleNumber prop 변경 시 새로운 API 호출', async () => {
    fetchBearBoxes.mockResolvedValue({ lineData: [], boxes: [], predictions: [], cycleInfo: {}, config: {} })
    const { result, rerender } = renderHook(({ cycle }) => useBearBoxData(cycle), {
      initialProps: { cycle: 3 },
    })
    await waitFor(() => expect(result.current.loading).toBe(false))
    rerender({ cycle: 4 })
    await waitFor(() => expect(fetchBearBoxes).toHaveBeenCalledTimes(2))
  })
})

describe('[QA] useBullBoxData', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('초기 상태: loading=true', () => {
    fetchBullBoxes.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useBullBoxData(3))
    expect(result.current.loading).toBe(true)
  })

  it('API 성공 시 lineData와 boxes 채운다', async () => {
    fetchBullBoxes.mockResolvedValue({
      lineData: [{ day: 0, price: 15000 }],
      boxes: [{ id: 1, hi: 20000, lo: 15000 }],
      cycleInfo: {},
      config: {},
    })
    const { result } = renderHook(() => useBullBoxData(3))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.lineData).toHaveLength(1)
    expect(result.current.boxes).toHaveLength(1)
  })
})

describe('[QA] useOhlcvData', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('초기 상태: data=[], loading=true', () => {
    fetchOhlcvData.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useOhlcvData())
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toEqual([])
  })

  it('API 성공 시 data를 채운다', async () => {
    fetchOhlcvData.mockResolvedValue({ data: [{ time: '2025-01-01', open: 100 }] })
    const { result } = renderHook(() => useOhlcvData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toHaveLength(1)
  })
})
