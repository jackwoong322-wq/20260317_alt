/**
 * ChartOverlay.jsx
 * lightweight-charts 위에 HTML div 레이어로 툴팁을 표시
 *
 * 동작 원리:
 * - 차트 컨테이너를 position:relative 로 감싸고
 * - 이 컴포넌트는 position:absolute 로 그 위에 배치된다
 * - 차트 인스턴스의 subscribeCrosshairMove() 이벤트로
 *   마우스 Y 좌표를 받아 박스 H/L선에 근접 여부를 판단한다
 * - Canvas 직접 수정 없이 순수 HTML div만 사용
 *
 * Props:
 *   chartRef    {React.RefObject}  lightweight-charts 인스턴스 ref
 *   boxZones    {Array<{hi, lo}>}  표시할 박스 H/L 가격 배열
 */

import { useState, useEffect, useRef, useCallback } from 'react'

const PROXIMITY_THRESHOLD_PX = 18  // 이 픽셀 이내 접근 시 툴팁 표시

/**
 * @param {{ chartRef: React.RefObject, boxZones: Array<{hi:number, lo:number}> }} props
 */
export default function ChartOverlay({ chartRef, boxZones = [] }) {
  const [tooltip, setTooltip] = useState(null)
  // tooltip: { x, y, text } | null

  const overlayRef = useRef(null)

  const handleCrosshairMove = useCallback(
    (param) => {
      const chart = chartRef.current
      if (!chart || !param?.point) {
        setTooltip(null)
        return
      }

      const { x: cursorX, y: cursorY } = param.point
      const priceScale = chart.priceScale('right')

      // 박스 H/L 선 중 커서에 가장 가까운 것을 탐색
      let closest = null
      let closestDist = Infinity

      for (const zone of boxZones) {
        for (const [price, kind] of [
          [zone.hi, 'hi'],
          [zone.lo, 'lo'],
        ]) {
          if (price == null) continue
          try {
            const lineY = priceScale.priceToCoordinate(price)
            if (lineY == null) continue
            const dist = Math.abs(cursorY - lineY)
            if (dist < PROXIMITY_THRESHOLD_PX && dist < closestDist) {
              closestDist = dist
              closest = { lineY, kind, price }
            }
          } catch {
            // priceToCoordinate 실패 시 무시
          }
        }
      }

      if (closest) {
        const text =
          closest.kind === 'hi'
            ? '이 선을 돌파하면 다음 사이클 진입'
            : '이 선이 깨지면 하락 사이클 진입'
        setTooltip({ x: cursorX, y: closest.lineY, text })
      } else {
        setTooltip(null)
      }
    },
    [chartRef, boxZones]
  )

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    chart.subscribeCrosshairMove(handleCrosshairMove)
    return () => {
      try {
        chart.unsubscribeCrosshairMove(handleCrosshairMove)
      } catch {
        // 차트가 이미 제거된 경우 무시
      }
    }
  }, [chartRef, handleCrosshairMove])

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 pointer-events-none z-10"
      aria-hidden="true"
    >
      {tooltip && (
        <div
          className="absolute flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap
                     bg-chart-panel/95 border border-accent/40 text-accent shadow-xl backdrop-blur-sm
                     transition-all duration-100"
          style={{
            left: tooltip.x + 12,
            top: tooltip.y - 14,
            // 오른쪽 경계를 넘으면 왼쪽에 표시
            transform: tooltip.x > 300 ? 'none' : 'none',
          }}
        >
          <span className="text-[10px]">💡</span>
          {tooltip.text}
        </div>
      )}
    </div>
  )
}
