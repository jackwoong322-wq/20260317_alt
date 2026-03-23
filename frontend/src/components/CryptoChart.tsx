import { useEffect, useRef } from 'react'
import { createChart, IChartApi } from 'lightweight-charts'

interface Props {
  ohlcv: any[]
  boxes: any[]
  predictions: any
}

export function CryptoChart({ ohlcv, boxes, predictions }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef     = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    chartRef.current = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 500,
      layout: { background: { color: '#0f0f0f' }, textColor: '#ccc' },
      grid: { vertLines: { color: '#222' }, horzLines: { color: '#222' } },
    })
    return () => { chartRef.current?.remove() }
  }, [])

  useEffect(() => {
    if (!chartRef.current || !ohlcv.length) return
    const series = chartRef.current.addCandlestickSeries()
    series.setData(
      ohlcv.map(d => ({
        time: d.date,
        open: d.open, high: d.high, low: d.low, close: d.close,
      }))
    )
  }, [ohlcv])

  return <div ref={containerRef} style={{ width: '100%' }} />
}
