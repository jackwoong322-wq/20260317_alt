/**
 * useChartTooltip.js — lightweight-charts 크로스헤어 기반 HTML 툴팁 훅
 *
 * 아키텍처 규칙:
 *   - 차트 인스턴스(chartRef)와 시리즈 배열을 받아 툴팁 상태만 계산
 *   - DOM 직접 조작 없음, 순수 상태 반환
 *   - containerRef로 뷰포트 클리핑 좌표 자동 보정
 *
 * @returns {{ tooltipState, resetTooltip }}
 */
import { useState, useEffect, useCallback, useRef } from 'react'

const TOOLTIP_WIDTH = 220   // px — 오른쪽 경계 초과 판단 기준
const TOOLTIP_HEIGHT = 120  // px — 하단 경계 초과 판단 기준
const EDGE_PADDING = 8      // px — 컨테이너 엣지 여백

/**
 * @param {React.RefObject} chartRef    lightweight-charts 인스턴스
 * @param {Array}           seriesList  { name, color, seriesRef } 배열
 * @param {React.RefObject} containerRef 컨테이너 div (좌표 클리핑용)
 */
export function useChartTooltip(chartRef, seriesList = [], containerRef = null) {
  const [tooltipState, setTooltipState] = useState(null)
  // tooltipState: { x, y, dayLabel, items: [{ name, color, value, diff }] } | null

  const prevValuesRef = useRef({}) // 이전 값 저장 (등락 계산용)

  const calcClippedPosition = useCallback((rawX, rawY, containerEl) => {
    if (!containerEl) return { x: rawX + 14, y: rawY - 10 }

    const { width, height } = containerEl.getBoundingClientRect()
    let x = rawX + 14
    let y = rawY - 10

    // 우측 클리핑 보정
    if (x + TOOLTIP_WIDTH + EDGE_PADDING > width) {
      x = rawX - TOOLTIP_WIDTH - 14
    }
    // 하단 클리핑 보정
    if (y + TOOLTIP_HEIGHT + EDGE_PADDING > height) {
      y = height - TOOLTIP_HEIGHT - EDGE_PADDING
    }
    // 상단 음수 방지
    if (y < EDGE_PADDING) y = EDGE_PADDING

    return { x, y }
  }, [])

  const handleCrosshairMove = useCallback(
    (param) => {
      const chart = chartRef.current
      if (!chart || !param?.point || !param?.time) {
        setTooltipState(null)
        return
      }

      const { x: rawX, y: rawY } = param.point

      // 날짜 레이블 계산 (시리즈는 Day 기반 인덱스)
      const dayLabel = (() => {
        try {
          const base = new Date(2000, 0, 1)
          const d = new Date(param.time)
          const diff = Math.round((d - base) / 86400000)
          return `Day ${diff}`
        } catch {
          return String(param.time)
        }
      })()

      // 각 시리즈에서 해당 시점 값 추출
      const items = seriesList
        .map(({ name, color, seriesRef }) => {
          if (!seriesRef?.current) return null
          try {
            const dataPoint = param.seriesData?.get(seriesRef.current)
            if (!dataPoint) return null
            const value = dataPoint.value ?? dataPoint.close ?? null
            if (value == null) return null

            const prev = prevValuesRef.current[name]
            const diff =
              prev != null
                ? (value - prev >= 0 ? '+' : '') + (value - prev).toFixed(2) + '%'
                : null

            return { name, color, value: value.toFixed(2) + '%', diff }
          } catch {
            return null
          }
        })
        .filter(Boolean)

      // 이전값 갱신
      items.forEach(({ name, value }) => {
        prevValuesRef.current[name] = parseFloat(value)
      })

      if (items.length === 0) {
        setTooltipState(null)
        return
      }

      const containerEl = containerRef?.current ?? null
      const { x, y } = calcClippedPosition(rawX, rawY, containerEl)

      setTooltipState({ x, y, dayLabel, items })
    },
    [chartRef, seriesList, containerRef, calcClippedPosition]
  )

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    chart.subscribeCrosshairMove(handleCrosshairMove)
    return () => {
      try {
        chart.unsubscribeCrosshairMove(handleCrosshairMove)
      } catch {
        // 차트가 이미 unmount된 경우 무시
      }
    }
  }, [chartRef, handleCrosshairMove])

  const resetTooltip = useCallback(() => setTooltipState(null), [])

  return { tooltipState, resetTooltip }
}
