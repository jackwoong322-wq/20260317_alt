/**
 * useBullBoxTooltip.js — BullBoxChart 전용 HTML 툴팁 훅
 *
 * BearBoxTooltip과 동일 구조, Bull 박스 데이터 인터페이스 적용:
 *   - 박스: { Start_Rate (고점), Low_Rate (저점), Low_Timestamp }
 *   - 표시: H(고점 진입), L(저점) 레이블 + 현재가 + 거리
 */
import { useState, useEffect, useCallback } from 'react'

const PROXIMITY_PX = 22
const EDGE_PADDING = 8
const TOOLTIP_W = 230
const TOOLTIP_H = 130

export function useBullBoxTooltip({
  chartRef,
  mainSeriesRef,
  containerRef,
  boxes = [],
}) {
  const [tooltipState, setTooltipState] = useState(null)

  const calcPosition = useCallback((rawX, rawY, containerEl) => {
    if (!containerEl) return { x: rawX + 14, y: rawY - 10 }
    const { width, height } = containerEl.getBoundingClientRect()
    let x = rawX + 14
    let y = rawY - 10
    if (x + TOOLTIP_W + EDGE_PADDING > width) x = rawX - TOOLTIP_W - 14
    if (y + TOOLTIP_H + EDGE_PADDING > height) y = height - TOOLTIP_H - EDGE_PADDING
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
      const priceScale = chart.priceScale('right')

      // 현재 값 추출
      let currentValue = null
      const mainSeries = mainSeriesRef?.current
      if (mainSeries) {
        try {
          const dp = param.seriesData?.get(mainSeries)
          currentValue = dp?.value ?? dp?.close ?? null
        } catch { /* 무시 */ }
      }

      // 날짜 레이블
      const dateLabel = (() => {
        try {
          const d = typeof param.time === 'string'
            ? new Date(param.time)
            : new Date(param.time * 1000)
          return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
        } catch { return String(param.time) }
      })()

      // Bull 박스 라인 목록: H(Start_Rate), L(Low_Rate)
      const allLines = [
        ...boxes.map((b, i) => ({
          label: `H${i + 1}`,
          price: b.Start_Rate,
          type: 'hi',
        })),
        ...boxes.map((b, i) => ({
          label: `L${i + 1}`,
          price: b.Low_Rate,
          type: 'lo',
        })),
      ].filter((b) => b.price != null)

      let nearestBox = null
      let nearestDist = Infinity

      for (const box of allLines) {
        try {
          const lineY = priceScale.priceToCoordinate(box.price)
          if (lineY == null) continue
          const dist = Math.abs(rawY - lineY)
          if (dist < PROXIMITY_PX && dist < nearestDist) {
            nearestDist = dist
            nearestBox = box
          }
        } catch { /* 무시 */ }
      }

      let distStr = null
      if (nearestBox && currentValue != null) {
        const diff = nearestBox.price - currentValue
        distStr = (diff >= 0 ? '+' : '') + diff.toFixed(2) + 'pp'
      }

      const containerEl = containerRef?.current ?? null
      const { x, y } = calcPosition(rawX, rawY, containerEl)

      setTooltipState({
        x,
        y,
        dateLabel,
        currentValue: currentValue != null ? currentValue.toFixed(2) + '%' : null,
        nearestBox: nearestBox
          ? {
              label: nearestBox.label,
              price: nearestBox.price.toFixed(2) + '%',
              dist: distStr,
              isPrediction: false,
              endDate: null,
            }
          : null,
      })
    },
    [chartRef, mainSeriesRef, containerRef, boxes, calcPosition]
  )

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return
    chart.subscribeCrosshairMove(handleCrosshairMove)
    return () => {
      try { chart.unsubscribeCrosshairMove(handleCrosshairMove) } catch { /* 무시 */ }
    }
  }, [chartRef, handleCrosshairMove])

  return { tooltipState, clearTooltip: () => setTooltipState(null) }
}
