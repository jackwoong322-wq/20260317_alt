import { useState, useEffect, useRef, useCallback } from 'react'
import { createChart } from 'lightweight-charts'
import { useCycleComparisonData } from '../hooks/useChartData'
import { useChartTooltip } from '../hooks/useChartTooltip'
import { useChartExport } from '../hooks/useChartExport'
import { CHART_THEME, COLORS, COLOR_NAMES } from '../utils/chartConstants'
import { useResizeChart } from '../hooks/useResizeChart'
import { ChartErrorState, ChartLoadingState, ChartWakingState } from './ChartStatus'
import ChartTooltip from './ChartTooltip'
import '../styles/Chart.css'

function dayToDateString(day) {
  const base = new Date(2000, 0, 1)
  const target = new Date(base.getTime() + day * 86400000)
  return `${target.getFullYear()}-${String(target.getMonth() + 1).padStart(2, '0')}-${String(target.getDate()).padStart(2, '0')}`
}

export default function CycleComparisonChart({ onHeaderContent }) {
  const { series, loading, error, retryInfo } = useCycleComparisonData()
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const [hiddenSeries, setHiddenSeries] = useState(new Set())

  // 시리즈 ref 배열 — 툴팁 데이터 추출에 사용
  const seriesRefsRef = useRef([])

  // F-08: PNG 내보내기
  const { exportPng, exporting } = useChartExport(chartRef, 'btc-cycle-comparison')

  const resizeLayoutKey = !loading && !error && series.length > 0 ? series.length : 0

  useResizeChart(containerRef, [chartRef], {
    watchHeight: true,
    layoutKey: resizeLayoutKey,
  })

  // ── 툴팁 훅 통합 ────────────────────────────────────────────────
  // useMemo: seriesList가 렌더마다 재생성되면 handleCrosshairMove가 무한 재구독됨 (BUG-04)
  const seriesListForTooltip = useMemo(
    () =>
      series
        .map((item, idx) => ({
          name: item.name,
          color: COLORS[idx % COLORS.length],
          seriesRef: seriesRefsRef.current[idx] ?? { current: null },
        }))
        .filter((_, idx) => !hiddenSeries.has(series[idx]?.name)),
    [series, hiddenSeries]
  )

  const { tooltipState } = useChartTooltip(chartRef, seriesListForTooltip, containerRef)

  const toggleSeries = (name) => {
    setHiddenSeries((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  useEffect(() => {
    if (!onHeaderContent || series.length === 0) return

    onHeaderContent(
      <>
        <span className="header-slot-title">Bitcoin Cycles Comparison</span>
        <span className="header-slot-sub">Days since peak</span>
        {series.map((item, idx) => (
          <div
            key={item.name}
            className={`header-stat-card ${hiddenSeries.has(item.name) ? 'inactive' : ''}`}
            onClick={() => toggleSeries(item.name)}
          >
            <span className={`header-stat-label tone-${COLOR_NAMES[idx % COLOR_NAMES.length]}`}>
              C{idx + 1}: {item.startDate}
            </span>
            <span className="header-stat-value">
              <span>{item.minRate.toFixed(1)}%</span>
              <span>{item.dayCount}d</span>
            </span>
          </div>
        ))}
      </>
    )
  }, [series, hiddenSeries, onHeaderContent])

  useEffect(() => {
    return () => {
      if (onHeaderContent) onHeaderContent(null)
    }
  }, [onHeaderContent])

  useEffect(() => {
    if (!containerRef.current || series.length === 0) return

    try {
      chartRef.current?.remove()
    } catch (_) {}
    chartRef.current = null
    seriesRefsRef.current = []

    const chart = createChart(containerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: CHART_THEME.textMuted },
      grid: {
        vertLines: { color: CHART_THEME.grid, style: 1 },
        horzLines: { color: CHART_THEME.grid, style: 1 },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: CHART_THEME.accent, width: 1, style: 3, labelBackgroundColor: CHART_THEME.crosshairLabel },
        horzLine: { color: CHART_THEME.accent, width: 1, style: 3, labelBackgroundColor: CHART_THEME.crosshairLabel },
      },
      rightPriceScale: { borderColor: CHART_THEME.border, textColor: CHART_THEME.textMuted },
      timeScale: {
        borderColor: CHART_THEME.border,
        textColor: CHART_THEME.textMuted,
        timeVisible: false,
        tickMarkFormatter: (time) => {
          const diff = Math.round((new Date(time) - new Date(2000, 0, 1)) / 86400000)
          return `${diff}d`
        },
      },
      localization: {
        timeFormatter: (time) => {
          const diff = Math.round((new Date(time) - new Date(2000, 0, 1)) / 86400000)
          return `Day ${diff}`
        },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
      width: containerRef.current.clientWidth || 360,
      height: containerRef.current.clientHeight || 400,
    })
    chartRef.current = chart

    ;[100, 50, 25].forEach((value, index) => {
      const baselineSeries = chart.addLineSeries({
        color: index === 0 ? CHART_THEME.textSoft : 'rgba(148, 163, 184, 0.28)',
        lineWidth: index === 0 ? 2 : 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
      baselineSeries.setData([
        { time: dayToDateString(0), value },
        { time: dayToDateString(1500), value },
      ])
    })

    series.forEach((item, idx) => {
      if (hiddenSeries.has(item.name)) return
      const color = COLORS[idx % COLORS.length]
      const lineSeries = chart.addLineSeries({
        color,
        lineWidth: 2.5,
        title: item.name,
      })
      lineSeries.setData(item.data.map((point) => ({ time: dayToDateString(point.x), value: point.y })))
      lineSeries.createPriceLine({
        price: item.minRate,
        color,
        lineWidth: 1.5,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `C${idx + 1} Min (${item.minRate.toFixed(1)}%)`,
      })
      // 시리즈 ref 저장 (툴팁 데이터 추출용)
      seriesRefsRef.current[idx] = { current: lineSeries }
    })

    chart.timeScale().setVisibleRange({
      from: dayToDateString(0),
      to: dayToDateString(900),
    })

    return () => {
      try {
        chartRef.current?.remove()
      } catch (_) {}
      chartRef.current = null
      seriesRefsRef.current = []
    }
  }, [series, hiddenSeries])

  if (loading) {
    const inner = retryInfo
      ? <ChartWakingState attempt={retryInfo.attempt} maxRetries={retryInfo.maxRetries} />
      : <ChartLoadingState title="데이터를 불러오는 중입니다..." message="사이클 비교 구간과 하락률 데이터를 준비하고 있습니다." />
    return (
      <div className="chart-page">
        <div className="chart-container">
          <div className="chart-wrapper">{inner}</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="chart-page">
        <div className="chart-container">
          <div className="chart-wrapper">
            <ChartErrorState
              title="사이클 비교 데이터를 불러오지 못했습니다."
              message={error}
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chart-page">
      <div className="chart-container">
        {/* chart-wrapper에 position:relative 필수 — 툴팁 absolute 기준점 */}
        <div className="chart-wrapper" style={{ position: 'relative' }}>
          <div className="chart-title-strip">
            <span className="chart-title-strip-kicker">Cycle Comparison</span>
            <h2 className="chart-title-strip-heading">비트코인 사이클 하락률 비교</h2>
            <p className="chart-title-strip-copy">
              각 사이클의 고점 이후 낙폭과 회복 흐름을 같은 축에서 겹쳐 유사 구간을 빠르게 읽습니다.
            </p>
          </div>

          {/* 차트 컨테이너 — position:relative (툴팁 기준점) */}
          <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <div ref={containerRef} className="chart-area chart-area-compact" />
            {/* HTML 오버레이 툴팁 */}
            <ChartTooltip tooltipState={tooltipState} />
          </div>

          <div className="chart-footer chart-footer-row">
            <span>Data source: Supabase BTC/USDT OHLCV</span>
            {/* F-08: PNG 내보내기 버튼 */}
            <button
              className="chart-export-btn"
              onClick={exportPng}
              disabled={exporting}
              title="차트를 PNG로 저장"
              aria-label="차트 PNG 내보내기"
            >
              {exporting ? '저장 중...' : '📥 PNG'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
