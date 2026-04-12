/**
 * Chart Constants — 매직 넘버/리터럴 금지 원칙 적용
 *
 * [설계 결정] 모든 숫자·문자열은 의미 있는 이름의 상수로 정의.
 * 금융 도메인 비율, UI 스타일, 시리즈 설정을 한 곳에서 관리.
 */
// ── Line & Series ─────────────────────────────────────
/** 단일 코인 표시 시 메인 라인 두께 */
export const LINE_WIDTH_SINGLE = 3;
/** 다중 코인 비교 시 메인 라인 두께 */
export const LINE_WIDTH_MULTI = 2.5;
/** BTC CURRENT 강조선 두께 */
export const LINE_WIDTH_EMPHASIS = 4;
/** 강조선 색상 (BTC CURRENT) */
export const EMPHASIS_COLOR = '#00d4ff';
// ── Box Zone Detection (JS fallback) ──────────────────
/** 박스로 인정할 최소 일수 */
export const MIN_BOX_DAYS = 5;
/** Bear 박스 이탈 비율 */
export const BEAR_BREAKOUT_RATIO = 0.98;
/** Bull 박스 돌파 비율 */
export const BULL_BREAKOUT_RATIO = 1.1;
/** Bear 반등 확인 비율 */
export const BEAR_REBOUND_RATIO = 1.05;
/** Bull 조정 확인 비율 */
export const BULL_DRAWDOWN_RATIO = 0.95;
/** Bull 피크 판별 lookahead 일수 */
export const BULL_PEAK_LOOKAHEAD_DAYS = 15;
// ── Default Cycle Selection ───────────────────────────
/** 기본 활성화 사이클 번호 */
export const DEFAULT_ACTIVE_CYCLES = [1, 2, 3, 4, 5];
// ── Fallback Values ───────────────────────────────────
/** 예측 경로용 기본 close 값 (데이터 없을 때) */
export const FALLBACK_CLOSE_PCT = 100;
