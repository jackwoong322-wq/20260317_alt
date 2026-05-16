/**
 * SummaryCard.tsx
 * 대시보드 상단 요약 카드 (03_frontend용)
 *
 * 데이터 소스: /api/bear-boxes?cycle=4 (04_frontend와 동일 엔드포인트 재사용)
 * Props로 bearBoxes 데이터를 받아서 파싱 — 별도 API 호출 없음
 *
 * 표시 항목:
 *   - BTC 사이클 차수
 *   - close_rate 현재 위치%
 *   - 사이클 고점 rate / 저점 rate
 *   - 다음 예측 고점 rate
 *   - SignalBadge
 */
import type { CSSProperties } from 'react'
import SignalBadge, { positionToSignal } from './SignalBadge'

// /api/bear-boxes 응답 타입 (일부)
interface BearBox {
  Start_Rate: number
  Peak_Rate: number
}

interface BearPrediction {
  Peak_Rate: number
}

interface LineDataPoint {
  value: number
}

export interface BearBoxesData {
  lineData: LineDataPoint[]
  boxes: BearBox[]
  predictions: BearPrediction[]
}

interface SummaryCardProps {
  cycleNumber: number
  data: BearBoxesData | null
}

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val == null) return '—'
  return val.toFixed(decimals) + 'x'
}

function calcPositionPercent(current: number, lo: number, hi: number): number {
  if (hi <= lo) return 0
  return Math.max(0, Math.min(100, ((current - lo) / (hi - lo)) * 100))
}

export default function SummaryCard({ cycleNumber, data }: SummaryCardProps) {
  if (!data || data.lineData.length === 0) {
    return (
      <div style={s.wrap}>
        <div style={s.skeleton} aria-label="Loading summary..." />
      </div>
    )
  }

  const currentRate = data.lineData[data.lineData.length - 1]?.value ?? 0
  const lastBox = data.boxes[data.boxes.length - 1]
  const hiRate = lastBox?.Peak_Rate ?? 0
  const loRate = lastBox?.Start_Rate ?? 0
  const nextPred = data.predictions[0]?.Peak_Rate ?? null
  const positionPct = calcPositionPercent(currentRate, loRate, hiRate)
  const signal = positionToSignal(positionPct)

  const fillColor =
    signal === 'BUY' ? '#34d399' : signal === 'SELL' ? '#fb7185' : '#6c9cff'

  return (
    <div style={s.wrap} aria-label="Cycle summary">
      {/* 왼쪽: 사이클 표시 */}
      <div style={s.cycleBlock}>
        <span style={s.eyebrow}>BTC CYCLE</span>
        <span style={s.cycleNum}>#{cycleNumber}</span>
      </div>

      {/* 구분선 */}
      <div style={s.divider} />

      {/* 통계 */}
      <div style={s.statsRow}>
        <StatItem label="CURRENT" value={fmt(currentRate)} highlight />
        <StatItem label="CYCLE HI" value={fmt(hiRate)} />
        <StatItem label="CYCLE LO" value={fmt(loRate)} />
        <StatItem label="NEXT PRED" value={fmt(nextPred)} accent />
      </div>

      {/* 구분선 */}
      <div style={s.divider} />

      {/* 위치 바 + 배지 */}
      <div style={s.rightBlock}>
        <div style={s.posRow}>
          <span style={{ ...s.posLabel, color: fillColor }}>
            {positionPct.toFixed(1)}%
          </span>
          <div style={s.barWrap} aria-label={`Position ${positionPct.toFixed(1)}%`}>
            <div style={{ ...s.barFill, width: `${positionPct}%`, background: fillColor }} />
          </div>
        </div>
        <SignalBadge signal={signal} />
      </div>
    </div>
  )
}

function StatItem({
  label,
  value,
  highlight = false,
  accent = false,
}: {
  label: string
  value: string
  highlight?: boolean
  accent?: boolean
}) {
  return (
    <div style={s.statItem}>
      <span style={s.statLabel}>{label}</span>
      <span
        style={{
          ...s.statValue,
          color: highlight ? '#f6fbff' : accent ? '#6c9cff' : '#9cb2ce',
          fontSize: highlight ? '0.88rem' : '0.78rem',
        }}
      >
        {value}
      </span>
    </div>
  )
}

const s: Record<string, CSSProperties> = {
  wrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    padding: '6px 12px',
    minHeight: 48,
    background: '#0d1725',
    borderBottom: '1px solid #1a2c46',
    fontFamily: '"JetBrains Mono", monospace',
    flexShrink: 0,
    flexWrap: 'wrap',
    overflow: 'hidden',
  },
  skeleton: {
    flex: 1,
    height: 16,
    borderRadius: 8,
    background: 'rgba(255,255,255,0.05)',
  },
  cycleBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
    paddingRight: 16,
  },
  eyebrow: {
    fontSize: '0.6rem',
    fontWeight: 700,
    letterSpacing: '0.2em',
    color: '#6882a7',
  },
  cycleNum: {
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#6c9cff',
    lineHeight: 1,
  },
  divider: {
    width: 1,
    height: 32,
    background: '#1a2c46',
    marginRight: 16,
    flexShrink: 0,
  },
  statsRow: {
    display: 'flex',
    gap: 0,
    flex: 1,
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    padding: '0 14px',
    borderRight: '1px solid #1a2c46',
  },
  statLabel: {
    fontSize: '0.58rem',
    fontWeight: 700,
    letterSpacing: '0.15em',
    color: '#6882a7',
  },
  statValue: {
    fontWeight: 700,
    letterSpacing: '0.04em',
  },
  rightBlock: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: 4,
    paddingLeft: 16,
    flexShrink: 0,
  },
  posRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  posLabel: {
    fontSize: '0.72rem',
    fontWeight: 700,
    width: 42,
    textAlign: 'right',
  },
  barWrap: {
    width: 80,
    height: 4,
    borderRadius: 999,
    background: 'rgba(255,255,255,0.06)',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 999,
    transition: 'width 700ms ease',
  },
}
