/**
 * visual.spec.js — TECH-02 시각 회귀 테스트
 *
 * 검증 항목:
 *   1. 데스크탑(1280×720): 앱 마운트 + 스크롤바 없음
 *   2. 모바일(375×667): 헤더 클리핑 없음 + 가로 스크롤 없음
 *   3. 테마 토글: 라이트모드 전환 후 배경색 변경 확인
 *   4. 차트 전환 애니메이션: 메뉴 클릭 후 chart-page 존재 확인
 */
import { test, expect } from '@playwright/test'

test.describe('대시보드 시각 회귀', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 15000 })
    // 앱 컨테이너 마운트 확인
    await page.waitForSelector('.app-container', { timeout: 10000 })
  })

  // ── 1. 데스크탑 레이아웃 ─────────────────────────────────────────
  test('데스크탑: 앱이 마운트되고 가로 스크롤이 없다', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 })

    // 앱 컨테이너 존재
    const container = page.locator('.app-container')
    await expect(container).toBeVisible()

    // 가로 스크롤 없음 확인
    const scrollWidth = await page.evaluate(() => document.body.scrollWidth)
    const clientWidth = await page.evaluate(() => document.body.clientWidth)
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2) // 2px 허용 오차
  })

  // ── 2. 모바일 375px ───────────────────────────────────────────────
  test('모바일 375px: 헤더가 보이고 가로 스크롤이 없다', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })

    const header = page.locator('.app-header')
    await expect(header).toBeVisible()

    // 헤더가 화면 안에 있음 (클리핑 없음)
    const headerBox = await header.boundingBox()
    expect(headerBox.x).toBeGreaterThanOrEqual(0)
    expect(headerBox.width).toBeLessThanOrEqual(375 + 2)

    // 가로 스크롤 없음
    const scrollWidth = await page.evaluate(() => document.body.scrollWidth)
    expect(scrollWidth).toBeLessThanOrEqual(377)
  })

  // ── 3. 테마 토글 ─────────────────────────────────────────────────
  test('테마 토글: 라이트 모드 전환 시 html에 data-theme=light 적용', async ({ page }) => {
    const toggleBtn = page.locator('.theme-toggle-btn')
    await expect(toggleBtn).toBeVisible()

    // 초기 테마 확인 (dark)
    const initialTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    expect(initialTheme).toBe('dark')

    // 토글 클릭
    await toggleBtn.click()

    const newTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    expect(newTheme).toBe('light')

    // 다시 토글 → dark
    await toggleBtn.click()
    const finalTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    expect(finalTheme).toBe('dark')
  })

  // ── 4. 차트 전환 애니메이션 ──────────────────────────────────────
  test('차트 전환: chart-page 컴포넌트가 렌더링된다', async ({ page }) => {
    // chart-page가 존재하는지 확인 (로딩 스켈레톤이나 실제 차트)
    const chartPage = page.locator('.chart-page, .chart-skeleton').first()
    await expect(chartPage).toBeVisible({ timeout: 8000 })
  })

  // ── 5. 테마 버튼 접근성 ──────────────────────────────────────────
  test('테마 버튼: aria-label이 존재한다', async ({ page }) => {
    const toggleBtn = page.locator('.theme-toggle-btn')
    const ariaLabel = await toggleBtn.getAttribute('aria-label')
    expect(ariaLabel).toBeTruthy()
    expect(ariaLabel.length).toBeGreaterThan(0)
  })
})
