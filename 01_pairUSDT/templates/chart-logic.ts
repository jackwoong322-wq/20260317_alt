/**
 * Chart Logic — 코어 상태, 색상, 데이터 처리 (DOM 없음)
 *
 * [설계 결정]
 * - chartState: 전역 대체용 래퍼. 향후 DI로 App 인스턴스에 주입 권장
 * - 상수: MIN_BOX_DAYS 등은 chart-constants에서 re-export하여 일원화
 * - 순수 함수: detectBoxZones, detectBearBull는 입력만으로 출력 결정
 */
import { MIN_BOX_DAYS, BEAR_BREAKOUT_RATIO, BULL_BREAKOUT_RATIO, BEAR_REBOUND_RATIO, BULL_DRAWDOWN_RATIO, BULL_PEAK_LOOKAHEAD_DAYS } from './chart-constants.js';

// ── Basic Types ───────────────────────────────────────
type CyclePoint = {
  x: number;
  low: number;
  high: number;
  close: number;
  date?: string;
};

type BoxZone = {
  startX: number;
  endX: number;
  hi: number;
  lo: number;
  loDay?: number;
  hiDay?: number;
  duration?: number;
  rangePct: string;
  phase: 'BEAR' | 'BULL';
  result: string;
  is_prediction: number;
  [key: string]: any;
};

type BoxMarksEntry = {
  zones: BoxZone[];
  cycleLowIdx: number;
  cycleData: CyclePoint[];
  seriesKey: string;
  coinId: string;
  symbol: string;
  cycleNumber: number;
  cycleRef: any;
};

// ── Cycle Colors ──────────────────────────────────────
export const CYCLE_COLORS = {
  1: { main: '#FF4D4D', band: 'rgba(255,77,77,0.08)' },
  2: { main: '#00C8FF', band: 'rgba(0,200,255,0.08)' },
  3: { main: '#FFB800', band: 'rgba(255,184,0,0.08)' },
  4: { main: '#A78BFA', band: 'rgba(167,139,250,0.08)' },
  5: { main: '#FF69B4', band: 'rgba(255,105,180,0.08)' },
};

// ── Scenario Styles (prediction styling) ──────────────
export const SCENARIO_STYLE = {
  es: {
    line: 'rgba(255,184,0,0.85)',
    fill: 'rgba(255,184,0,0.10)',
    dot: '#FFB800',
    lbl: '#FFD700',
    tag: '(ES)',
  },
  plus: {
    line: 'rgba(0,255,136,0.85)',
    fill: 'rgba(0,255,136,0.08)',
    dot: '#00ff88',
    lbl: '#66ffaa',
    tag: '(+1σ)',
  },
  minus: {
    line: 'rgba(255,68,102,0.85)',
    fill: 'rgba(255,68,102,0.08)',
    dot: '#ff4466',
    lbl: '#ff8899',
    tag: '(-1σ)',
  },
} as const;

type ScenarioKey = keyof typeof SCENARIO_STYLE;

export function getScenarioKey(result: string | null | undefined): ScenarioKey {
  if (!result) return 'es';
  const r = (result || '').toUpperCase();
  if (r.includes('_PLUS') || r.includes('CHAIN_PLUS')) return 'plus';
  if (r.includes('_MINUS') || r.includes('CHAIN_MINUS')) return 'minus';
  return 'es';
}

// ── Coin Colors / Global State ────────────────────────
export const COIN_COLORS = [
  '#00D4FF',
  '#FF6B35',
  '#A8FF3E',
  '#FF3CAC',
  '#784BA0',
  '#2B86C5',
  '#FFD700',
  '#FF6B6B',
  '#4ECDC4',
  '#45B7D1',
];

// BTC 기준축용 코인 ID (symbol === 'BTC')
const BTC_COIN_ID =
  Object.keys(ALL_DATA).find(
    (id) => (ALL_DATA[id]?.symbol || '').toUpperCase() === 'BTC',
  ) || null;

