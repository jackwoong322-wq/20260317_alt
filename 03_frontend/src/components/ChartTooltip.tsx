/**
 * ChartTooltip.tsx — HTML 오버레이 툴팁 UI (TypeScript)
 *
 * 04_frontend ChartTooltip.jsx 기반 TypeScript 포팅
 *
 * BUG-05: null 시 언마운트 → visibility:hidden (DOM 유지, aria-live 호환)
 * BUG-08: visibility 대신 opacity/transform transition 기반 애니메이션
 */
import type { CSSProperties } from 'react'

export interface TooltipItem {
  name: string
  color: string
  value: string
  diff: string | null
}

export interface TooltipState {
  x: number
  y: number
  dayLabel: string
  items: TooltipItem[]
}

interface ChartTooltipProps {
  tooltipState: TooltipState | null
}

const TOOLTIP_STYLE: CSSProperties = {
  position: 'absolute',
  zIndex: 20,
  pointerEvents: 'none',
  minWidth: 180,
  maxWidth: 240,
  borderRadius: 12,
  border: '1px solid rgba(191,144,35,0.35)',
  background: 'rgba(10,18,32,0.96)',
  boxShadow: '0 8px 24px rgba(3,7,15,0.55)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  overflow: 'hidden',
  fontFamily: '"JetBrains Mono", monospace',
  transition: 'opacity 120ms ease, transform 120ms ease',
}

const VISIBLE_STYLE: CSSProperties = {
  opacity: 1,
  transform: 'translateY(0) scale(1)',
}

const HIDDEN_STYLE: CSSProperties = {
  opacity: 0,
  transform: 'translateY(-4px) scale(0.97)',
}

export default function ChartTooltip({ tooltipState }: ChartTooltipProps) {
  const visible = tooltipState !== null
  const { x = 0, y = 0, dayLabel = '', items = [] } = tooltipState ?? {}

  return (
    <div
      style={{
        ...TOOLTIP_STYLE,
        left: x,
        top: y,
        ...(visible ? VISIBLE_STYLE : HIDDEN_STYLE),
      }}
      role="tooltip"
      aria-live="polite"
      aria-hidden={!visible}
    >
      {/* 날짜 헤더 */}
      <div style={s.header}>
        <span style={s.day}>{dayLabel}</span>
      </div>

      {/* 시리즈별 값 */}
      <div style={s.body}>
        {items.map((item) => (
          <div key={item.name} style={s.row}>
            <span
              style={{ ...s.dot, background: item.color }}
              aria-hidden="true"
            />
            <span style={s.name}>{item.name}</span>
            <span style={s.value}>{item.value}</span>
            {item.diff && (
              <span
                style={{
                  ...s.diff,
                  color: item.diff.startsWith('+') ? '#34d399' : '#fb7185',
                }}
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

const s: Record<string, CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '7px 12px 6px',
    borderBottom: '1px solid rgba(255,255,255,0.08)',
    background: 'rgba(191,144,35,0.08)',
  },
  day: {
    fontSize: '0.68rem',
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#bf9023',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    padding: '6px 12px 8px',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '3px 0',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
  },
  name: {
    fontSize: '0.72rem',
    color: '#9cb2ce',
    flex: 1,
    minWidth: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  value: {
    fontSize: '0.78rem',
    fontWeight: 700,
    color: '#f6fbff',
    letterSpacing: '0.02em',
    marginLeft: 'auto',
  },
  diff: {
    fontSize: '0.68rem',
    fontWeight: 600,
    letterSpacing: '0.02em',
    minWidth: 52,
    textAlign: 'right',
  },
}
