import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import ShapForcePlot from '../components/ShapForcePlot'

describe('ShapForcePlot', () => {
  it('기본 피처들로 정상 렌더링되며 제목이 표시된다', () => {
    render(<ShapForcePlot />)
    expect(screen.getByText('XGBoost 변수 기여도 (SHAP)')).toBeInTheDocument()
    expect(screen.getByText('Mayer Multiple')).toBeInTheDocument()
    expect(screen.getByText('DXY Correlation (90d)')).toBeInTheDocument()
  })

  it('사용자 정의 피처 리스트를 주입했을 때 해당 지표와 영향도가 올바르게 표시된다', () => {
    const mockFeatures = [
      { name: 'Custom Indicator A', value: '1.5', impact: 0.15, desc: 'A Desc' },
      { name: 'Custom Indicator B', value: '2.5', impact: -0.25, desc: 'B Desc' },
    ]
    render(<ShapForcePlot features={mockFeatures} />)
    expect(screen.getByText('Custom Indicator A')).toBeInTheDocument()
    expect(screen.getByText('Custom Indicator B')).toBeInTheDocument()
    expect(screen.getByText('+0.15')).toBeInTheDocument()
    expect(screen.getByText('-0.25')).toBeInTheDocument()
  })
})
