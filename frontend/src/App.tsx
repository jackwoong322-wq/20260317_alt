import { useState } from 'react'
import { CoinSelector } from './components/CoinSelector'
import { CryptoChart } from './components/CryptoChart'
import { useChartData } from './hooks/useChartData'

export default function App() {
  const [coinId, setCoinId] = useState<string | null>(null)
  const { ohlcv, boxes, predictions, loading, error } = useChartData(coinId)

  return (
    <div style={{ background: '#0f0f0f', minHeight: '100vh', color: '#fff', padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>CryptoChart</h2>
        <CoinSelector selected={coinId} onChange={setCoinId} />
      </div>

      {loading && <p>로딩 중...</p>}
      {error   && <p style={{ color: '#f66' }}>{error}</p>}

      {coinId && !loading && (
        <CryptoChart ohlcv={ohlcv} boxes={boxes} predictions={predictions} />
      )}
    </div>
  )
}
