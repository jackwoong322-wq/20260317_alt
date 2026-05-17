/**
 * architecture.test.ts — 03_frontend 아키텍처 GATE 자동화 (TypeScript)
 *
 * QA 에이전트 작성 | Loop 32
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'fs'
import { resolve, join } from 'path'

const SRC = resolve(__dirname, '..')

function collectFiles(dir: string, exts: string[] = ['.tsx', '.ts'], results: string[] = []): string[] {
  const entries = readdirSync(dir)
  for (const entry of entries) {
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      if (['node_modules', '__snapshots__'].includes(entry)) continue
      collectFiles(fullPath, exts, results)
    } else if (exts.some((e) => entry.endsWith(e)) && !entry.includes('.test.') && !entry.includes('setup')) {
      results.push(fullPath)
    }
  }
  return results
}

const SOURCE_FILES = collectFiles(SRC)
const SOURCE_CONTENTS = SOURCE_FILES.map((f) => ({
  file: f.replace(SRC, '').replace(/\\/g, '/'),
  content: readFileSync(f, 'utf-8'),
}))

// ── GATE-1: API URL 하드코딩 금지 ─────────────────────────────────────

describe('[GATE-1] API URL 하드코딩 금지 (03_frontend)', () => {
  it('소스 파일에 onrender.com URL 없음', () => {
    const violations = SOURCE_CONTENTS.filter(({ content }) =>
      content.includes('onrender.com')
    )
    expect(violations.map((v) => v.file)).toEqual([])
  })

  it('LegacyAnalyzerApp.tsx는 VITE_API_URL 환경변수를 사용한다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('LegacyAnalyzerApp'))
    expect(file?.content).toContain('VITE_API_URL')
  })
})

// ── GATE-4: TypeScript any 금지 ───────────────────────────────────────

describe('[GATE-4] TypeScript any 사용 금지 (03_frontend 신규 파일)', () => {
  const NEW_FILES = [
    'ChartTooltip.tsx',
    'ChartSkeleton.tsx',
    'useChartExport.ts',
    'useTheme.ts',
    'chartHelpers.ts',
  ]

  NEW_FILES.forEach((filename) => {
    it(`${filename}에 ": any" 패턴 없음`, () => {
      const file = SOURCE_CONTENTS.find((f) => f.file.includes(filename))
      if (!file) return  // 파일 없으면 통과
      expect(file.content).not.toContain(': any')
    })
  })

  NEW_FILES.forEach((filename) => {
    it(`${filename}에 "as any" 패턴 없음`, () => {
      const file = SOURCE_CONTENTS.find((f) => f.file.includes(filename))
      if (!file) return
      // 테스트 파일 내 예외 허용, 소스 파일만 검사
      expect(file.content).not.toContain('as any')
    })
  })
})

// ── GATE-5: 언마운트 안전 패턴 ────────────────────────────────────────

describe('[GATE-5] 언마운트 안전 패턴 (03_frontend)', () => {
  it('useChartExport.ts에 mountedRef 패턴이 존재한다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useChartExport'))
    expect(file?.content).toContain('mountedRef')
  })
})

// ── 신규 파일 존재 확인 ───────────────────────────────────────────────

describe('[포팅 완료] 신규 파일 존재 검증', () => {
  const EXPECTED_FILES = [
    'components/ChartTooltip.tsx',
    'components/ChartSkeleton.tsx',
    'hooks/useChartExport.ts',
    'hooks/useTheme.ts',
    'utils/chartHelpers.ts',
  ]

  EXPECTED_FILES.forEach((expectedPath) => {
    it(`${expectedPath}가 생성되었다`, () => {
      const found = SOURCE_FILES.some((f) => f.replace(/\\/g, '/').includes(expectedPath))
      expect(found).toBe(true)
    })
  })
})

// ── BUG 회귀 방지 ────────────────────────────────────────────────────

describe('[회귀] 03_frontend BUG 패턴 방지', () => {
  it('[BUG-10] ChartSkeleton에 aria-label 없고 aria-live 있다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('ChartSkeleton'))
    const content = file?.content ?? ''
    expect(content).toContain('aria-live')
    expect(content).not.toContain('aria-label="차트 데이터를 불러오는 중')
  })

  it('[BUG-07] useTheme에 matchMedia 안전 체크 있다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useTheme'))
    expect(file?.content).toContain('matchMedia')
    expect(file?.content).toContain('typeof window')
  })

  it('[BUG-06] useChartExport에 mountedRef.current 체크 있다', () => {
    const file = SOURCE_CONTENTS.find((f) => f.file.includes('useChartExport'))
    expect(file?.content).toContain('mountedRef.current')
  })
})
