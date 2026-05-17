/**
 * chartHelpers.ts — 03_frontend 공통 순수 유틸 함수
 *
 * 아키텍처 규칙:
 *   - 사이드 이펙트 없음 (순수 함수만)
 *   - DOM / API 접근 없음
 *   - 완전 테스트 가능
 */

/**
 * 타임스탬프 → YYYY-MM-DD 문자열 변환
 */
export function toDateString(timestamp: string | number | null | undefined): string | null {
  if (!timestamp) return null
  try {
    const date = new Date(timestamp)
    if (isNaN(date.getTime())) return null
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  } catch {
    return null
  }
}

/**
 * 고점~저점 사이에서 현재값의 위치를 0~100%로 계산
 */
export function calcPositionPercent(current: number, lo: number, hi: number): number {
  if (hi <= lo) return 0
  return Math.max(0, Math.min(100, ((current - lo) / (hi - lo)) * 100))
}

/**
 * 파일명 안전화 (경로 조작 방지)
 */
export function safeFilename(name: string, maxLen: number = 80): string {
  return String(name)
    .replace(/[^a-zA-Z0-9\-_]/g, '-')
    .slice(0, maxLen)
}

/**
 * 뷰포트 클리핑 보정 — 툴팁이 컨테이너 밖으로 벗어나지 않도록
 */
export function clampTooltipPosition(
  rawX: number,
  rawY: number,
  containerWidth: number,
  containerHeight: number,
  tooltipWidth: number = 240,
  tooltipHeight: number = 120,
  edgePadding: number = 8,
): { x: number; y: number } {
  let x = rawX + 14
  let y = rawY - 10

  if (x + tooltipWidth + edgePadding > containerWidth) {
    x = rawX - tooltipWidth - 14
  }
  if (y + tooltipHeight + edgePadding > containerHeight) {
    y = containerHeight - tooltipHeight - edgePadding
  }
  if (y < edgePadding) y = edgePadding
  if (x < edgePadding) x = edgePadding

  return { x, y }
}

/**
 * Day 레이블 계산 — epoch 기준 상대 일수
 */
export function calcDayLabel(time: string | number): string {
  try {
    const base = new Date(2000, 0, 1)
    const d = new Date(time)
    if (isNaN(d.getTime())) return String(time)
    const diff = Math.round((d.getTime() - base.getTime()) / 86_400_000)
    return `Day ${diff}`
  } catch {
    return String(time)
  }
}

/**
 * 등락 문자열 계산
 */
export function calcDiffStr(current: number, prev: number | null, unit: string = '%'): string | null {
  if (prev == null) return null
  const diff = current - prev
  return (diff >= 0 ? '+' : '') + diff.toFixed(2) + unit
}
