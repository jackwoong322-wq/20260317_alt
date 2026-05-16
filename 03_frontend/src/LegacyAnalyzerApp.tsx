import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import WakingBanner from './components/WakingBanner'
import SummaryCard, { type BearBoxesData } from './components/SummaryCard'

// ── 환경 변수 ────────────────────────────────────────────────────────
const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

// ── Render cold-start 재시도 설정 ────────────────────────────────────
const MAX_RETRIES = 8
const RETRY_INTERVAL_MS = 10_000
const CYCLE_NUMBER = 4  // 기본 사이클 차수

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

// ── 타입 정의 ────────────────────────────────────────────────────────
type DashboardMeta = {
  data_version?: string
  generated_at?: string
  cache_status?: string
}

type DashboardInitialResponse = DashboardMeta & {
  data: unknown
}

// ── 플레이스홀더 검증 ────────────────────────────────────────────────
function assertPlaceholderReplaced(html: string) {
  const remaining = [
    '"__LEGACY_CHART_DATA__"',
    '"__DASHBOARD_META__"',
    '"__DASHBOARD_MANIFEST__"',
    '"__API_BASE_URL__"',
  ].filter((p) => html.includes(p))

  if (remaining.length > 0) {
    throw new Error(`Failed to inject legacy shell placeholders: ${remaining.join(', ')}`)
  }
}

function buildShell(
  html: string,
  manifestResponse: unknown,
  initialResponse: DashboardInitialResponse,
): string {
  const meta: DashboardMeta = {
    data_version: initialResponse.data_version,
    generated_at: initialResponse.generated_at,
    cache_status: initialResponse.cache_status,
  }

  const shellHtml = html
    .replace('"__LEGACY_CHART_DATA__"', JSON.stringify(initialResponse.data))
    .replace('"__DASHBOARD_META__"', JSON.stringify(meta))
    .replace('"__DASHBOARD_MANIFEST__"', JSON.stringify(manifestResponse))
    .replace('"__API_BASE_URL__"', JSON.stringify(BASE_URL))

  assertPlaceholderReplaced(shellHtml)
  return shellHtml
}

// ── 재시도 포함 fetch ─────────────────────────────────────────────────
async function fetchJsonWithRetry<T>(
  path: string,
  onRetry?: (attempt: number, max: number) => void,
): Promise<T> {
  let lastError: Error | null = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const res = await fetch(`${BASE_URL}${path}`)
      if (!res.ok) {
        throw new Error(`Failed to load ${path}: ${res.status} ${res.statusText}`)
      }
      return res.json() as Promise<T>
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err))
      if (attempt === MAX_RETRIES) break
      onRetry?.(attempt + 1, MAX_RETRIES)
      await sleep(RETRY_INTERVAL_MS)
    }
  }

  throw lastError
}

