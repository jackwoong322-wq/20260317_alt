/**
 * chartSkeleton.test.tsx — 03_frontend ChartSkeleton 접근성 + 렌더링 테스트
 *
 * QA 에이전트 작성 | Loop 30
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChartSkeleton from '../components/ChartSkeleton'

describe('[QA] ChartSkeleton (TypeScript)', () => {
  it('role="status"와 aria-live="polite"가 있다 (BUG-10)', () => {
    const { container } = render(<ChartSkeleton />)
    const el = container.firstChild as HTMLElement
    expect(el.getAttribute('role')).toBe('status')
    expect(el.getAttribute('aria-live')).toBe('polite')
  })

  it('스크린 리더 텍스트가 포함되어 있다', () => {
    render(<ChartSkeleton />)
    expect(screen.getByText('차트 데이터를 불러오고 있습니다. 잠시 기다려 주세요.')).toBeDefined()
  })

  it('기본 type은 line이다', () => {
    const { container } = render(<ChartSkeleton />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
  })

  it('type="bar" 시 SVG 없음, bands 표시', () => {
    const { container } = render(<ChartSkeleton type="bar" />)
    const svg = container.querySelector('svg')
    expect(svg).toBeNull()
  })

  it('type="line" 시 SVG 렌더링', () => {
    const { container } = render(<ChartSkeleton type="line" />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
  })

  it('aria-hidden="true"인 SVG는 스크린 리더에서 무시된다', () => {
    const { container } = render(<ChartSkeleton type="line" />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('aria-hidden')).toBe('true')
  })
})
