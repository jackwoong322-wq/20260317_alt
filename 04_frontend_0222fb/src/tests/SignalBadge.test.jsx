/**
 * SignalBadge.test.jsx
 * BUY / HOLD / SELL 세 가지 신호에 대한 렌더링 무결성 테스트
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SignalBadge from '../components/SignalBadge'

describe('SignalBadge', () => {
  it('BUY 신호: 초록색 클래스 + ▲ 아이콘 + 매수 구간 텍스트가 렌더링된다', () => {
    render(<SignalBadge signal="BUY" />)
    const badge = screen.getByRole('status')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('▲')
    expect(badge).toHaveTextContent('매수 구간')
    // 초록 색상 클래스 포함 확인
    expect(badge.className).toMatch(/buy/)
    expect(badge).toHaveAttribute('aria-label', '현재 매수 진입 구간입니다')
  })

  it('HOLD 신호: 회색 클래스 + — 아이콘 + 관망 텍스트가 렌더링된다', () => {
    render(<SignalBadge signal="HOLD" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('—')
    expect(badge).toHaveTextContent('관망')
    expect(badge.className).toMatch(/hold/)
    expect(badge).toHaveAttribute('aria-label', '현재 관망 구간입니다')
  })

  it('SELL 신호: 빨간 클래스 + ▼ 아이콘 + 매도 접근 텍스트가 렌더링된다', () => {
    render(<SignalBadge signal="SELL" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('▼')
    expect(badge).toHaveTextContent('매도 접근')
    expect(badge.className).toMatch(/sell/)
    expect(badge).toHaveAttribute('aria-label', '현재 매도 접근 구간입니다')
  })

  it('알 수 없는 signal 값 → HOLD 폴백으로 렌더링된다', () => {
    render(<SignalBadge signal="UNKNOWN" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('관망')
  })

  it('size=sm → 텍스트가 작은 크기 클래스를 포함한다', () => {
    render(<SignalBadge signal="BUY" size="sm" />)
    const badge = screen.getByRole('status')
    expect(badge.className).toMatch(/text-\[11px\]/)
  })

  it('size=lg → 텍스트가 큰 크기 클래스를 포함한다', () => {
    render(<SignalBadge signal="SELL" size="lg" />)
    const badge = screen.getByRole('status')
    expect(badge.className).toMatch(/text-\[15px\]/)
  })
})
