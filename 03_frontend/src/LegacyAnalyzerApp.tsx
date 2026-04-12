import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

function buildShell(html: string, data: unknown) {
  return html.replace('__CHART_DATA__', JSON.stringify(data))
}

export default function LegacyAnalyzerApp() {
  const [srcDoc, setSrcDoc] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      try {
        const [shellRes, dataRes] = await Promise.all([
          fetch('/legacy/chart-shell-v2.html'),
          fetch(`${BASE_URL}/api/dashboard-data`),
        ])

        if (!shellRes.ok) {
          throw new Error('Failed to load legacy chart shell')
        }
        if (!dataRes.ok) {
          throw new Error('Failed to load dashboard data')
        }

        const [shellHtml, data] = await Promise.all([shellRes.text(), dataRes.json()])
        if (!cancelled) {
          setSrcDoc(buildShell(shellHtml, data))
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div style={styles.statusWrap}>
        <div style={styles.statusCard}>
          <div style={styles.statusEyebrow}>ALT/BTC CYCLE ANALYZER</div>
          <div style={styles.statusTitle}>Preparing the chart workspace</div>
          <div style={styles.statusText}>Loading cycle data, overlays, and comparison controls.</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={styles.statusWrap}>
        <div style={styles.statusCard}>
          <div style={styles.statusEyebrow}>DATA CONNECTION</div>
          <div style={{ ...styles.statusTitle, color: '#ff92aa' }}>Unable to load the analyzer</div>
          <div style={{ ...styles.statusText, color: '#ffcad5' }}>{error}</div>
        </div>
      </div>
    )
  }

  return (
    <iframe
      title="ALT/BTC Cycle Analyzer"
      srcDoc={srcDoc}
      style={styles.frame}
      sandbox="allow-scripts allow-same-origin"
    />
  )
}

const styles: Record<string, CSSProperties> = {
  frame: {
    width: '100%',
    height: '100vh',
    border: 'none',
    display: 'block',
    background: '#080c14',
  },
  statusWrap: {
    minHeight: '100vh',
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
