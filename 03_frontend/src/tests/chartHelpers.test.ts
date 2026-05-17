/**
 * chartHelpers.test.ts — 03_frontend 유틸 함수 유닛 테스트
 *
 * QA 에이전트 작성 | Loop 8
 * 대상: src/utils/chartHelpers.ts
 */
import { describe, it, expect } from 'vitest'
import {
  toDateString,
  calcPositionPercent,
  safeFilename,
  clampTooltipPosition,
  calcDayLabel,
  calcDiffStr,
} from '../utils/chartHelpers'

// ── toDateString ──────────────────────────────────────────────────────

describe('toDateString', () => {
  it('유효한 ISO 문자열에서 YYYY-MM-DD 반환', () => {
    const result = toDateString('2025-06-15T00:00:00Z')
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('null → null 반환', () => {
    expect(toDateString(null)).toBeNull()
  })

  it('undefined → null 반환', () => {
    expect(toDateString(undefined)).toBeNull()
  })

  it('빈 문자열 → null 반환', () => {
    expect(toDateString('')).toBeNull()
  })

  it('숫자 타임스탬프 처리', () => {
    const ts = new Date('2025-01-15').getTime()
    const result = toDateString(ts)
    expect(result).toBeTruthy()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('유효하지 않은 날짜 문자열 → null', () => {
    expect(toDateString('not-a-date')).toBeNull()
  })
})

// ── calcPositionPercent ───────────────────────────────────────────────

describe('calcPositionPercent', () => {
  it('중간값 → 50%', () => {
    expect(calcPositionPercent(50, 0, 100)).toBe(50)
  })

  it('최솟값 → 0%', () => {
    expect(calcPositionPercent(0, 0, 100)).toBe(0)
  })

  it('최댓값 → 100%', () => {
    expect(calcPositionPercent(100, 0, 100)).toBe(100)
  })

  it('범위 초과 → 0~100 클램프', () => {
    expect(calcPositionPercent(-10, 0, 100)).toBe(0)
    expect(calcPositionPercent(150, 0, 100)).toBe(100)
  })

  it('hi <= lo → 0 반환 (ZeroDivision 방지)', () => {
    expect(calcPositionPercent(50, 100, 0)).toBe(0)
    expect(calcPositionPercent(50, 100, 100)).toBe(0)
  })
})

// ── safeFilename ──────────────────────────────────────────────────────

describe('safeFilename', () => {
  it('특수문자를 대시로 치환', () => {
    expect(safeFilename('btc chart 2025')).toBe('btc-chart-2025')
  })

  it('경로 조작 방지', () => {
    expect(safeFilename('../path/traversal')).toBe('---path-traversal')
  })

  it('허용 문자 유지', () => {
    expect(safeFilename('normal-file_name123')).toBe('normal-file_name123')
  })

  it('최대 길이 제한', () => {
    const long = 'a'.repeat(200)
    expect(safeFilename(long, 80).length).toBe(80)
  })
})

// ── clampTooltipPosition ──────────────────────────────────────────────

describe('clampTooltipPosition', () => {
  it('일반 위치 — 오른쪽 offset 적용', () => {
    const { x, y } = clampTooltipPosition(100, 100, 800, 600)
    expect(x).toBe(114)  // 100 + 14
    expect(y).toBe(90)   // 100 - 10
  })

  it('우측 경계 초과 — 왼쪽으로 이동', () => {
    const { x } = clampTooltipPosition(700, 100, 800, 600, 240)
    expect(x).toBeLessThan(700)
  })

  it('하단 경계 초과 — 위로 이동', () => {
    const { y } = clampTooltipPosition(100, 550, 800, 600, 240, 120)
    expect(y).toBeLessThan(550)
  })

  it('상단 음수 방지', () => {
    const { y } = clampTooltipPosition(100, 5, 800, 600, 240, 120)
    expect(y).toBeGreaterThanOrEqual(8)
  })
})

// ── calcDayLabel ──────────────────────────────────────────────────────

describe('calcDayLabel', () => {
  it('유효한 날짜 → "Day N" 형식 반환', () => {
    const result = calcDayLabel('2025-06-15')
    expect(result).toMatch(/^Day \d+$/)
  })

  it('유효하지 않은 값 → 입력값 문자열 반환', () => {
    const result = calcDayLabel('invalid')
    expect(typeof result).toBe('string')
  })
})

// ── calcDiffStr ───────────────────────────────────────────────────────

describe('calcDiffStr', () => {
  it('이전값 없음 → null', () => {
    expect(calcDiffStr(5, null)).toBeNull()
  })

  it('양수 등락 → + 접두사', () => {
    const result = calcDiffStr(5, 3)
    expect(result?.startsWith('+')).toBe(true)
  })

  it('음수 등락 → - 접두사', () => {
    const result = calcDiffStr(3, 5)
    expect(result?.startsWith('-')).toBe(true)
  })

  it('단위 기본값 %', () => {
    const result = calcDiffStr(5, 3)
    expect(result?.endsWith('%')).toBe(true)
  })

  it('커스텀 단위', () => {
    const result = calcDiffStr(5, 3, 'pp')
    expect(result?.endsWith('pp')).toBe(true)
  })
})
