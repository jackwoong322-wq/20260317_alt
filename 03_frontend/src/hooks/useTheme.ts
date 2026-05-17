/**
 * useTheme.ts — 다크/라이트 테마 토글 훅 (TypeScript)
 *
 * 04_frontend useTheme.js 기반 TypeScript 포팅
 * - localStorage 영속
 * - <html data-theme="light|dark"> 속성으로 테마 적용
 * - 시스템 prefers-color-scheme 초기값 존중
 *
 * BUG-07 수정: matchMedia/localStorage null 체크 강화
 */
import { useState, useEffect, useCallback } from 'react'

export type Theme = 'light' | 'dark'

export interface UseThemeReturn {
  theme: Theme
  toggleTheme: () => void
}

const STORAGE_KEY = 'btc-dashboard-theme'
const VALID_THEMES = new Set<Theme>(['light', 'dark'])

function isValidTheme(value: string | null): value is Theme {
  return VALID_THEMES.has(value as Theme)
}

function getInitialTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (isValidTheme(saved)) return saved
  } catch {
    // localStorage 접근 실패 무시 (iframe/private 모드 등)
  }

  try {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
    }
  } catch {
    // matchMedia 미지원 환경 무시
  }

  return 'dark'
}

export function useTheme(): UseThemeReturn {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // 무시
    }
  }, [theme])

  const toggleTheme = useCallback((): void => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggleTheme }
}