// [설계 결정] 단일 state 객체로 전역 let 제거. DI 시 이 객체를 주입.
const _state = {
  selectedCoins: (BTC_COIN_ID ? [BTC_COIN_ID] : []) as string[],
  activeCycles: new Set([1, 2, 3, 4, 5]) as Set<number>,
  showHighLow: false,
  showBoxZone: true,
  showBearBull: false,
  bearBullLabels: [] as any[],
  boxMarkEls: [] as any[],
  boxMarksData: [] as BoxMarksEntry[],
  chart: null as any,
  seriesMap: {} as Record<string, any>,
  seriesMetaMap: {} as Record<string, any>,
};

export const chartState = {
  get chart() { return _state.chart; },
  set chart(v: any) { _state.chart = v; },
  get seriesMap() { return _state.seriesMap; },
  set seriesMap(v: Record<string, any>) { _state.seriesMap = v; },
  get seriesMetaMap() { return _state.seriesMetaMap; },
  set seriesMetaMap(v: Record<string, any>) { _state.seriesMetaMap = v; },
  get boxMarksData() { return _state.boxMarksData; },
  set boxMarksData(v: BoxMarksEntry[]) { _state.boxMarksData = v; },
  get selectedCoins() { return _state.selectedCoins; },
  set selectedCoins(v: string[]) { _state.selectedCoins = v; },
  get activeCycles() { return _state.activeCycles; },
  set activeCycles(v: Set<number>) { _state.activeCycles = v; },
  get showHighLow() { return _state.showHighLow; },
  set showHighLow(v: boolean) { _state.showHighLow = v; },
  get showBoxZone() { return _state.showBoxZone; },
  set showBoxZone(v: boolean) { _state.showBoxZone = v; },
  get showBearBull() { return _state.showBearBull; },
  set showBearBull(v: boolean) { _state.showBearBull = v; },
  get boxMarkEls() { return _state.boxMarkEls; },
  set boxMarkEls(v: any[]) { _state.boxMarkEls = v; },
  get bearBullLabels() { return _state.bearBullLabels; },
  set bearBullLabels(v: any[]) { _state.bearBullLabels = v; },
};

export type ChartState = typeof chartState;

// ── Time helpers for Lightweight Charts ──────────────
// We use simple numeric "day index" as chart time.
export function dayToTime(day: number): number {
  return day;
}

export function timeToDay(time: number | { day: number } | null | undefined): number | null {
  if (typeof time === 'number') return time;
  if (time && typeof time.day === 'number') return time.day;
  return null;
}

// ── Step-series helpers (for prediction paths) ────────
export function sanitizePathPoints(points: Array<{ x: number; value?: number }> | null | undefined) {
  if (!points) return [];
  const byX = new Map<number, { x: number; value?: number }>();
  points.forEach((p: { x: number; value?: number } | null | undefined) => {
    if (!p || typeof p.x !== 'number') return;
    byX.set(p.x, p);
  });
  return Array.from(byX.values()).sort((a, b) => a.x - b.x);
}

/**
 * buildStepSeries — prediction 경로를 LineSeries용 포인트로 변환
 *
 * [현재] step 구간 제거 → 일반 직선 연결 (t1,v1)-(t2,v2)
 *
 * [롤백] step(계단형) 복원 시 아래 주석 블록으로 교체:
 * ---
 * const STEP_TIME_EPSILON = 1e-9;
 * for (let i = 0; i < points.length; i++) {
 *   const p = points[i];
 *   out.push(p);
 *   const next = points[i + 1];
 *   if (!next) continue;
 *   const stepTime = next.time - STEP_TIME_EPSILON;
 *   if (stepTime > p.time) out.push({ time: stepTime, value: p.value });
 * }
 * ---
 */
export function buildStepSeries(points: Array<{ time: number; value: number }> | null | undefined) {
  if (!points || points.length === 0) return [];
  return [...points];
}

