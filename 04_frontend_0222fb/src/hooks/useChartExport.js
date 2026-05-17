/**
 * useChartExport.js — F-08 차트 PNG 내보내기 훅
 *
 * lightweight-charts v4+ takeScreenshot() API 사용
 * 반환된 canvas를 PNG blob으로 변환 후 자동 다운로드
 *
 * BUG-06 수정: toBlob 콜백이 언마운트 후 실행될 때 state 업데이트 방지
 *
 * @param {React.RefObject} chartRef  lightweight-charts 인스턴스 ref
 * @param {string}          filename  다운로드 파일명 (확장자 없이)
 */
import { useCallback, useState, useRef, useEffect } from 'react'

export function useChartExport(chartRef, filename = 'btc-chart') {
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState(null)
  // BUG-06: 언마운트 후 state 업데이트 방지
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const exportPng = useCallback(async () => {
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
      // lightweight-charts v4 API
      const canvas = chart.takeScreenshot()
      if (!canvas) throw new Error('스크린샷 생성 실패')

      // 파일명 안전화 (경로 조작 방지)
      const safeFilename = String(filename).replace(/[^a-zA-Z0-9\-_]/g, '-').slice(0, 80)

      // canvas → blob → 다운로드
      canvas.toBlob((blob) => {
        if (!mountedRef.current) return  // BUG-06: 언마운트 후 무시
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
        setExporting(false)
      }, 'image/png')
    } catch (err) {
      if (mountedRef.current) {
        setExportError(err.message ?? 'PNG 내보내기 실패')
        setExporting(false)
      }
    }
  }, [chartRef, filename])

  return { exportPng, exporting, exportError }
}
