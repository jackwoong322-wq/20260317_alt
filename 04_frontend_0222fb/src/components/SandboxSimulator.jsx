import React, { useState } from 'react'
import './SandboxSimulator.css'

export default function SandboxSimulator({ onSimulate, onReset }) {
  const [isActive, setIsActive] = useState(false)
  const [price, setPrice] = useState(65000)
  const [mayer, setMayer] = useState(1.1)
  const [drawdown, setDrawdown] = useState(25) // percent from ATH
  const [dxy, setDxy] = useState(102)

  const handleToggle = () => {
    const nextActive = !isActive
    setIsActive(nextActive)
    if (!nextActive) {
      onReset()
    } else {
      triggerSimulation(price, mayer, drawdown, dxy)
    }
  }

  const triggerSimulation = (p, m, d, dx) => {
    // 신호 판정 공식 모의 적용 (CMS 및 기획 로직 기준)
    let predictedPrice = p * 1.15
    let calculatedSignal = 'WATCH'
    let confidence = 0.5
    let stageName = 'Stage 2: 관망 국면'
    let action = '일부 현금 확보 및 포지션 관망'
    let messageKo = '시장 변동성 완화 속에서 달러 강세 압력이 존재합니다.'

    if (m < 0.6 || d > 60) {
      calculatedSignal = 'ACCUMULATE'
      confidence = 0.88
      stageName = 'Stage 4: 최대 분할 매수 구간'
      action = '적극 비중 확대'
      messageKo = '역사적 바닥 구간 진입 및 메이어 멀티플이 과매도 신호를 나타냅니다.'
    } else if (m > 2.2 || d < 5) {
      calculatedSignal = 'EXIT'
      confidence = 0.92
      stageName = 'Stage 4: 과열 국면 매도 준비'
      action = '포지션 분할 종료'
      messageKo = '메이어 멀티플 상 위험 구간이며 전고점 저항에 직면했습니다.'
    } else if (m > 1.6) {
      calculatedSignal = 'CAUTION'
      confidence = 0.72
      stageName = 'Stage 3: 일부 수익 실현'
      action = '점진적 비중 축소'
      messageKo = '상승 모멘텀 둔화 가능성 및 가격 이격 리스크가 존재합니다.'
    }

    onSimulate({
      isActive: true,
      currentPrice: p,
      highPrice: p * (1 + d / 100),
      lowPrice: p * 0.5,
      positionPercent: 100 - d,
      signal: calculatedSignal,
      nextPredictedPrice: predictedPrice,
      confidence,
      description: {
        stage: 2,
        stage_name: stageName,
        signal: calculatedSignal,
        action,
        message_ko: messageKo,
      },
    })
  }

  const handleApply = () => {
    if (!isActive) return
    triggerSimulation(price, mayer, drawdown, dxy)
  }

  return (
    <section className="sandbox-panel" aria-label="투자 신호 샌드박스 시뮬레이터">
      <div className="sandbox-header">
        <h3 className="sandbox-title">투자 신호 샌드박스</h3>
        <label className="sandbox-toggle">
          <input
            type="checkbox"
            checked={isActive}
            onChange={handleToggle}
            aria-label="샌드박스 모드 활성화"
          />
          <span className="sandbox-toggle-slider" />
        </label>
      </div>

      <div className={`sandbox-body ${isActive ? 'active' : 'inactive'}`}>
        {/* 가상 가격 입력 */}
        <div className="sandbox-control">
          <label htmlFor="sb-price">가상 현재가 ($)</label>
          <input
            id="sb-price"
            type="number"
            value={price}
            disabled={!isActive}
            onChange={(e) => setPrice(Number(e.target.value))}
          />
        </div>

        {/* 메이어 멀티플 슬라이더 */}
        <div className="sandbox-control">
          <div className="sandbox-control-header">
            <label htmlFor="sb-mayer">Mayer Multiple</label>
            <span className="sandbox-control-val">{mayer.toFixed(2)}</span>
          </div>
          <input
            id="sb-mayer"
            type="range"
            min="0.4"
            max="3.0"
            step="0.05"
            value={mayer}
            disabled={!isActive}
            onChange={(e) => setMayer(Number(e.target.value))}
          />
        </div>

        {/* 낙폭 슬라이더 */}
        <div className="sandbox-control">
          <div className="sandbox-control-header">
            <label htmlFor="sb-drawdown">고점 대비 낙폭 (%)</label>
            <span className="sandbox-control-val">{drawdown}%</span>
          </div>
          <input
            id="sb-drawdown"
            type="range"
            min="0"
            max="90"
            step="1"
            value={drawdown}
            disabled={!isActive}
            onChange={(e) => setDrawdown(Number(e.target.value))}
          />
        </div>

        {/* 달러 인덱스 슬라이더 */}
        <div className="sandbox-control">
          <div className="sandbox-control-header">
            <label htmlFor="sb-dxy">달러 인덱스 (DXY)</label>
            <span className="sandbox-control-val">{dxy}</span>
          </div>
          <input
            id="sb-dxy"
            type="range"
            min="90"
            max="120"
            step="0.5"
            value={dxy}
            disabled={!isActive}
            onChange={(e) => setDxy(Number(e.target.value))}
          />
        </div>

        <button
          type="button"
          className="sandbox-btn"
          disabled={!isActive}
          onClick={handleApply}
        >
          시나리오 적용
        </button>
      </div>
    </section>
  )
}
