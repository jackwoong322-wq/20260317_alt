import React from 'react'
import './ShapForcePlot.css'

const DEFAULT_FEATURES = [
  { name: 'Mayer Multiple', value: '0.84', impact: 0.24, desc: '이평선 이격 과매수/과매도' },
  { name: 'Drawdown Depth (ATH)', value: '-34.2%', impact: 0.18, desc: '전고점 대비 낙폭 지지력' },
  { name: 'Hashrate Growth (30d)', value: '+4.5%', impact: 0.08, desc: '네트워크 기초 해시 성장' },
  { name: 'Difficulty Ribbon Compression', value: '0.04', impact: 0.05, desc: '난이도 수렴을 통한 바닥 확인' },
  { name: 'DXY Correlation (90d)', value: '-0.68', impact: -0.12, desc: '달러 인덱스 역상관 영향' },
]

export default function ShapForcePlot({ features = DEFAULT_FEATURES }) {
  // SHAP 합산값 계산
  const totalPositive = features
    .filter((f) => f.impact > 0)
    .reduce((acc, cur) => acc + cur.impact, 0)
  const totalNegative = features
    .filter((f) => f.impact < 0)
    .reduce((acc, cur) => acc + cur.impact, 0)
  
  const baseValue = 0.5 // 기준 모델 점수
  const predictionValue = Math.max(0, Math.min(1, baseValue + totalPositive + totalNegative))

  return (
    <section className="shap-panel" aria-label="XGBoost 변수 기여도 분석 (SHAP)">
      <div className="shap-header">
        <h3 className="shap-title">XGBoost 변수 기여도 (SHAP)</h3>
        <span className="shap-subtitle">무료 지표 기반 의사결정 기여도</span>
      </div>

      {/* 종합 포스 바 */}
      <div className="shap-force-bar-wrapper">
        <div className="shap-force-labels">
          <span className="text-sell font-bold">Bear (-)</span>
          <span className="text-white font-mono text-xs">기준값 {baseValue.toFixed(2)} → 예측치 {predictionValue.toFixed(2)}</span>
          <span className="text-buy font-bold">Bull (+)</span>
        </div>
        <div className="shap-force-track">
          {/* 음의 영향 영역 */}
          <div
            className="shap-force-segment neg"
            style={{
              width: `${Math.abs(totalNegative) * 100}%`,
              marginRight: 'auto',
            }}
          />
          {/* 양의 영향 영역 */}
          <div
            className="shap-force-segment pos"
            style={{
              width: `${totalPositive * 100}%`,
              marginLeft: 'auto',
            }}
          />
          {/* 예측 마커 */}
          <div
            className="shap-force-marker"
            style={{ left: `${predictionValue * 100}%` }}
            title={`최종 예측치: ${predictionValue.toFixed(2)}`}
          />
        </div>
      </div>

      {/* 개별 변수 목록 */}
      <div className="shap-feature-list">
        {features.map((feature, idx) => {
          const isPositive = feature.impact >= 0
          const pct = Math.abs(feature.impact) * 100
          
          return (
            <div key={idx} className="shap-feature-item">
              <div className="shap-feature-info">
                <span className="shap-feature-name">{feature.name}</span>
                <span className="shap-feature-val">{feature.value}</span>
              </div>
              
              <div className="shap-feature-bar-row">
                <div className="shap-feature-bar-track">
                  <div
                    className={`shap-feature-bar-fill ${isPositive ? 'pos' : 'neg'}`}
                    style={{
                      width: `${pct}%`,
                      marginLeft: isPositive ? '50%' : 'auto',
                      marginRight: isPositive ? 'auto' : '50%',
                    }}
                  />
                </div>
                <span className={`shap-feature-impact ${isPositive ? 'text-buy' : 'text-sell'}`}>
                  {isPositive ? '+' : ''}
                  {feature.impact.toFixed(2)}
                </span>
              </div>
              <span className="shap-feature-desc">{feature.desc}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
