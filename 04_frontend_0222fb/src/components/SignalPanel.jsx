/**
 * SignalPanel.jsx
 * BTC 투자 신호 패널 — ACCUMULATE / WATCH / CAUTION / EXIT
 * GET /api/btc-signal 응답을 받아 현재 투자 신호를 시각화
 */

import { useState, useEffect } from 'react'
import { fetchBtcSignal } from '../lib/api'
import './SignalPanel.css'

const SIGNAL_CONFIG = {
  ACCUMULATE: {
    color: '#00b894',
    bg: 'rgba(0,184,148,0.12)',
    border: 'rgba(0,184,148,0.35)',
    icon: '🟢',
    label: '매수 관찰',
  },
  WATCH: {
    color: '#fdcb6e',
    bg: 'rgba(253,203,110,0.12)',
    border: 'rgba(253,203,110,0.35)',
    icon: '🟡',
    label: '대기',
  },
  CAUTION: {
    color: '#e17055',
    bg: 'rgba(225,112,85,0.12)',
    border: 'rgba(225,112,85,0.35)',
    icon: '🟠',
    label: '주의',
  },
  EXIT: {
    color: '#d63031',
    bg: 'rgba(214,48,49,0.12)',
    border: 'rgba(214,48,49,0.35)',
    icon: '🔴',
    label: '매도 고려',
  },
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100)
  const color =
    pct >= 70 ? '#00b894' :
    pct >= 40 ? '#fdcb6e' :
                '#d63031'

  return (
    <div className="sp-confidence-wrap" aria-label={`신뢰도 ${pct}%`}>
      <div className="sp-confidence-track">
        <div
          className="sp-confidence-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="sp-confidence-label" style={{ color }}>
        {pct}%
      </span>
    </div>
  )
}

function Skeleton() {
  return (
    <div className="sp-skeleton" aria-busy="true" aria-label="신호 로딩 중">
      <div className="sp-sk-line sp-sk-wide" />
      <div className="sp-sk-line sp-sk-narrow" />
      <div className="sp-sk-line sp-sk-mid" />
    </div>
  )
}

export default function SignalPanel({ sandboxData }) {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setIsLoading(true)
        setError(null)
        const result = await fetchBtcSignal()
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    if (sandboxData) {
      setData(sandboxData)
      setIsLoading(false)
    } else {
      load()
    }
    return () => { cancelled = true }
  }, [sandboxData])

  if (isLoading) return <Skeleton />

  if (error || !data) {
    return (
      <div className="sp-error" role="alert">
        <span aria-hidden="true">⚠</span>
        <span>신호 데이터를 불러오지 못했습니다</span>
      </div>
    )
  }

  const signalKey = (data.signal?.signal || 'WATCH').toUpperCase()
  const cfg = SIGNAL_CONFIG[signalKey] || SIGNAL_CONFIG.WATCH
  const phase = data.phase || 'BEAR'
  const cycleNum = data.cycle_number ?? '?'
  const confidence = data.signal?.confidence ?? 0
  const messageKo = data.description?.message_ko || ''
  const stageName = data.description?.stage_name || ''
  const action = data.description?.action || ''
  const cp = data.cycle_position

  return (
    <section
      className="signal-panel"
      style={{
        '--sp-color': cfg.color,
        '--sp-bg': cfg.bg,
        '--sp-border': cfg.border,
      }}
      aria-label="BTC 투자 신호"
    >
      {/* 헤더 행 */}
      <div className="sp-header">
        <div className="sp-meta">
          <span className="sp-phase-label">
            {phase === 'BEAR' ? '하락장' : '상승장'}
          </span>
          <span className="sp-cycle-num">Cycle #{cycleNum}</span>
        </div>

        {/* 신호 뱃지 */}
        <div className="sp-badge">
          <span className="sp-icon" aria-hidden="true">{cfg.icon}</span>
          <span className="sp-signal-text">{signalKey}</span>
          <span className="sp-signal-sub">{cfg.label}</span>
        </div>
      </div>

      {/* 신뢰도 바 */}
      <div className="sp-section">
        <span className="sp-field-label">신뢰도</span>
        <ConfidenceBar value={confidence} />
      </div>

      {/* 단계 + 액션 */}
      {(stageName || action) && (
        <div className="sp-section sp-stage-row">
          {stageName && (
            <span className="sp-stage-name">{stageName}</span>
          )}
          {action && (
            <span className="sp-action">{action}</span>
          )}
        </div>
      )}

      {/* 메시지 */}
      {messageKo && (
        <p className="sp-message">{messageKo}</p>
      )}

      {/* 사이클 위치 */}
      {cp && (
        <div className="sp-position-row">
          <span className="sp-field-label">박스 진행</span>
          <span className="sp-pos-val">
            {cp.completed_boxes} / {cp.total_boxes}
          </span>
          {cp.is_near_target && (
            <span className="sp-near-tag">목표 근접</span>
          )}
        </div>
      )}
    </section>
  )
}