// ── Box Zone detection (JS fallback when DB has no data) ─
export function detectBoxZones(data: CyclePoint[]): BoxZone[] {
  const zones: BoxZone[] = [];
  if (!data || data.length < 2) return zones;

  let cycleMinLow = Infinity,
    cycleMinIdx = 0;
  data.forEach((d, i) => {
    if (d.low < cycleMinLow) {
      cycleMinLow = d.low;
      cycleMinIdx = i;
    }
  });

  const phase1 = data.slice(0, cycleMinIdx + 1);
  const phase2 = data.slice(cycleMinIdx);

  let i = 0;
  while (i < phase1.length - 1) {
    let troughIdx = -1;
    for (let k = i; k < phase1.length; k++) {
      const candLow = phase1[k].low;
      const confirmEnd = Math.min(phase1.length - 1, k + 3);
      let broken3 = false;
      for (let m = k + 1; m <= confirmEnd; m++) {
        if (phase1[m].low < candLow) {
          broken3 = true;
          break;
        }
      }
      if (!broken3) {
        troughIdx = k;
        break;
      }
    }
    if (troughIdx === -1) break;

    const baseLow = phase1[troughIdx].low;
    let reboundIdx = -1;
    for (let k = troughIdx + 1; k < phase1.length; k++) {
      if (phase1[k].high >= baseLow * BEAR_REBOUND_RATIO) {
        reboundIdx = k;
        break;
      }
    }
    if (reboundIdx === -1) {
      i = troughIdx + 1;
      continue;
    }

    let boxHi = -Infinity,
      boxLo = Infinity;
    for (let k = troughIdx; k <= reboundIdx; k++) {
      boxHi = Math.max(boxHi, phase1[k].high);
      boxLo = Math.min(boxLo, phase1[k].low);
    }
    const loDayX = phase1[troughIdx].x;
    const hiDayX = phase1[reboundIdx].x;
    const boxStart = troughIdx;
    let boxEnd = reboundIdx;
    let broken = false;

    for (let j = reboundIdx + 1; j < phase1.length; j++) {
      if (phase1[j].close < boxLo * BEAR_BREAKOUT_RATIO) {
        const duration = phase1[j - 1].x - phase1[boxStart].x + 1;
        if (duration >= MIN_BOX_DAYS) {
          zones.push({
            startX: phase1[boxStart].x,
            endX: phase1[j - 1].x,
            hi: boxHi,
            lo: boxLo,
            loDay: loDayX,
            hiDay: hiDayX,
            duration,
            rangePct: (((boxHi - boxLo) / boxLo) * 100).toFixed(1),
            phase: 'BEAR',
            result: 'DOWN',
            is_prediction: 0,
          });
        }
        i = j;
        broken = true;
        break;
      }
      boxHi = Math.max(boxHi, phase1[j].high);
      boxLo = Math.min(boxLo, phase1[j].low);
      boxEnd = j;
    }
    if (!broken) {
      const duration = phase1[boxEnd].x - phase1[boxStart].x + 1;
      if (duration >= MIN_BOX_DAYS) {
        zones.push({
          startX: phase1[boxStart].x,
          endX: phase1[boxEnd].x,
          hi: boxHi,
          lo: boxLo,
          loDay: loDayX,
          hiDay: hiDayX,
          duration,
          rangePct: (((boxHi - boxLo) / boxLo) * 100).toFixed(1),
          phase: 'BEAR',
          result: 'BOTTOM',
          is_prediction: 0,
        });
      }
      break;
    }
  }

  function bullBoxHiLo(
    phase2: CyclePoint[],
    boxStart: number,
    boxEnd: number,
  ): { boxHi: number; boxLo: number; hiDayX: number; loDayX: number } {
    let loIdx = boxStart;
    for (let k = boxStart + 1; k <= boxEnd; k++) {
      if (phase2[k].low < phase2[loIdx].low) loIdx = k;
    }
    const loDayX = phase2[loIdx].x;
    const boxLo = phase2[loIdx].low;
    let hiIdx = boxStart;
    for (let k = boxStart; k < loIdx; k++) {
      if (phase2[k].high > phase2[hiIdx].high) hiIdx = k;
    }
    const hiDayX = phase2[hiIdx].x;
    const boxHi = phase2[hiIdx].high;
    return { boxHi, boxLo, hiDayX, loDayX };
  }

  i = 0;
  for (let _guard = 0; _guard < 300 && i < phase2.length - 1; _guard++) {
    let peakIdx = -1;
    for (let k = i; k < phase2.length - 1; k++) {
      const hi = Math.min(phase2.length - 1, k + BULL_PEAK_LOOKAHEAD_DAYS);
      let isPeak = true;
      for (let m = k + 1; m <= hi; m++) {
        if (phase2[m].high >= phase2[k].high) {
          isPeak = false;
          break;
        }
      }
      if (isPeak) {
        peakIdx = k;
        break;
      }
    }
    if (peakIdx === -1) break;

    const peakHi = phase2[peakIdx].high;
    let adjIdx = -1;
    for (let k = peakIdx + 1; k < phase2.length; k++) {
      if (phase2[k].low <= peakHi * BULL_DRAWDOWN_RATIO) {
        adjIdx = k;
        break;
      }
    }
    if (adjIdx === -1) break;

    const boxStart = peakIdx;
    let boxEnd = adjIdx;
    let broken = false;
    const breakoutThreshold = peakHi * BULL_BREAKOUT_RATIO;

    for (let j = adjIdx + 1; j < phase2.length; j++) {
      if (phase2[j].close > breakoutThreshold) {
        const endIdx = j - 1;
        const duration = phase2[endIdx].x - phase2[boxStart].x + 1;
        if (duration >= MIN_BOX_DAYS) {
          const { boxHi, boxLo, hiDayX, loDayX } = bullBoxHiLo(
            phase2,
            boxStart,
            endIdx,
          );
          zones.push({
            startX: phase2[boxStart].x,
            endX: phase2[endIdx].x,
            hi: boxHi,
            lo: boxLo,
            hiDay: hiDayX,
            loDay: loDayX,
            duration,
            rangePct: (((boxHi - boxLo) / boxLo) * 100).toFixed(1),
            phase: 'BULL',
            result: 'UP',
            is_prediction: 0,
          });
        }
        i = j;
        broken = true;
        break;
      }
      boxEnd = j;
    }
    if (!broken) {
      const duration = phase2[boxEnd].x - phase2[boxStart].x + 1;
      if (duration >= MIN_BOX_DAYS) {
        const { boxHi, boxLo, hiDayX, loDayX } = bullBoxHiLo(
          phase2,
          boxStart,
          boxEnd,
        );
        zones.push({
          startX: phase2[boxStart].x,
          endX: phase2[boxEnd].x,
          hi: boxHi,
          lo: boxLo,
          hiDay: hiDayX,
          loDay: loDayX,
          duration,
          rangePct: (((boxHi - boxLo) / boxLo) * 100).toFixed(1),
          phase: 'BULL',
          result: 'ACTIVE',
          is_prediction: 0,
        });
      }
      break;
    }
  }
  return zones;
}

