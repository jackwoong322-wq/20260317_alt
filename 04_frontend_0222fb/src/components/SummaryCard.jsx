/**
 * SummaryCard.jsx
 * 대시보드 상단 현재 상태 요약 카드
 *
 * 데이터 소스: /api/bear-boxes?cycle=5 (현재 사이클 실데이터)
 * 03_frontend와 동일한 엔드포인트 사용 → 동일한 결과 표시
 */

import { useState, useEffect } from 'react'
import SignalBadge from './SignalBadge'

const CURRENT_CYCLE = 5
const CURRENT_CYCLE_LABEL = 'CURRENT CYCLE (2025)'

const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

function formatRate(value) {
  if (value == null) return '—'
  return Number(value).toFixed(2) + 'x'
}

function calcPositionPercent(current, lo, hi) {
  if (hi <= lo) return 0
  return Math.max(0, Math.min(100, ((current - lo) / (hi - lo)) * 100))
}

function signalFromPercent(pct) {
  if (pct < 30) return 'BUY'
  if (pct < 70) return 'HOLD'
  return 'SELL'
}

/** 위치 바: 고점~저점 사이 현재가 위치를 시각화 */
function PositionBar({ percent }) {
  const clamped = Math.max(0, Math.min(100, percent ?? 0))

  const fillColor =
    clamped < 30  ? 'bg-buy' :
    clamped < 70  ? 'bg-accent' :
                    'bg-sell'

  const labelColor =
    clamped < 30  ? 'text-buy' :
    clamped < 70  ? 'text-accent' :
                    'text-sell'

  return (
    <div
      className="relative w-full h-1.5 rounded-full bg-white/10"
      role="img"
      aria-label={`고점 대비 현재가 위치 ${clamped.toFixed(1)}%`}
    >
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${fillColor}`}
        style={{ width: `${clamped}%` }}
      />
      <span
        className={`absolute -top-5 text-[10px] font-bold whitespace-nowrap ${labelColor}`}
        style={{ left: `${clamped}%`, transform: 'translateX(-50%)' }}
      >
        {clamped.toFixed(1)}%
      </span>
    </div>
  )
}

export default function SummaryCard() {
  const [summary, setSummary] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setIsLoading(true)
        setError(null)

        // 03_frontend와 동일한 엔드포인트 사용
        const res = await fetch(`${API_BASE}/api/bear-boxes?cycle=${CURRENT_CYCLE}`)
        if (!res.ok) throw new Error(`API ${res.status}`)
        const data = await res.json()

        if (!cancelled) {
          const lineData = data.lineData ?? []
          const boxes = data.boxes ?? []
          const predictions = data.predictions ?? []

          const currentRate = lineData[lineData.length - 1]?.value ?? 0
          const lastBox = boxes[boxes.length - 1]
          const hiRate = lastBox?.Peak_Rate ?? 0
          const loRate = lastBox?.Start_Rate ?? 0
          const nextPredRate = predictions[0]?.Peak_Rate ?? null
          const positionPercent = calcPositionPercent(currentRate, loRate, hiRate)

          setSummary({
            cycleLabel: CURRENT_CYCLE_LABEL,
            currentRate,
            hiRate,
            loRate,
            nextPredRate,
            positionPercent,
            signal: signalFromPercent(positionPercent),
          })
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  /* ── 로딩 상태 ── */
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 p-4 rounded-2xl border border-white/8 bg-chart-panel animate-pulse">
        <div className="h-5 w-32 rounded-md bg-white/10" />
        <div className="h-4 w-48 rounded-md bg-white/8" />
      </div>
    )
  }

  /* ── 에러 상태 ── */
  if (error || !summary) {
    return (
      <div className="flex items-center gap-2 p-3 rounded-xl border border-sell/30 bg-sell/10 text-sell text-sm">
        <span aria-hidden="true">⚠</span>
        <span>요약 데이터를 불러오지 못했습니다</span>
      </div>
    )
  }

  return (
    <section
      className="flex flex-col gap-4 p-4 sm:p-5 rounded-2xl border border-white/8 bg-chart-panel/90 shadow-lg backdrop-blur-sm"
      aria-label="현재 시장 상태 요약"
    >
      {/* 헤더: 사이클 라벨 + 신호 배지 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-hold">
            BTC
          </span>
          <span className="text-lg font-black tracking-tight text-accent">
            {summary.cycleLabel}
          </span>
        </div>
        <SignalBadge signal={summary.signal} size="md" />
      </div>

      {/* 통계 격자 — 모바일 2열, 데스크탑 4열 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-0 sm:divide-x sm:divide-white/8">
        <StatItem label="현재 Rate" value={formatRate(summary.currentRate)} highlight />
        <StatItem label="사이클 고점" value={formatRate(summary.hiRate)} />
        <StatItem label="사이클 저점" value={formatRate(summary.loRate)} />
        <StatItem
          label="다음 예측"
          value={formatRate(summary.nextPredRate)}
          className="text-accent"
        />
      </div>

      {/* 위치 바 */}
      <div className="flex items-center gap-3 pt-2">
        <span className="text-[10px] font-bold text-hold shrink-0">저점</span>
        <PositionBar percent={summary.positionPercent} />
        <span className="text-[10px] font-bold text-hold shrink-0">고점</span>
      </div>

      <p className="text-xs text-hold -mt-1">
        현재가는 사이클 고점 대비{' '}
        <strong className="text-white/70">
          {summary.positionPercent?.toFixed(1)}%
        </strong>{' '}
        위치에 있습니다
      </p>
    </section>
  )
}

function StatItem({ label, value, highlight = false, className = '' }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 sm:py-0 sm:px-3 rounded-xl sm:rounded-none bg-white/3 sm:bg-transparent">
      <span className="text-[10px] font-bold uppercase tracking-widest text-hold">
        {label}
      </span>
      <span
        className={`font-bold tabular-nums ${
          highlight ? 'text-lg text-white' : 'text-sm text-white/60'
        } ${className}`}
      >
        {value}
      </span>
    </div>
  )
}
