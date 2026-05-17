import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: '',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.js'],
    // E2E 테스트 제외 (Playwright 전용)
    exclude: ['**/node_modules/**', '**/e2e/**', '**/*.spec.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary'],
      include: [
        'src/components/**/*.jsx',
        'src/hooks/**/*.js',
        'src/lib/**/*.js',
        'src/utils/**/*.js',
        'src/mocks/**/*.js',
      ],
      exclude: [
        // Chart 렌더링 컴포넌트: lightweight-charts canvas → jsdom 미지원
        'src/components/BearBoxChart.jsx',
        'src/components/BullBoxChart.jsx',
        'src/components/CycleComparisonChart.jsx',
        'src/components/TradingChart.jsx',
        'src/components/ChartOverlay.jsx',
        'src/components/layout/**',
        // API 계층: 실제 네트워크 없이 커버리지 측정 불가
        'src/lib/api.js',
        // wrapper only
        'src/components/ChartStatus.jsx',
        'src/**/*.test.*',
      ],
      // TECH-03: 가측 코드 기준 임계값
      thresholds: {
        lines: 15,
        functions: 25,
        branches: 12,
      },
    },
  },
})