// ── Bear/Bull detection for background segments ───────
export function detectBearBull(data: CyclePoint[]): {
  type: 'BEAR' | 'BULL';
  startX: number;
  endX: number;
  startVal: number;
  endVal: number;
  pct: string;
  days: number;
}[] {
  if (!data || data.length === 0) return [];
  let minVal = Infinity,
    minIdx = 0;
  data.forEach((d, i) => {
    if (d.close < minVal) {
      minVal = d.close;
      minIdx = i;
    }
  });
  const bottomDay = data[minIdx].x;
  const startDay = data[0].x;
  const endDay = data[data.length - 1].x;
  const segments: {
    type: 'BEAR' | 'BULL';
    startX: number;
    endX: number;
    startVal: number;
    endVal: number;
    pct: string;
    days: number;
  }[] = [];
  if (minIdx > 5) {
    segments.push({
      type: 'BEAR',
      startX: startDay,
      endX: bottomDay,
      startVal: data[0].close,
      endVal: minVal,
      pct: (((minVal - data[0].close) / data[0].close) * 100).toFixed(1),
      days: bottomDay - startDay,
    });
  }
  if (minIdx < data.length - 5) {
    const lastVal = data[data.length - 1].close;
    segments.push({
      type: 'BULL',
      startX: bottomDay,
      endX: endDay,
      startVal: minVal,
      endVal: lastVal,
      pct: (((lastVal - minVal) / minVal) * 100).toFixed(1),
      days: endDay - bottomDay,
    });
  }
  return segments;
}

