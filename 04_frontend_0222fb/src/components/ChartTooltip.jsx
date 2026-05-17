/**
 * ChartTooltip.jsx — HTML 오버레이 툴팁 UI 컴포넌트
 *
 * 아키텍처 규칙:
 *   - position:absolute + pointer-events:none → 캔버스 인터랙션 방해 없음
 *   - 데이터 가공 없음 — useChartTooltip 훅에서 받은 상태 그대로 렌더링
 *   - 스타일: Tooltip.css 전용 클래스 사용
 *
 * BUG-05 수정: null 시 언마운트 → visibility:hidden으로 DOM 유지
 * 이유: aria-live는 이미 마운트된 요소의 변경만 감지함.
 * 언마운트/리마운트를 반복하면 스크린 리더에 고지되지 않음.
 *
 * @param {{ tooltipState: { x: number, y: number, dayLabel: string, items: Array } | null }} props
 */
import '../styles/Tooltip.css'

export default function ChartTooltip({ tooltipState }) {
  const visible = !!tooltipState
  const { x = 0, y = 0, dayLabel = '', items = [] } = tooltipState ?? {}

  return (
    <div
      className={`chart-tooltip${visible ? ' chart-tooltip--visible' : ''}`}
      style={{
        left: x,
        top: y,
        pointerEvents: 'none',
      }}
      role="tooltip"
      aria-live="polite"
      aria-hidden={!visible}
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
