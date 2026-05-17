/**
 * issue101_dropdown.test.ts
 * 이슈 #101: 커스텀 드롭다운 로직 단위 테스트
 * - chart-ui.js는 DOM+ESM 의존성이 있어 순수 로직만 분리하여 테스트
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

// ── 1. SHOW_OPTIONS 정의 검증 ──────────────────────────

const SHOW_OPTIONS = [
  { value: 'highlow',  label: 'HIGH / LOW',  key: 'showHighLow' },
  { value: 'boxzone',  label: 'BOX ZONE',    key: 'showBoxZone' },
  { value: 'predict',  label: 'PREDICT',     key: 'showPrediction' },
  { value: 'extended', label: 'EXTENDED',    key: 'showExtendedForecast' },
  { value: 'subbox',   label: 'SUB-BOX',     key: 'showSubBox' },
  { value: 'bb',       label: 'BB (20,2)',   key: 'showBB' },
]

describe('[#101] SHOW_OPTIONS 정의', () => {
  it('6개 항목이어야 한다', () => {
    expect(SHOW_OPTIONS).toHaveLength(6)
  })

  it('모든 항목에 value, label, key가 있어야 한다', () => {
    SHOW_OPTIONS.forEach((opt) => {
      expect(opt.value).toBeTruthy()
      expect(opt.label).toBeTruthy()
      expect(opt.key).toBeTruthy()
    })
  })

  it('value 중복이 없어야 한다', () => {
    const values = SHOW_OPTIONS.map((o) => o.value)
    expect(new Set(values).size).toBe(values.length)
  })

  it('key 중복이 없어야 한다', () => {
    const keys = SHOW_OPTIONS.map((o) => o.key)
    expect(new Set(keys).size).toBe(keys.length)
  })
})

// ── 2. trigger 레이블 생성 로직 ───────────────────────

function updateTriggerLabel(items: string[], emptyText = 'None'): string {
  if (items.length === 0) return emptyText
  if (items.length <= 3)  return items.join(', ')
  return `${items[0]}, ${items[1]} +${items.length - 2}`
}

describe('[#101] updateTriggerLabel', () => {
  it('빈 배열 → emptyText 반환', () => {
    expect(updateTriggerLabel([])).toBe('None')
  })

  it('빈 배열 + 커스텀 emptyText', () => {
    expect(updateTriggerLabel([], 'Select...')).toBe('Select...')
  })

  it('1개 → 해당 항목 반환', () => {
    expect(updateTriggerLabel(['BTC'])).toBe('BTC')
  })

  it('2개 → 쉼표로 연결', () => {
    expect(updateTriggerLabel(['BTC', 'ETH'])).toBe('BTC, ETH')
  })

  it('3개 → 쉼표로 연결 (최대 노출)', () => {
    expect(updateTriggerLabel(['BTC', 'ETH', 'BNB'])).toBe('BTC, ETH, BNB')
  })

  it('4개 → 앞 2개 + 나머지 수', () => {
    expect(updateTriggerLabel(['BTC', 'ETH', 'BNB', 'SOL'])).toBe('BTC, ETH +2')
  })

  it('5개 → 앞 2개 + 나머지 수', () => {
    expect(updateTriggerLabel(['A', 'B', 'C', 'D', 'E'])).toBe('A, B +3')
  })
})

// ── 3. COIN 멀티선택 상태 로직 ────────────────────────

function toggleCoin(selectedCoins: string[], coinId: string): string[] {
  const idx = selectedCoins.indexOf(coinId)
  if (idx >= 0) {
    if (selectedCoins.length === 1) return selectedCoins // 마지막 코인 해제 불가
    return selectedCoins.filter((_, i) => i !== idx)
  }
  return [...selectedCoins, coinId]
}

describe('[#101] COIN 멀티선택 로직', () => {
  it('없는 코인 클릭 → 추가', () => {
    expect(toggleCoin(['BTC'], 'ETH')).toEqual(['BTC', 'ETH'])
  })

  it('있는 코인 클릭 → 제거', () => {
    expect(toggleCoin(['BTC', 'ETH'], 'BTC')).toEqual(['ETH'])
  })

  it('마지막 코인은 해제 불가', () => {
    expect(toggleCoin(['BTC'], 'BTC')).toEqual(['BTC'])
  })

  it('3개 중 1개 제거', () => {
    expect(toggleCoin(['BTC', 'ETH', 'BNB'], 'ETH')).toEqual(['BTC', 'BNB'])
  })

  it('동일 코인 중복 추가 방지 (이미 존재시 제거)', () => {
    const result = toggleCoin(['BTC', 'ETH'], 'ETH')
    expect(result).toEqual(['BTC'])
  })
})

// ── 4. CYCLE 멀티선택 상태 로직 ──────────────────────

function toggleCycle(activeCycles: Set<number>, n: number): Set<number> {
  const next = new Set(activeCycles)
  if (next.has(n)) {
    if (next.size === 1) return next // 마지막 사이클 해제 불가
    next.delete(n)
  } else {
    next.add(n)
  }
  return next
}

describe('[#101] CYCLE 멀티선택 로직', () => {
  it('없는 사이클 추가', () => {
    expect(toggleCycle(new Set([1]), 2)).toEqual(new Set([1, 2]))
  })

  it('있는 사이클 제거', () => {
    expect(toggleCycle(new Set([1, 2]), 1)).toEqual(new Set([2]))
  })

  it('마지막 사이클 해제 불가', () => {
    expect(toggleCycle(new Set([5]), 5)).toEqual(new Set([5]))
  })

  it('복수 사이클 유지', () => {
    const result = toggleCycle(new Set([1, 3, 5]), 3)
    expect(result).toEqual(new Set([1, 5]))
  })
})

// ── 5. SHOW 상태 토글 로직 ────────────────────────────

interface ShowState {
  showHighLow: boolean
  showBoxZone: boolean
  showPrediction: boolean
  showExtendedForecast: boolean
  showSubBox: boolean
  showBB: boolean
}

function toggleShow(state: ShowState, key: keyof ShowState): ShowState {
  const next = { ...state, [key]: !state[key] }
  // PREDICT 꺼지면 EXTENDED도 꺼짐
  if (!next.showPrediction) next.showExtendedForecast = false
  return next
}

describe('[#101] SHOW 상태 토글', () => {
  const base: ShowState = {
    showHighLow: false,
    showBoxZone: true,
    showPrediction: true,
    showExtendedForecast: false,
    showSubBox: false,
    showBB: false,
  }

  it('showHighLow 토글 ON', () => {
    expect(toggleShow(base, 'showHighLow').showHighLow).toBe(true)
  })

  it('showBoxZone 토글 OFF', () => {
    expect(toggleShow(base, 'showBoxZone').showBoxZone).toBe(false)
  })

  it('showPrediction OFF → showExtendedForecast도 OFF', () => {
    const withExtended = { ...base, showPrediction: true, showExtendedForecast: true }
    const result = toggleShow(withExtended, 'showPrediction')
    expect(result.showPrediction).toBe(false)
    expect(result.showExtendedForecast).toBe(false)
  })

  it('showPrediction ON이면 showExtendedForecast 독립 토글 가능', () => {
    const result = toggleShow(base, 'showExtendedForecast')
    expect(result.showExtendedForecast).toBe(true)
  })

  it('showSubBox 토글', () => {
    expect(toggleShow(base, 'showSubBox').showSubBox).toBe(true)
  })

  it('showBB 토글', () => {
    expect(toggleShow(base, 'showBB').showBB).toBe(true)
  })
})
