/**
 * useTheme.js — 다크/라이트 테마 토글 훅
 *
 * - localStorage에 사용자 선택 저장
 * - <html data-theme="light|dark"> 속성으로 테마 적용
 * - 시스템 prefers-color-scheme 초기값 존중
 */
import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'btc-dashboard-theme'

function getInitialTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* 무시 */ }
  // 시스템 설정 감지
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function useTheme() {
  const [theme, setTheme] = useState(getInitialTheme)

  // html 요소에 data-theme 속성 적용
  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    try { localStorage.setItem(STORAGE_KEY, theme) } catch { /* 무시 */ }
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggleTheme }
}
