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
        'src/components/ChartStatus.jsx',  // wrapper only
        'src/**/*.test.*',
      ],
      // TECH-03: 커버리지 임계값 — 80% 목표
      thresholds: {
        lines: 60,
        functions: 60,
        branches: 50,
      },
    },
  },
})