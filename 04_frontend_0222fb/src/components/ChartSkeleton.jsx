/**
 * ChartSkeleton.jsx — 차트 로딩 스켈레톤 (F-06)
 *
 * 데이터 로딩 중 실제 차트 레이아웃과 유사한 뼈대를 펄스 애니메이션으로 표시.
 * 스켈레톤은 ChartLoadingState를 대체하며 더 나은 UX를 제공한다.
 *
 * @param {{ type?: 'line' | 'bar' }} props
 *   type: 'line' (사이클/트레이딩), 'bar' (박스 차트)
 */
import '../styles/Chart.css'

export default function ChartSkeleton({ type = 'line' }) {
  return (
    <div className="chart-skeleton" role="status" aria-live="polite">
      {/* 타이틀 스트립 스켈레톤 */}
      <div className="chart-skeleton__title-strip">
        <div className="chart-skeleton__kicker skel-pulse" />
        <div className="chart-skeleton__heading skel-pulse" />
        <div className="chart-skeleton__copy skel-pulse" />
      </div>

      {/* 차트 캔버스 스켈레톤 */}
      <div className="chart-skeleton__canvas">
        {/* Y축 레이블 */}
        <div className="chart-skeleton__y-axis">
          {[100, 75, 50, 25, 0].map((v) => (
            <div key={v} className="chart-skeleton__y-label skel-pulse" />
          ))}
        </div>

        {/* 차트 본문 */}
        <div className="chart-skeleton__plot">
          {type === 'line' ? (
            /* 라인 차트용 곡선 SVG 스켈레톤 */
            <svg
              viewBox="0 0 600 200"
              preserveAspectRatio="none"
              className="chart-skeleton__svg"
              aria-hidden="true"
            >
              <polyline
                points="0,180 60,140 120,90 180,120 240,60 300,80 360,110 420,70 480,90 540,110 600,95"
                fill="none"
                stroke="var(--color-border)"
                strokeWidth="3"
                strokeLinecap="round"
                className="chart-skeleton__line"
              />
              <polyline
                points="0,190 60,160 120,140 180,155 240,130 300,145 360,135 420,150 480,140 540,155 600,145"
                fill="none"
                stroke="var(--color-border)"
                strokeWidth="2"
                strokeLinecap="round"
                className="chart-skeleton__line chart-skeleton__line--secondary"
              />
            </svg>
          ) : (
            /* 박스 차트용 수평 밴드 스켈레톤 */
            <div className="chart-skeleton__bands">
              {[0.72, 0.55, 0.38, 0.22].map((pct, i) => (
                <div
                  key={i}
                  className="chart-skeleton__band skel-pulse"
                  style={{ top: `${(1 - pct) * 100}%` }}
                />
              ))}
            </div>
          )}

          {/* X축 레이블 */}
          <div className="chart-skeleton__x-axis">
            {['Day 0', 'Day 100', 'Day 200', 'Day 300'].map((label) => (
              <div key={label} className="chart-skeleton__x-label skel-pulse" />
            ))}
          </div>
        </div>
      </div>

      {/* 푸터 스켈레톤 */}
      <div className="chart-skeleton__footer">
        <div className="chart-skeleton__footer-text skel-pulse" />
      </div>

      {/* 스크린 리더 텍스트 */}
      <span className="sr-only">차트 데이터를 불러오고 있습니다. 잠시 기다려 주세요.</span>
    </div>
  )
}
