import { useEffect, useState } from 'react'
import { fetchChartData, fetchPredictions } from '../api/client'

export function useChartData(coinId: string | null) {
  const [ohlcv, setOhlcv]           = useState<any[]>([])
  const [boxes, setBoxes]           = useState<any[]>([])
  const [predictions, setPredictions] = useState<any>(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState<string | null>(null)

  useEffect(() => {
    if (!coinId) return
    setLoading(true)
    setError(null)

    Promise.all([fetchChartData(coinId), fetchPredictions(coinId).catch(() => null)])
      .then(([chart, preds]) => {
        setOhlcv(chart.ohlcv)
        setBoxes(chart.boxes)
        setPredictions(preds)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [coinId])

  return { ohlcv, boxes, predictions, loading, error }
}
