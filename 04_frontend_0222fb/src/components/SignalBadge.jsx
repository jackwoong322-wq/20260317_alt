/**
 * SignalBadge.jsx
 * BUY / HOLD / SELL 신호를 직관적인 색상·아이콘 배지로 표시
 * Tailwind CSS 사용
 */

const SIGNAL_CONFIG = {
  BUY: {
    label: '매수 구간',
    icon: '▲',
    className:
      'bg-buy/20 text-buy border border-buy/40 animate-pulse',
    ariaLabel: '현재 매수 진입 구간입니다',
  },
  HOLD: {
    label: '관망',
    icon: '—',
    className:
      'bg-hold/10 text-hold border border-hold/30',
    ariaLabel: '현재 관망 구간입니다',
  },
  SELL: {
    label: '매도 접근',
    icon: '▼',
    className:
      'bg-sell/20 text-sell border border-sell/40',
    ariaLabel: '현재 매도 접근 구간입니다',
  },
}

/**
 * @param {{ signal: 'BUY' | 'HOLD' | 'SELL', size?: 'sm' | 'md' | 'lg' }} props
 */
export default function SignalBadge({ signal, size = 'md' }) {
  const config = SIGNAL_CONFIG[signal] ?? SIGNAL_CONFIG.HOLD

  const sizeClass = {
    sm: 'text-[11px] px-2 py-0.5 gap-1',
    md: 'text-[13px] px-3 py-1 gap-1.5',
    lg: 'text-[15px] px-4 py-1.5 gap-2',
  }[size]

  return (
    <span
      className={`inline-flex items-center rounded-full font-bold tracking-wide whitespace-nowrap ${sizeClass} ${config.className}`}
      role="status"
      aria-label={config.ariaLabel}
    >
      <span className="text-[0.8em] leading-none" aria-hidden="true">
        {config.icon}
      </span>
      <span className="leading-none">{config.label}</span>
    </span>
  )
}
