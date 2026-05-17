/**
 * hooks.test.jsx — useTheme, useChartExport 훅 유닛 테스트 (추가)
 *
 * QA 에이전트 작성 | Loop 17
 * 커버리지 목표: useTheme 90%+, useChartExport 60%+
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTheme } from '../hooks/useTheme'
import { useChartExport } from '../hooks/useChartExport'

// ── useTheme 훅 테스트 ───────────────────────────────────────────────

describe('[QA] useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('초기 테마는 dark이다 (localStorage 없을 때)', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
  })

  it('localStorage에 light 저장 시 초기 테마가 light이다', () => {
    localStorage.setItem('btc-dashboard-theme', 'light')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
  })

  it('localStorage에 잘못된 값 저장 시 dark로 폴백한다', () => {
    localStorage.setItem('btc-dashboard-theme', 'invalid')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
  })

  it('toggleTheme 호출 시 dark → light 전환된다', () => {
    localStorage.setItem('btc-dashboard-theme', 'dark')
    const { result } = renderHook(() => useTheme())
    act(() => {
      result.current.toggleTheme()
    })
    expect(result.current.theme).toBe('light')
  })

  it('toggleTheme 두 번 호출 시 원래 테마로 복귀한다', () => {
    const { result } = renderHook(() => useTheme())
    act(() => {
      result.current.toggleTheme()
      result.current.toggleTheme()
    })
    expect(result.current.theme).toBe('dark')
  })

  it('테마 변경 시 html 요소에 data-theme 속성이 적용된다', () => {
    const { result } = renderHook(() => useTheme())
    act(() => {
      result.current.toggleTheme()
    })
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('테마 변경 시 localStorage에 저장된다', () => {
    const { result } = renderHook(() => useTheme())
    act(() => {
      result.current.toggleTheme()
    })
    expect(localStorage.getItem('btc-dashboard-theme')).toBe('light')
  })

  it('toggleTheme는 안정적인 함수 참조를 반환한다 (useCallback)', () => {
    const { result, rerender } = renderHook(() => useTheme())
    const firstFn = result.current.toggleTheme
    rerender()
    expect(result.current.toggleTheme).toBe(firstFn)
  })
})

// ── useChartExport 훅 테스트 ──────────────────────────────────────────

describe('[QA] useChartExport', () => {
  it('초기 exporting은 false이다', () => {
    const chartRef = { current: null }
    const { result } = renderHook(() => useChartExport(chartRef, 'test'))
    expect(result.current.exporting).toBe(false)
  })

  it('초기 exportError는 null이다', () => {
    const chartRef = { current: null }
    const { result } = renderHook(() => useChartExport(chartRef, 'test'))
    expect(result.current.exportError).toBeNull()
  })

  it('chartRef.current가 null일 때 exportPng는 오류 메시지를 설정한다', async () => {
    const chartRef = { current: null }
    const { result } = renderHook(() => useChartExport(chartRef, 'test'))
    await act(async () => {
      await result.current.exportPng()
    })
    expect(result.current.exportError).toBe('차트가 준비되지 않았습니다.')
  })

  it('exportPng는 함수이다', () => {
    const chartRef = { current: null }
    const { result } = renderHook(() => useChartExport(chartRef, 'test'))
    expect(typeof result.current.exportPng).toBe('function')
  })

  it('takeScreenshot가 있는 차트 ref로 PNG 내보내기를 시도한다', async () => {
    const mockCanvas = document.createElement('canvas')
    mockCanvas.width = 400
    mockCanvas.height = 200

    const mockChart = {
      takeScreenshot: vi.fn(() => mockCanvas),
    }
    const chartRef = { current: mockChart }

    // URL.createObjectURL / revokeObjectURL mock
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const { result } = renderHook(() => useChartExport(chartRef, 'btc-test'))

    await act(async () => {
      await result.current.exportPng()
      await new Promise((resolve) => setTimeout(resolve, 50))
    })

    expect(mockChart.takeScreenshot).toHaveBeenCalledOnce()
    vi.restoreAllMocks()
  })
})