// ── BTC anchor info + historical box stats ────────────
export function getBtcAnchorInfo(
  cycleNumber: number,
): { progress: number; level: string; label: string } | null {
  if (!BTC_COIN_ID) return null;
  const btc = ALL_DATA[BTC_COIN_ID];
  if (!btc || !btc.cycles) return null;
  let cyc = btc.cycles.find((c: any) => c.cycle_number === cycleNumber);
  if (!cyc) {
    cyc = btc.cycles.find((c: any) =>
      (c.cycle_name || '').toLowerCase().includes('current'),
    );
  }
  if (!cyc || !cyc.data || cyc.data.length === 0) return null;
  const last = cyc.data[cyc.data.length - 1];
  const AVG_BTC_CYCLE_DAYS = 365;
  const progress = Math.min(last.x / AVG_BTC_CYCLE_DAYS, 1.0);
  let level = 'LOW';
  if (progress >= 0.85) level = 'HIGH';
  else if (progress >= 0.65) level = 'MID';
  const label =
    level === 'HIGH' ? 'High Risk' : level === 'MID' ? 'Caution' : 'Normal';
  return { progress, level, label };
}

export function getPhaseBoxStatsForSymbol(
  symbol: string,
  phase: string,
): { avg: number; max: number } | null {
  const coinId = Object.keys(ALL_DATA).find(
    (id) =>
      (ALL_DATA[id]?.symbol || '').toUpperCase() === symbol.toUpperCase(),
  );
  if (!coinId) return null;
  const d = ALL_DATA[coinId];
  if (!d || !d.cycles) return null;
  const counts: number[] = [];
  d.cycles.forEach((c: any) => {
    const zs = c.box_zones || [];
    const cnt = zs.filter((z: any) => z.phase === phase && !z.is_prediction)
      .length;
    if (cnt > 0) counts.push(cnt);
  });
  if (!counts.length) return null;
  const sum = counts.reduce((a, b) => a + b, 0);
  const avg = sum / counts.length;
  const max = Math.max(...counts);
  return { avg, max };
}

// ── Lookup box info at given day (for tooltip) ────────
export function findBoxAtDay(
  dayX: number,
  coinId: string,
  cycleNum: number,
): {
  zone: BoxZone;
  index: number;
  prev: BoxZone | null;
  cycleLow: number | null;
  firstBullZi: number;
} | null {
  for (const bmd of _state.boxMarksData as any[]) {
    if (bmd.seriesKey !== `${coinId}_${cycleNum}_close`) continue;
    const firstBullZi = bmd.zones.findIndex((z: BoxZone) => z.phase === 'BULL');
    for (let zi = 0; zi < bmd.zones.length; zi++) {
      const z = bmd.zones[zi];
      if (dayX >= z.startX && dayX <= z.endX) {
        const prev = bmd.zones[zi - 1] || null;
        const cycleLow = bmd.cycleData[bmd.cycleLowIdx]?.low ?? null;
        return { zone: z, index: zi, prev, cycleLow, firstBullZi };
      }
    }
  }
  return null;
}

