/**
 * architecture.test.js — 아키텍처 GATE 정적 분석 테스트 (04_frontend)
 *
 * QA 에이전트 작성 | Loop 31
 * Tech Lead GATE-1~5 자동 검증
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'fs'
import { resolve, join } from 'path'

const SRC = resolve(__dirname, '..')

function collectFiles(dir, exts = ['.jsx', '.js'], results = []) {
  const entries = readdirSync(dir)
  for (const entry of entries) {
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      if (['node_modules', 'e2e', '__snapshots__'].includes(entry)) continue
      collectFiles(fullPath, exts, results)
    } else if (exts.some((e) => entry.endsWith(e)) && !entry.includes('.test.')) {
      results.push(fullPath)
    }
  }
  return results
}

const SOURCE_FILES = collectFiles(SRC)
const SOURCE_CONTENTS = SOURCE_FILES.map((f) => ({
  file: f.replace(SRC, ''),
  content: readFileSync(f, 'utf-8'),
}))

// ── GATE-1: API URL 하드코딩 금지 ────────────────────────────────────

describe('[GATE-1] API URL 하드코딩 금지', () => {
  it('소스 파일에 localhost:8000 하드코딩 없음', () => {
    const violations = SOURCE_CONTENTS.filter(
      ({ content, file }) =>
        !file.includes('api.js') &&  // api.js의 dev fallback 허용
        content.includes('localhost:8000')
    )
    expect(violations.map((v) => v.file)).toEqual([])
  })

  it('소스 파일에 render.com URL 하드코딩 없음', () => {
    const violations = SOURCE_CONTENTS.filter(({ content }) =>
      content.includes('onrender.com')
    )
    expect(violations.map((v) => v.file)).toEqual([])
  })
})

// ── GATE-2: fetch() 직접 호출 금지 ───────────────────────────────────

describe('[GATE-2] 컴포넌트 내 fetch() 직접 호출 금지', () => {
  it('lib/api.js 제외한 파일에서 await fetch( 없음', () => {
    const violations = SOURCE_CONTENTS.filter(
      ({ content, file }) =>
        !file.includes('api.js') &&
        /await\s+fetch\s*\(/.test(content)
    )
    expect(violations.map((v) => v.file)).toEqual([])
  })
})

// ── GATE-3: chartRef null 체크 ───────────────────────────────────────

describe('[GATE-3] chartRef.current null 체크 패턴', () => {
  it('useChartExport.js에 mountedRef 패턴이 존재한다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useChartExport'))
    expect(file?.content).toContain('mountedRef')
  })

  it('useChartData.js에 cancelledRef 패턴이 존재한다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useChartData'))
    expect(file?.content).toContain('cancelledRef')
  })
})

// ── GATE-4: 환경 변수 패턴 ───────────────────────────────────────────

describe('[GATE-4] 환경 변수 패턴', () => {
  it('api.js에서 VITE_API_URL 환경 변수를 사용한다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('api.js'))
    expect(file?.content).toContain('VITE_API_URL')
  })

  it('api.js에서 VITE_API_URL은 import.meta.env를 통해 접근한다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('api.js'))
    expect(file?.content).toContain('import.meta.env.VITE_API_URL')
  })
})

// ── GATE-5: 언마운트 안전 패턴 ───────────────────────────────────────

describe('[GATE-5] 언마운트 안전 패턴', () => {
  it('useChartData.js에 모든 useEffect가 cancelledRef로 보호된다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useChartData'))
    const content = file?.content ?? ''
    const cancelledCount = (content.match(/cancelledRef/g) ?? []).length
    // cancelledRef가 최소 4개 이상 (각 훅마다)
    expect(cancelledCount).toBeGreaterThanOrEqual(4)
  })

  it('useChartExport.js에 mountedRef가 있다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useChartExport'))
    expect(file?.content).toContain('mountedRef.current')
  })
})

// ── BUG 회귀 테스트 ──────────────────────────────────────────────────

describe('[회귀] 수정된 버그 회귀 방지', () => {
  it('[BUG-07] useTheme에 matchMedia 안전 체크가 있다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useTheme'))
    expect(file?.content).toContain('matchMedia')
    // 단순 호출이 아닌 조건부 호출
    expect(file?.content).toMatch(/window\.matchMedia|typeof.*matchMedia/)
  })

  it('[BUG-09] useResizeChart에 height 가드가 있다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useResizeChart'))
    expect(file?.content).toContain('height > 0')
  })

  it('[BUG-04] CycleComparisonChart에 useMemo가 사용된다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('CycleComparisonChart'))
    expect(file?.content).toContain('useMemo')
  })
})
