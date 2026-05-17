/**
 * useBearBoxTooltip.js — BearBoxChart 전용 HTML 툴팁 훅
 *
 * F-03 스펙:
 *   - 박스 레이블 (H1, L1, H2, L2 …)
 *   - 현재 값 (% from peak)
 *   - 가장 가까운 박스 라인까지 거리 (±pp)
 *   - 예측 박스의 경우 예상 도달 날짜 표시
 *
 * 아키텍처 규칙:
 *   - DOM 직접 조작 없음, 순수 상태 반환
 *   - chartRef.current null 체크 필수
 *   - API URL / fetch() 없음
 */
import { useState, useEffect, useCallback } from 'react'

const PROXIMITY_PX = 22   // 박스 라인 근접 판단 픽셀
const EDGE_PADDING = 8
const TOOLTIP_W = 230
const TOOLTIP_H = 140

/**
 * @param {React.RefObject} chartRef       lightweight-charts 인스턴스
 * @param {React.RefObject} mainSeriesRef  메인 라인 시리즈 (현재가 추출)
 * @param {React.RefObject} containerRef   컨테이너 div (클리핑 보정)
 * @param {Array}           boxes          실제 박스 데이터
 * @param {Array}           predictions    예측 박스 데이터
 */
export function useBearBoxTooltip({
  chartRef,
  mainSeriesRef,
  containerRef,
  boxes = [],
  predictions = [],
}) {
  const [tooltipState, setTooltipState] = useState(null)

  // 뷰포트 클리핑 보정
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

      // ── 현재 값 추출 ─────────────────────────────────────────────
      let currentValue = null
      const mainSeries = mainSeriesRef?.current
      if (mainSeries) {
        try {
          const dp = param.seriesData?.get(mainSeries)
          currentValue = dp?.value ?? dp?.close ?? null
        } catch { /* 무시 */ }
      }

      // ── 날짜 레이블 ──────────────────────────────────────────────
      const dateLabel = (() => {
        try {
          const d = typeof param.time === 'string'
            ? new Date(param.time)
            : new Date(param.time * 1000)
          return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
        } catch { return String(param.time) }
      })()

      // ── 가장 가까운 박스 라인 탐색 ───────────────────────────────
      let nearestBox = null
      let nearestDist = Infinity

      const allBoxes = [
        ...boxes.map((b, i) => ({
          label: `H${i + 1}`,
          price: b.Peak_Rate,
          type: 'hi',
          isPrediction: false,
          endDate: null,
        })),
        ...boxes.map((b, i) => ({
          label: `L${i + 1}`,
          price: b.Start_Rate,
          type: 'lo',
          isPrediction: false,
          endDate: null,
        })),
        ...predictions.map((p, i) => ({
          label: `H${boxes.length + i + 1}(예측)`,
          price: p.Peak_Rate,
          type: 'hi',
          isPrediction: true,
          endDate: p.Peak_Timestamp
            ? new Date(p.Peak_Timestamp).toLocaleDateString('ko-KR')
            : null,
        })),
        ...predictions.map((p, i) => ({
          label: `L${boxes.length + i + 1}(예측)`,
          price: p.Start_Rate,
          type: 'lo',
          isPrediction: true,
          endDate: p.Start_Timestamp
            ? new Date(p.Start_Timestamp).toLocaleDateString('ko-KR')
            : null,
        })),
      ].filter((b) => b.price != null)

      for (const box of allBoxes) {
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

      // ── 거리 계산 ────────────────────────────────────────────────
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
              isPrediction: nearestBox.isPrediction,
              endDate: nearestBox.endDate,
            }
          : null,
      })
    },
    [chartRef, mainSeriesRef, containerRef, boxes, predictions, calcPosition]
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
