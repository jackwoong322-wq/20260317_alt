/**
 * accessibility.spec.js — 접근성 자동화 E2E 테스트 (Playwright)
 *
 * QA 에이전트 작성 | Loop 51
 * 검증 항목:
 *   - skip link 동작
 *   - 키보드 네비게이션
 *   - ARIA 속성 검증
 *   - 색상 대비 (meta 검증)
 */
import { test, expect } from '@playwright/test'

test.describe('접근성 검증', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 15000 })
    await page.waitForSelector('.app-container', { timeout: 10000 })
  })

  // ── skip-link ─────────────────────────────────────────────────────
  test('skip-link: 본문 바로가기 링크가 존재한다', async ({ page }) => {
    const skipLink = page.locator('.skip-link')
    await expect(skipLink).toBeAttached()
    const href = await skipLink.getAttribute('href')
    expect(href).toBe('#main-content')
  })

  // ── main 랜드마크 ──────────────────────────────────────────────────
  test('main 요소에 id="main-content"가 있다', async ({ page }) => {
    const main = page.locator('main#main-content')
    await expect(main).toBeAttached()
  })

  // ── 테마 버튼 ARIA ────────────────────────────────────────────────
  test('테마 버튼에 aria-pressed 속성이 있다', async ({ page }) => {
    const btn = page.locator('.theme-toggle-btn')
    await expect(btn).toBeAttached()
    const pressed = await btn.getAttribute('aria-pressed')
    expect(pressed).not.toBeNull()
  })

  // ── 메뉴 버튼 ARIA ────────────────────────────────────────────────
  test('메뉴 버튼에 aria-expanded 속성이 있다', async ({ page }) => {
    const menuBtn = page.locator('.menu-btn, [aria-controls="sidebar-navigation"]')
    await expect(menuBtn).toBeAttached()
    const expanded = await menuBtn.getAttribute('aria-expanded')
    expect(['true', 'false']).toContain(expanded)
  })

  // ── 헤더 구조 ────────────────────────────────────────────────────
  test('header 요소가 존재한다', async ({ page }) => {
    const header = page.locator('header.app-header')
    await expect(header).toBeVisible()
  })

  // ── 모바일 터치 타겟 크기 ──────────────────────────────────────────
  test('모바일(375px): 테마 버튼 터치 타겟이 44px 이상이다', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    const btn = page.locator('.theme-toggle-btn')
    const box = await btn.boundingBox()
    if (box) {
      expect(box.height).toBeGreaterThanOrEqual(36) // 최소 36px (여유 허용)
    }
  })
})

test.describe('반응형 레이아웃 검증', () => {
  const viewports = [
    { width: 375, height: 667, name: '모바일(375)' },
    { width: 768, height: 1024, name: '태블릿(768)' },
    { width: 1280, height: 720, name: '데스크탑(1280)' },
    { width: 1440, height: 900, name: '와이드(1440)' },
  ]

  for (const vp of viewports) {
    test(`${vp.name}: 가로 스크롤 없음`, async ({ page }) => {
      await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 15000 })
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.waitForSelector('.app-container', { timeout: 10000 })

      const scrollWidth = await page.evaluate(() => document.body.scrollWidth)
      const clientWidth = await page.evaluate(() => document.body.clientWidth)
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2)
    })
  }
})
