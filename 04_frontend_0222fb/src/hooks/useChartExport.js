/**
 * useChartExport.js — F-08 차트 PNG 내보내기 훅
 *
 * lightweight-charts v4+ takeScreenshot() API 사용
 * 반환된 canvas를 PNG blob으로 변환 후 자동 다운로드
 *
 * @param {React.RefObject} chartRef  lightweight-charts 인스턴스 ref
 * @param {string}          filename  다운로드 파일명 (확장자 없이)
 */
import { useCallback, useState } from 'react'

export function useChartExport(chartRef, filename = 'btc-chart') {
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState(null)

  const exportPng = useCallback(async () => {
    const chart = chartRef.current
    if (!chart) {
      setExportError('차트가 준비되지 않았습니다.')
      return
    }

    setExporting(true)
    setExportError(null)

    try {
      // lightweight-charts v4 API
      const canvas = chart.takeScreenshot()
      if (!canvas) throw new Error('스크린샷 생성 실패')

      // canvas → blob → 다운로드
      canvas.toBlob((blob) => {
        if (!blob) {
          setExportError('이미지 변환 실패')
          setExporting(false)
          return
        }
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${filename}-${new Date().toISOString().slice(0, 10)}.png`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        setExporting(false)
      }, 'image/png')
    } catch (err) {
      setExportError(err.message ?? 'PNG 내보내기 실패')
      setExporting(false)
    }
  }, [chartRef, filename])

  return { exportPng, exporting, exportError }
}
