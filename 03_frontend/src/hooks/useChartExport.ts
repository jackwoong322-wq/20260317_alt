/**
 * useChartExport.ts — F-08 차트 PNG 내보내기 훅 (TypeScript)
 *
 * 04_frontend useChartExport.js 기반 TypeScript 포팅
 * lightweight-charts v4+ takeScreenshot() API 사용
 *
 * BUG-06 수정: mountedRef로 언마운트 후 state 업데이트 방지
 */
import { useCallback, useState, useRef, useEffect } from 'react'
import type { IChartApi } from 'lightweight-charts'

export interface UseChartExportReturn {
  exportPng: () => Promise<void>
  exporting: boolean
  exportError: string | null
}

export function useChartExport(
  chartRef: React.RefObject<IChartApi | null>,
  filename: string = 'btc-chart',
): UseChartExportReturn {
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const exportPng = useCallback(async (): Promise<void> => {
    const chart = chartRef.current
    if (!chart) {
      if (mountedRef.current) setExportError('차트가 준비되지 않았습니다.')
      return
    }

    if (mountedRef.current) {
      setExporting(true)
      setExportError(null)
    }

    try {
      const canvas = chart.takeScreenshot()
      if (!canvas) throw new Error('스크린샷 생성 실패')

      // 파일명 안전화 (경로 조작 방지)
      const safeFilename = String(filename)
        .replace(/[^a-zA-Z0-9\-_]/g, '-')
        .slice(0, 80)

      canvas.toBlob((blob) => {
        if (!mountedRef.current) return
        if (!blob) {
          setExportError('이미지 변환 실패')
          setExporting(false)
          return
        }
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${safeFilename}-${new Date().toISOString().slice(0, 10)}.png`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        if (mountedRef.current) setExporting(false)
      }, 'image/png')
    } catch (err) {
      if (mountedRef.current) {
        setExportError(err instanceof Error ? err.message : 'PNG 내보내기 실패')
        setExporting(false)
      }
    }
  }, [chartRef, filename])

  return { exportPng, exporting, exportError }
}
