/*
 * Chart data hooks
 *
 * All data shaping and heavy calculation are handled by the backend.
 * These hooks are responsible only for fetching API responses and
 * exposing stable loading, error, retryInfo, and data state to the UI.
 *
 * retryInfo: { attempt, maxRetries } | null
 *   - null → 정상 로딩 중 (또는 성공)
 *   - { attempt, maxRetries } → Render cold-start 재시도 중
 */
import { useState, useEffect } from 'react'
import {
  fetchCycleComparison,
  fetchBearBoxes,
  fetchBullBoxes,
  fetchOhlcvData,
} from '../lib/api'

// ── 공통 재시도 콜백 팩토리 ─────────────────────────────────────────
function makeRetryCallback(setRetryInfo) {
  return (attempt, maxRetries) => {
    setRetryInfo({ attempt, maxRetries })
  }
}

export function useCycleComparisonData() {
  const [series, setSeries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryInfo, setRetryInfo] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      try {
        setLoading(true)
        setRetryInfo(null)
        const result = await fetchCycleComparison(makeRetryCallback(setRetryInfo))
        if (!cancelled) {
          setSeries(result.series || [])
          setError(null)
          setRetryInfo(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadData()
    return () => { cancelled = true }
  }, [])

  return { series, loading, error, retryInfo }
}

export function useBearBoxData(cycleNumber = 4) {
  const [lineData, setLineData] = useState([])
  const [boxes, setBoxes] = useState([])
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cycleInfo, setCycleInfo] = useState({ startDate: '', endDate: '' })
  const [config, setConfig] = useState({})
  const [retryInfo, setRetryInfo] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      try {
        setLoading(true)
        setRetryInfo(null)
        const result = await fetchBearBoxes(cycleNumber, makeRetryCallback(setRetryInfo))
        if (!cancelled) {
          setLineData(result.lineData || [])
          setBoxes(result.boxes || [])
          setPredictions(result.predictions || [])
          setCycleInfo(result.cycleInfo || { startDate: '', endDate: '' })
          setConfig(result.config || {})
          setError(null)
          setRetryInfo(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadData()
    return () => { cancelled = true }
  }, [cycleNumber])

  return { lineData, boxes, predictions, loading, error, cycleInfo, config, retryInfo }
}

export function useBullBoxData(cycleNumber = 3) {
  const [lineData, setLineData] = useState([])
  const [boxes, setBoxes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cycleInfo, setCycleInfo] = useState({ startDate: '', endDate: '', maxDays: 0 })
  const [config, setConfig] = useState({})
  const [retryInfo, setRetryInfo] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      try {
        setLoading(true)
        setRetryInfo(null)
        const result = await fetchBullBoxes(cycleNumber, makeRetryCallback(setRetryInfo))
        if (!cancelled) {
          setLineData(result.lineData || [])
          setBoxes(result.boxes || [])
          setCycleInfo(result.cycleInfo || { startDate: '', endDate: '', maxDays: 0 })
          setConfig(result.config || {})
          setError(null)
          setRetryInfo(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadData()
    return () => { cancelled = true }
  }, [cycleNumber])

  return { lineData, boxes, loading, error, cycleInfo, config, retryInfo }
}

export function useOhlcvData() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryInfo, setRetryInfo] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      try {
        setLoading(true)
        setRetryInfo(null)
        const result = await fetchOhlcvData(makeRetryCallback(setRetryInfo))
        if (!cancelled) {
          setData(result.data || [])
          setError(null)
          setRetryInfo(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadData()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error, retryInfo }
}
