import { useState, useEffect } from 'react'
import '../styles/Chart.css'

export function ChartLoadingState({ title, message }) {
  return (
    <div className="loading-container" role="status" aria-live="polite">
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  )
}

export function ChartErrorState({ title, message }) {
  return (
    <div className="error-container" role="alert">
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  )
}

/**
 * ChartWakingState
 * Render cold-start 재시도 중 표시하는 전용 UI
 *
 * Props:
 *   attempt    {number}  현재 재시도 횟수 (1~)
 *   maxRetries {number}  최대 재시도 횟수
 */
export function ChartWakingState({ attempt, maxRetries }) {
  // 다음 재시도까지 남은 초 카운트다운 (10초)
  const [countdown, setCountdown] = useState(10)

  useEffect(() => {
    setCountdown(10)
    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(timer)
          return 0
        }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [attempt])  // attempt가 바뀔 때마다 카운트다운 리셋

  const progressPct = Math.round((attempt / maxRetries) * 100)

  return (
    <div className="waking-container" role="status" aria-live="polite" aria-label="서버 재부팅 중">
      {/* 스피너 */}
      <div className="waking-spinner" aria-hidden="true">
        <div className="waking-spinner-ring" />
      </div>

      <div className="waking-text">
        <strong className="waking-title">🚀 서버 재부팅 중...</strong>
        <span className="waking-desc">
          Render 서버가 잠시 Sleep 상태였습니다.
          <br />
          자동으로 재부팅되면 차트가 표시됩니다.
        </span>
      </div>

      {/* 재시도 진행 바 */}
      <div className="waking-progress-wrap" aria-label={`재시도 ${attempt}/${maxRetries}`}>
        <div className="waking-progress-bar" style={{ width: `${progressPct}%` }} />
      </div>

      <div className="waking-meta">
        <span>재시도 {attempt} / {maxRetries}</span>
        <span className="waking-countdown">
          {countdown > 0 ? `다음 시도까지 ${countdown}초` : '재시도 중...'}
        </span>
      </div>
    </div>
  )
}
