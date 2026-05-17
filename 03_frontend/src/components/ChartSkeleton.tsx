/**
 * ChartSkeleton.tsx — 차트 로딩 스켈레톤 (TypeScript)
 *
 * 04_frontend ChartSkeleton.jsx 기반 TypeScript 포팅
 *
 * BUG-10 수정: role="status" + aria-live (aria-label 제거)
 */
import type { CSSProperties } from 'react'

interface ChartSkeletonProps {
  type?: 'line' | 'bar'
}

const SKEL_BASE: CSSProperties = {
  borderRadius: 4,
  background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.07) 50%, rgba(255,255,255,0.03) 75%)',
  backgroundSize: '200% 100%',
  animation: 'skelPulse 1.4s ease-in-out infinite',
}

export default function ChartSkeleton({ type = 'line' }: ChartSkeletonProps) {
  return (
    <div style={s.wrap} role="status" aria-live="polite">
      {/* 타이틀 스트립 스켈레톤 */}
      <div style={s.titleStrip}>
        <div style={{ ...SKEL_BASE, ...s.kicker }} />
        <div style={{ ...SKEL_BASE, ...s.heading }} />
        <div style={{ ...SKEL_BASE, ...s.copy }} />
      </div>

      {/* 차트 캔버스 */}
      <div style={s.canvas}>
        {/* Y축 */}
        <div style={s.yAxis}>
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} style={{ ...SKEL_BASE, ...s.yLabel }} />
          ))}
        </div>

        {/* 플롯 */}
        <div style={s.plot}>
          {type === 'line' ? (
            <svg
              viewBox="0 0 600 200"
              preserveAspectRatio="none"
              style={s.svg}
              aria-hidden="true"
            >
              <polyline
                points="0,180 60,140 120,90 180,120 240,60 300,80 360,110 420,70 480,90 540,110 600,95"
                fill="none"
                stroke="rgba(255,255,255,0.07)"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            <div style={s.bands}>
              {[0.72, 0.55, 0.38, 0.22].map((pct, i) => (
                <div
                  key={i}
                  style={{
                    ...SKEL_BASE,
                    ...s.band,
                    top: `${(1 - pct) * 100}%`,
                  }}
                />
              ))}
            </div>
          )}

          {/* X축 */}
          <div style={s.xAxis}>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} style={{ ...SKEL_BASE, ...s.xLabel }} />
            ))}
          </div>
        </div>
      </div>

      {/* 스크린 리더 */}
      <span
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          overflow: 'hidden',
          clip: 'rect(0,0,0,0)',
          whiteSpace: 'nowrap',
        }}
      >
        차트 데이터를 불러오고 있습니다. 잠시 기다려 주세요.
      </span>

      <style>{`
        @keyframes skelPulse {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}

const s: Record<string, CSSProperties> = {
  wrap: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    padding: '12px 16px',
    gap: 12,
    position: 'relative',
  },
  titleStrip: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    padding: '8px 0 12px',
  },
  kicker: { width: 80, height: 10 },
  heading: { width: 240, height: 18 },
  copy: { width: 320, height: 11 },
  canvas: {
    display: 'flex',
    flex: 1,
    gap: 8,
    minHeight: 200,
  },
  yAxis: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    width: 40,
  },
  yLabel: { width: 32, height: 10 },
  plot: {
    flex: 1,
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
  },
  svg: {
    width: '100%',
    height: '100%',
    flex: 1,
  },
  bands: {
    position: 'relative',
    flex: 1,
  },
  band: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
  },
  xAxis: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '4px 0',
  },
  xLabel: { width: 48, height: 10 },
}
