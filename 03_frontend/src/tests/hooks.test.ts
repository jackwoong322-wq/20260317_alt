/**
 * hooks.test.ts — 03_frontend useTheme, useChartExport 훅 테스트
 *
 * QA 에이전트 작성 | Loop 22
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTheme } from '../hooks/useTheme'
import { useChartExport } from '../hooks/useChartExport'

// ── useTheme ──────────────────────────────────────────────────────────

describe('[QA] useTheme (TypeScript)', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('초기 테마는 dark이다', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
  })

  it('localStorage에 light 저장 시 초기 테마 light', () => {
    localStorage.setItem('btc-dashboard-theme', 'light')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
  })

  it('잘못된 localStorage 값 → dark 폴백', () => {
    localStorage.setItem('btc-dashboard-theme', 'blue')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
  })

  it('toggleTheme → dark→light', () => {
    const { result } = renderHook(() => useTheme())
    act(() => { result.current.toggleTheme() })
    expect(result.current.theme).toBe('light')
  })

  it('toggleTheme 2회 → 원래 값', () => {
    const { result } = renderHook(() => useTheme())
    act(() => {
      result.current.toggleTheme()
      result.current.toggleTheme()
    })
    expect(result.current.theme).toBe('dark')
  })

  it('data-theme 속성이 html에 적용된다', () => {
    const { result } = renderHook(() => useTheme())
    act(() => { result.current.toggleTheme() })
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('localStorage에 테마가 저장된다', () => {
    const { result } = renderHook(() => useTheme())
    act(() => { result.current.toggleTheme() })
    expect(localStorage.getItem('btc-dashboard-theme')).toBe('light')
  })

  it('toggleTheme 함수 참조가 안정적이다 (useCallback)', () => {
    const { result, rerender } = renderHook(() => useTheme())
    const fn = result.current.toggleTheme
    rerender()
    expect(result.current.toggleTheme).toBe(fn)
  })
})

// ── useChartExport ────────────────────────────────────────────────────

describe('[QA] useChartExport (TypeScript)', () => {
  it('초기 exporting은 false', () => {
    const chartRef = { current: null }
    const { result } = renderHook(() => useChartExport(chartRef, 'test'))
    expect(result.current.exporting).toBe(false)
  })

  it('초기 exportError는 null', () => {
    const chartRef = { current: null }
    const { result } = renderHook(() => useChartExport(chartRef, 'test'))
    expect(result.current.exportError).toBeNull()
  })

  it('chartRef.current가 null일 때 오류 메시지 설정', async () => {
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

  it('takeScreenshot가 있는 차트로 내보내기 시도', async () => {
    const mockCanvas = document.createElement('canvas')
    const mockChart = {
      takeScreenshot: vi.fn(() => mockCanvas),
    }
    const chartRef = { current: mockChart as unknown as import('lightweight-charts').IChartApi }

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const { result } = renderHook(() => useChartExport(chartRef, 'btc-test'))
    await act(async () => {
      await result.current.exportPng()
      await new Promise((r) => setTimeout(r, 50))
    })

    expect(mockChart.takeScreenshot).toHaveBeenCalledOnce()
    vi.restoreAllMocks()
  })
})
