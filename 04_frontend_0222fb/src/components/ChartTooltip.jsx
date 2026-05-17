/**
 * ChartTooltip.jsx — HTML 오버레이 툴팁 UI 컴포넌트
 *
 * 아키텍처 규칙:
 *   - position:absolute + pointer-events:none → 캔버스 인터랙션 방해 없음
 *   - 데이터 가공 없음 — useChartTooltip 훅에서 받은 상태 그대로 렌더링
 *   - 스타일: Tooltip.css 전용 클래스 사용
 *
 * @param {{ tooltipState: { x: number, y: number, dayLabel: string, items: Array } | null }} props
 */
import '../styles/Tooltip.css'

export default function ChartTooltip({ tooltipState }) {
  if (!tooltipState) return null

  const { x, y, dayLabel, items } = tooltipState

  return (
    <div
      className="chart-tooltip"
      style={{ left: x, top: y }}
      role="tooltip"
      aria-live="polite"
    >
      {/* 날짜 헤더 */}
      <div className="chart-tooltip__header">
        <span className="chart-tooltip__day">{dayLabel}</span>
      </div>

      {/* 시리즈별 값 */}
      <div className="chart-tooltip__body">
        {items.map((item) => (
          <div key={item.name} className="chart-tooltip__row">
            {/* 색상 인디케이터 */}
            <span
              className="chart-tooltip__dot"
              style={{ background: item.color }}
              aria-hidden="true"
            />
            {/* 시리즈명 */}
            <span className="chart-tooltip__name">{item.name}</span>
            {/* 현재값 */}
            <span className="chart-tooltip__value">{item.value}</span>
            {/* 등락 */}
            {item.diff && (
              <span
                className={`chart-tooltip__diff ${
                  item.diff.startsWith('+') ? 'chart-tooltip__diff--up' : 'chart-tooltip__diff--down'
                }`}
              >
                {item.diff}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
