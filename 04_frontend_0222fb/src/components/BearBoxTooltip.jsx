/**
 * BearBoxTooltip.jsx — BearBoxChart / BullBoxChart 전용 HTML 오버레이 툴팁
 *
 * F-03 스펙 표시 항목:
 *   - 날짜 (YYYY.MM.DD)
 *   - 현재가 (% from peak)
 *   - 근접 박스 라인: 레이블(H/L 넘버), 가격(%), 거리(±pp)
 *   - 예측 박스인 경우: 예상 도달 날짜
 *
 * BUG-05 수정: null 시 언마운트 대신 visibility:hidden으로 DOM 유지 (aria-live 호환)
 *
 * @param {{ tooltipState: object | null }} props
 */
import '../styles/Tooltip.css'

export default function BearBoxTooltip({ tooltipState }) {
  const visible = !!tooltipState
  const {
    x = 0,
    y = 0,
    dateLabel = '',
    currentValue = null,
    nearestBox = null,
  } = tooltipState ?? {}

  return (
    <div
      className="chart-tooltip chart-tooltip--bearbox"
      style={{
        left: x,
        top: y,
        visibility: visible ? 'visible' : 'hidden',
        pointerEvents: 'none',
      }}
      role="tooltip"
      aria-live="polite"
      aria-hidden={!visible}
    >
      {/* 날짜 헤더 */}
      <div className="chart-tooltip__header">
        <span className="chart-tooltip__day">{dateLabel}</span>
      </div>

      <div className="chart-tooltip__body">
        {/* 현재가 행 */}
        {currentValue && (
          <div className="chart-tooltip__row">
            <span
              className="chart-tooltip__dot"
              style={{ background: 'var(--color-info)' }}
              aria-hidden="true"
            />
            <span className="chart-tooltip__name">현재가</span>
            <span className="chart-tooltip__value">{currentValue}</span>
          </div>
        )}

        {/* 근접 박스 라인 정보 */}
        {nearestBox && (
          <>
            <div className="chart-tooltip__divider" />
            <div className="chart-tooltip__row">
              <span
                className="chart-tooltip__dot"
                style={{
                  background: nearestBox.isPrediction
                    ? 'var(--color-accent)'
                    : nearestBox.label.startsWith('H')
                    ? 'var(--color-danger)'
                    : 'var(--color-success)',
                }}
                aria-hidden="true"
              />
              <span className="chart-tooltip__name">{nearestBox.label}</span>
              <span className="chart-tooltip__value">{nearestBox.price}</span>
              {nearestBox.dist && (
                <span
                  className={`chart-tooltip__diff ${
                    nearestBox.dist.startsWith('+')
                      ? 'chart-tooltip__diff--up'
                      : 'chart-tooltip__diff--down'
                  }`}
                >
                  {nearestBox.dist}
                </span>
              )}
            </div>

            {/* 예측 도달 날짜 */}
            {nearestBox.isPrediction && nearestBox.endDate && (
              <div className="chart-tooltip__pred-date">
                <span className="chart-tooltip__pred-icon">📅</span>
                <span>예상 도달: {nearestBox.endDate}</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
