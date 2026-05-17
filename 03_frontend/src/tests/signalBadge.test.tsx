/**
 * signalBadge.test.ts — 03_frontend SignalBadge + positionToSignal 테스트
 *
 * QA 에이전트 작성 | Loop 29
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SignalBadge, { positionToSignal } from '../components/SignalBadge'
import type { Signal } from '../components/SignalBadge'

// ── positionToSignal 로직 검증 ─────────────────────────────────────────

describe('[QA] positionToSignal', () => {
  it('0% → BUY', () => expect(positionToSignal(0)).toBe('BUY'))
  it('29.9% → BUY', () => expect(positionToSignal(29.9)).toBe('BUY'))
  it('30% → HOLD', () => expect(positionToSignal(30)).toBe('HOLD'))
  it('50% → HOLD', () => expect(positionToSignal(50)).toBe('HOLD'))
  it('69.9% → HOLD', () => expect(positionToSignal(69.9)).toBe('HOLD'))
  it('70% → SELL', () => expect(positionToSignal(70)).toBe('SELL'))
  it('100% → SELL', () => expect(positionToSignal(100)).toBe('SELL'))
})

// ── SignalBadge 렌더링 ────────────────────────────────────────────────

describe('[QA] SignalBadge 렌더링', () => {
  it('BUY → ACCUMULATE ZONE 표시', () => {
    render(<SignalBadge signal="BUY" />)
    expect(screen.getByText('ACCUMULATE ZONE')).toBeDefined()
  })

  it('HOLD → HOLD / OBSERVE 표시', () => {
    render(<SignalBadge signal="HOLD" />)
    expect(screen.getByText('HOLD / OBSERVE')).toBeDefined()
  })

  it('SELL → DISTRIBUTION ZONE 표시', () => {
    render(<SignalBadge signal="SELL" />)
    expect(screen.getByText('DISTRIBUTION ZONE')).toBeDefined()
  })

  it('알 수 없는 signal → HOLD 폴백', () => {
    render(<SignalBadge signal={'UNKNOWN' as Signal} />)
    expect(screen.getByText('HOLD / OBSERVE')).toBeDefined()
  })

  it('role="status" 접근성 속성이 있다', () => {
    render(<SignalBadge signal="BUY" />)
    expect(screen.getByRole('status')).toBeDefined()
  })

  it('aria-label이 설정되어 있다', () => {
    render(<SignalBadge signal="BUY" />)
    const badge = screen.getByRole('status')
    expect(badge.getAttribute('aria-label')).toBeTruthy()
  })

  it('BUY 시 아이콘 ▲이 표시된다', () => {
    render(<SignalBadge signal="BUY" />)
    expect(screen.getByText('▲')).toBeDefined()
  })

  it('SELL 시 아이콘 ▼이 표시된다', () => {
    render(<SignalBadge signal="SELL" />)
    expect(screen.getByText('▼')).toBeDefined()
  })
})
