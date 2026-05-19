import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = env.VITE_API_URL ?? 'http://localhost:8000'

  return {
  plugins: [react()],
  server: {
    proxy: {
      '/api': apiUrl,
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    exclude: ['**/node_modules/**', '**/my-test-harness/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        // 레거시 앱 — canvas 없이 테스트 불가
        'src/LegacyAnalyzerApp.tsx',
        'src/main.tsx',
        // 미포팅 컴포넌트
        'src/components/WakingBanner.tsx',
        'src/**/*.test.*',
        'src/tests/**',
      ],
      // TECH-04: 신규 포팅 코드 기준 임계값
      thresholds: {
        lines: 70,
        functions: 60,
        branches: 60,
      },
    },
  },
  }
})
