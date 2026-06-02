import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import SandboxSimulator from '../components/SandboxSimulator'

describe('SandboxSimulator', () => {
  it('처음 렌더링 시 비활성화 상태이며 컨트롤들이 disabled 상태다', () => {
    const handleSimulate = vi.fn()
    const handleReset = vi.fn()

    render(<SandboxSimulator onSimulate={handleSimulate} onReset={handleReset} />)

    expect(screen.getByText('투자 신호 샌드박스')).toBeInTheDocument()
    const applyButton = screen.getByRole('button', { name: '시나리오 적용' })
    expect(applyButton).toBeDisabled()
  })

  it('토글 스위치를 활성화하면 시뮬레이터 콜백이 즉시 호출되고 컨트롤들이 활성화된다', () => {
    const handleSimulate = vi.fn()
    const handleReset = vi.fn()

    render(<SandboxSimulator onSimulate={handleSimulate} onReset={handleReset} />)

    const checkbox = screen.getByRole('checkbox', { name: '샌드박스 모드 활성화' })
    expect(checkbox).not.toBeChecked()

    // 활성화 토글 클릭
    fireEvent.click(checkbox)
    expect(checkbox).toBeChecked()
    expect(handleSimulate).toHaveBeenCalled()

    const applyButton = screen.getByRole('button', { name: '시나리오 적용' })
    expect(applyButton).not.toBeDisabled()
  })

  it('활성화 상태에서 적용 버튼을 누르면 업데이트된 매개변수로 콜백이 호출된다', () => {
    const handleSimulate = vi.fn()
    const handleReset = vi.fn()

    render(<SandboxSimulator onSimulate={handleSimulate} onReset={handleReset} />)

    const checkbox = screen.getByRole('checkbox', { name: '샌드박스 모드 활성화' })
    fireEvent.click(checkbox)

    const priceInput = screen.getByLabelText('가상 현재가 ($)')
    fireEvent.change(priceInput, { target: { value: '80000' } })

    const applyButton = screen.getByRole('button', { name: '시나리오 적용' })
    fireEvent.click(applyButton)

    expect(handleSimulate).toHaveBeenCalledTimes(2) // 1st on toggle, 2nd on apply button
    const lastCallArg = handleSimulate.mock.calls[1][0]
    expect(lastCallArg.currentPrice).toBe(80000)
  })

  it('토글을 해제하면 reset 콜백이 호출된다', () => {
    const handleSimulate = vi.fn()
    const handleReset = vi.fn()

    render(<SandboxSimulator onSimulate={handleSimulate} onReset={handleReset} />)

    const checkbox = screen.getByRole('checkbox', { name: '샌드박스 모드 활성화' })
    
    // On
    fireEvent.click(checkbox)
    // Off
    fireEvent.click(checkbox)

    expect(handleReset).toHaveBeenCalled()
  })
})