// ── 메인 컴포넌트 ────────────────────────────────────────────────────
export default function LegacyAnalyzerApp() {
  const [srcDoc, setSrcDoc] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryAttempt, setRetryAttempt] = useState(0)

  // SummaryCard용 bear-boxes 데이터 (레거시 API와 별개로 로드)
  const [bearBoxesData, setBearBoxesData] = useState<BearBoxesData | null>(null)

  // 레거시 차트 로드
  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      setRetryAttempt(0)

      const onRetry = (attempt: number, max: number) => {
        if (!cancelled) setRetryAttempt(attempt)
        // 첫 재시도에서 bear-boxes도 같이 시도 (서버 깨어날 때 한꺼번에)
        void loadBearBoxes()
        void loadBearBoxes  // suppress unused warning — called above
      }

      try {
        const [shellRes, manifestResponse, initialResponse] = await Promise.all([
          fetch('/legacy/chart-shell-v2.html'),
          fetchJsonWithRetry<unknown>('/api/dashboard-manifest', onRetry),
          fetchJsonWithRetry<DashboardInitialResponse>('/api/dashboard-initial-data', onRetry),
        ])

        if (!shellRes.ok) throw new Error('Failed to load legacy chart shell')

        const shellHtml = await shellRes.text()
        if (!cancelled) {
          setSrcDoc(buildShell(shellHtml, manifestResponse, initialResponse))
          setRetryAttempt(0)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => { cancelled = true }
  }, [])

  // SummaryCard용 bear-boxes 로드 (레거시 차트와 독립적)
  async function loadBearBoxes() {
    try {
      const data = await fetchJsonWithRetry<BearBoxesData>(`/api/bear-boxes?cycle=${CYCLE_NUMBER}`)
      setBearBoxesData(data)
    } catch {
      // SummaryCard 데이터 실패는 무시 (레거시 차트에 영향 없음)
    }
  }

  useEffect(() => {
    void loadBearBoxes()
  }, [])

  // ── 렌더링 ──────────────────────────────────────────────────────────
  const isWaking = loading && retryAttempt > 0

  return (
    <div style={styles.root}>
      {/* 재부팅 배너 (재시도 중일 때만) */}
      {isWaking && (
        <WakingBanner attempt={retryAttempt} maxRetries={MAX_RETRIES} />
      )}

      {/* 요약 카드 (항상 표시 — 데이터 없으면 skeleton) */}
      <SummaryCard cycleNumber={CYCLE_NUMBER} data={bearBoxesData} />

      {/* 메인 영역: 로딩 / 에러 / 차트 */}
      {loading ? (
        <div style={styles.statusWrap}>
          <div style={styles.statusCard}>
            <div style={styles.statusEyebrow}>ALT/BTC CYCLE ANALYZER</div>
            <div style={styles.statusTitle}>
              {isWaking ? 'Waiting for server restart...' : 'Preparing the chart workspace'}
            </div>
            <div style={styles.statusText}>
              {isWaking
                ? `Render server is waking up. Attempt ${retryAttempt}/${MAX_RETRIES}.`
                : 'Loading cycle data, overlays, and comparison controls.'}
            </div>
          </div>
        </div>
      ) : error ? (
        <div style={styles.statusWrap}>
          <div style={styles.statusCard}>
            <div style={styles.statusEyebrow}>DATA CONNECTION</div>
            <div style={{ ...styles.statusTitle, color: '#ff92aa' }}>Unable to load the analyzer</div>
            <div style={{ ...styles.statusText, color: '#ffcad5' }}>{error}</div>
          </div>
        </div>
      ) : (
        <iframe
          title="ALT/BTC Cycle Analyzer"
          srcDoc={srcDoc}
          style={styles.frame}
        />
      )}
    </div>
  )
}

// ── 스타일 ───────────────────────────────────────────────────────────
const styles: Record<string, CSSProperties> = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#080c14',
    overflow: 'hidden',
  },
  frame: {
    flex: 1,
    width: '100%',
    border: 'none',
    display: 'block',
    background: '#080c14',
    minHeight: 0,
  },
  statusWrap: {
    flex: 1,
    display: 'grid',
    placeItems: 'center',
    background: '#080c14',
    color: '#c8d8f0',
    fontFamily: '"JetBrains Mono", monospace',
  },
  statusCard: {
    width: 'min(460px, calc(100vw - 40px))',
    border: '1px solid #20344f',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)), #0d1725',
    padding: '26px 28px',
    borderRadius: 16,
    boxShadow: '0 24px 64px rgba(0, 0, 0, 0.32)',
  },
  statusEyebrow: {
    marginBottom: 10,
    color: '#6882a7',
    fontSize: '0.76rem',
    fontWeight: 700,
    letterSpacing: '0.24em',
  },
  statusTitle: {
    color: '#f6fbff',
    fontFamily: '"Oxanium", sans-serif',
    fontSize: '1.5rem',
    fontWeight: 700,
    letterSpacing: '0.06em',
  },
  statusText: {
    marginTop: 10,
    color: '#9cb2ce',
    fontSize: '0.98rem',
    lineHeight: 1.6,
  },
}
