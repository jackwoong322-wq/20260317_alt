/**
 * WakingBanner.tsx
 * Render cold-start 재부팅 대기 배너
 * 재시도 중일 때만 표시 (loading + attempt > 0)
 */
import { useState, useEffect, type CSSProperties } from 'react'

interface WakingBannerProps {
  attempt: number
  maxRetries: number
}

export default function WakingBanner({ attempt, maxRetries }: WakingBannerProps) {
  const [countdown, setCountdown] = useState(10)

  useEffect(() => {
    setCountdown(10)
    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { clearInterval(timer); return 0 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [attempt])

  const progressPct = Math.round((attempt / maxRetries) * 100)

  return (
    <div style={s.wrap} role="status" aria-live="polite" aria-label="Server restarting">
      <div style={s.spinner}>
        <svg width="20" height="20" viewBox="0 0 20 20" style={s.spinSvg} aria-hidden="true">
          <circle cx="10" cy="10" r="8" fill="none" stroke="rgba(108,156,255,0.2)" strokeWidth="2.5" />
          <path d="M10 2 A8 8 0 0 1 18 10" fill="none" stroke="#6c9cff" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </div>
      <div style={s.text}>
        <span style={s.title}>🚀 Waking up the Render server...</span>
        <span style={s.desc}>Server is restarting. Chart will appear automatically.</span>
      </div>
      <div style={s.right}>
        <div style={s.barWrap}>
          <div style={{ ...s.barFill, width: `${progressPct}%` }} />
        </div>
        <span style={s.meta}>
          Attempt {attempt}/{maxRetries}
          {' · '}
          <span style={s.countdown}>
            {countdown > 0 ? `retry in ${countdown}s` : 'retrying...'}
          </span>
        </span>
      </div>
    </div>
  )
}

const s: Record<string, CSSProperties> = {
  wrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 20px',
    background: 'linear-gradient(90deg, rgba(108,156,255,0.08), rgba(108,156,255,0.04))',
    borderBottom: '1px solid rgba(108,156,255,0.2)',
    fontFamily: '"JetBrains Mono", monospace',
  },
  spinner: {
    flexShrink: 0,
    animation: 'waking-spin 1s linear infinite',
  },
  spinSvg: {
    display: 'block',
    animation: 'waking-spin 1s linear infinite',
  },
  text: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    flex: 1,
  },
  title: {
    fontSize: '0.82rem',
    fontWeight: 700,
    color: '#6c9cff',
    letterSpacing: '0.02em',
  },
  desc: {
    fontSize: '0.74rem',
    color: '#6882a7',
  },
  right: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: 4,
    flexShrink: 0,
  },
  barWrap: {
    width: 120,
    height: 3,
    borderRadius: 999,
    background: 'rgba(108,156,255,0.12)',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 999,
    background: '#6c9cff',
    transition: 'width 600ms ease',
  },
  meta: {
    fontSize: '0.7rem',
    color: '#6882a7',
  },
  countdown: {
    color: '#6c9cff',
    fontWeight: 700,
  },
}
