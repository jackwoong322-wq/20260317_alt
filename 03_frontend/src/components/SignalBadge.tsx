/**
 * SignalBadge.tsx
 * BUY / HOLD / SELL 신호를 영문 기술 용어 배지로 표시
 * 03_frontend는 전문 분석가 대상 → 영문 표기 사용
 */
import type { CSSProperties } from 'react'

export type Signal = 'BUY' | 'HOLD' | 'SELL'

interface SignalConfig {
  label: string
  shortLabel: string   // 375px 모바일용 축약형
  icon: string
  style: CSSProperties
  ariaLabel: string
}

const SIGNAL_CONFIG: Record<Signal, SignalConfig> = {
  BUY: {
    label: 'ACCUMULATE ZONE',
    shortLabel: 'ACCUM.',
    icon: '▲',
    style: {
      background: 'rgba(52, 211, 153, 0.12)',
      color: '#34d399',
      border: '1px solid rgba(52, 211, 153, 0.3)',
    },
    ariaLabel: 'Current zone: Accumulate / Buy',
  },
  HOLD: {
    label: 'HOLD / OBSERVE',
    shortLabel: 'HOLD',
    icon: '—',
    style: {
      background: 'rgba(100, 116, 139, 0.15)',
      color: '#94a3b8',
      border: '1px solid rgba(100, 116, 139, 0.25)',
    },
    ariaLabel: 'Current zone: Hold and observe',
  },
  SELL: {
    label: 'DISTRIBUTION ZONE',
    shortLabel: 'DIST.',
    icon: '▼',
    style: {
      background: 'rgba(251, 113, 133, 0.12)',
      color: '#fb7185',
      border: '1px solid rgba(251, 113, 133, 0.3)',
    },
    ariaLabel: 'Current zone: Distribution / Sell',
  },
}


interface SignalBadgeProps {
  signal: Signal | string
}

export default function SignalBadge({ signal }: SignalBadgeProps) {
  const config = SIGNAL_CONFIG[signal as Signal] ?? SIGNAL_CONFIG.HOLD

  return (
    <span
      role="status"
      aria-label={config.ariaLabel}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 10px',
        borderRadius: 999,
        fontSize: '0.72rem',
        fontWeight: 700,
        letterSpacing: '0.08em',
        fontFamily: '"JetBrains Mono", monospace',
        whiteSpace: 'nowrap',
        ...config.style,
      }}
    >
      <span aria-hidden="true" style={{ fontSize: '0.65em' }}>{config.icon}</span>
      {config.label}
    </span>
  )
}

/**
 * positionPercent → Signal 결정
 * < 30%  → BUY (ACCUMULATE ZONE)
 * < 70%  → HOLD
 * ≥ 70%  → SELL (DISTRIBUTION ZONE)
 */
export function positionToSignal(positionPercent: number): Signal {
  if (positionPercent < 30) return 'BUY'
  if (positionPercent < 70) return 'HOLD'
  return 'SELL'
}
