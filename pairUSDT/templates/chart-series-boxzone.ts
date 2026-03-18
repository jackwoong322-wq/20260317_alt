// ── Box zone series (hi/lo lines, fill area, active extension) ─────────────
import { chartState } from './chart-logic.js';
import { dayToTime, detectBoxZones } from './chart-logic.js';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js';
import { renderBoxMarks } from './chart-render-overlays.js';

declare const LightweightCharts: any;

// z.hi / z.lo / z.startX / z.endX 가 하나라도 NaN/null 이면 skip
function isValidZone(z: any): boolean {
  return (
    z != null &&
    Number.isFinite(Number(z.hi)) &&
    Number.isFinite(Number(z.lo)) &&
    Number.isFinite(Number(z.startX)) &&
    Number.isFinite(Number(z.endX)) &&
    z.startX < z.endX
  );
}

// NaN-safe price (applyOptions baseValue 등에 사용)
function safePrice(val: any, fallback = 0): number {
  const n = Number(val);
  return Number.isFinite(n) ? n : fallback;
}

function getBoxZoneColors(
  isPred: boolean, isBearBox: boolean,
): { lineColor: string; fillTop: string; fillBot: string } {
  if (isPred) {
    const rgb = isBearBox ? '255,107,107' : '255,217,102';
    return { lineColor: `rgba(${rgb},0.80)`, fillTop: `rgba(${rgb},0.10)`, fillBot: `rgba(${rgb},0.01)` };
  }
  const rgb = isBearBox ? '255,68,102' : '255,184,0';
  return { lineColor: `rgba(${rgb},0.85)`, fillTop: `rgba(${rgb},0.14)`, fillBot: `rgba(${rgb},0.04)` };
}

function addBoxHiLoLines(
  z: any, zi: number, isPred: boolean, lineColor: string,
  coinId: string, coinData: any, cycle: any, cycleNum: number,
): void {
  const meta = { coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum };
  const t1 = dayToTime(z.startX);
  const t2 = dayToTime(z.endX);

  const hiLine = chartState.chart.addLineSeries({ color: lineColor, lineWidth: isPred ? 1 : 1.5, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
  if (t1 != null && t2 != null) {
    setSeriesDataSafe(hiLine, filterValidPoints([{ time: t1, value: z.hi }, { time: t2, value: z.hi }]), { kind: 'box_hi', ...meta });
  }
  chartState.seriesMap[`${coinId}_${cycle.cycle_number}_bhi${zi}`] = hiLine;

  const loLine = chartState.chart.addLineSeries({ color: lineColor, lineWidth: isPred ? 1 : 1.5, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
  if (t1 != null && t2 != null) {
    setSeriesDataSafe(loLine, filterValidPoints([{ time: t1, value: z.lo }, { time: t2, value: z.lo }]), { kind: 'box_lo', ...meta });
  }
  chartState.seriesMap[`${coinId}_${cycle.cycle_number}_blo${zi}`] = loLine;
}

function addBoxFillSeries(
  z: any, zi: number, fillTop: string, fillBot: string,
  coinId: string, coinData: any, cycle: any, cycleNum: number,
): void {
  const meta = { coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum };
  const t1 = dayToTime(z.startX);
  const t2 = dayToTime(z.endX);
  const fillSeries = chartState.chart.addAreaSeries({ topColor: fillTop, bottomColor: fillBot, lineColor: 'rgba(0,0,0,0)', lineWidth: 0, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
  fillSeries.applyOptions({ baseValue: { type: 'price', price: safePrice(z.lo) } });
  if (t1 != null && t2 != null) {
    setSeriesDataSafe(fillSeries, filterValidPoints([{ time: t1, value: z.hi }, { time: t2, value: z.hi }]), { kind: 'box_fill', ...meta });
  }
  chartState.seriesMap[`${coinId}_${cycle.cycle_number}_bfill${zi}`] = fillSeries;
}

function addActiveBoxExtensionForZone(
  z: any, coinId: string, coinData: any, cycle: any, cycleNum: number,
  lastRealDay: number, lastRealClose: number,
): void {
  const actBear = z.result === 'BEAR_ACTIVE';
  const actColor = actBear ? 'rgba(255,80,100,0.80)' : 'rgba(255,184,0,0.80)';
  const dur = z.endX - z.startX;
  const hiDay = z.hiDay != null ? z.hiDay : z.startX + Math.floor(dur / 4);
  const loDay = z.loDay != null ? z.loDay : z.startX + Math.floor((dur * 3) / 4);

  const pts: any[] = [{ time: lastRealDay, value: lastRealClose }];
  if (actBear) {
    if (hiDay > lastRealDay) pts.push({ time: hiDay, value: z.hi });
    if (loDay > lastRealDay && loDay > (pts[pts.length - 1]?.time ?? 0)) pts.push({ time: loDay, value: z.lo });
  } else {
    if (loDay > lastRealDay) pts.push({ time: loDay, value: z.lo });
    if (hiDay > lastRealDay && hiDay > (pts[pts.length - 1]?.time ?? 0)) pts.push({ time: hiDay, value: z.hi });
  }

  const tsPts = pts.map((p) => { const ts = dayToTime(p.time); if (ts == null || p.value == null) return null; return { time: ts, value: p.value }; }).filter((p) => p !== null);
  if (tsPts.length <= 1) return;

  const actSeries = chartState.chart.addLineSeries({ color: actColor, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
  setSeriesDataSafe(actSeries, filterValidPoints(tsPts), { kind: 'box_active', coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum });
  chartState.seriesMap[`${coinId}_${cycle.cycle_number}_active_${z.boxIndex}`] = actSeries;
}

export function addBoxZoneSeries(
  coinId: string, coinData: any, cycle: any, cycleNum: number,
  cycleMinLowIdx: number, closeKey: string, lineSeries: any,
): void {
  if (!lineSeries) {
    console.warn('[SERIES_NULL] addBoxZoneSeries', { coinId, symbol: coinData.symbol, cycleNum });
    return;
  }
  const hasDbZones = cycle.box_zones && cycle.box_zones.length > 0;
  const zones = hasDbZones ? cycle.box_zones : detectBoxZones(cycle.data);

  zones.forEach((z: any, zi: number) => {
    if (!isValidZone(z)) return;
    const { lineColor, fillTop, fillBot } = getBoxZoneColors(z.is_prediction === 1, z.phase === 'BEAR');
    addBoxHiLoLines(z, zi, z.is_prediction === 1, lineColor, coinId, coinData, cycle, cycleNum);
    addBoxFillSeries(z, zi, fillTop, fillBot, coinId, coinData, cycle, cycleNum);
  });

  chartState.boxMarksData.push({ zones, cycleLowIdx: cycleMinLowIdx, cycleData: cycle.data, seriesKey: closeKey, coinId, symbol: coinData.symbol, cycleNumber: cycle.cycle_number, cycleRef: cycle });
  setTimeout(() => {
    const series = chartState.seriesMap[closeKey];
    if (!series || !chartState.chart) {
      console.warn('[SERIES_NULL] addBoxZoneSeries setTimeout', { closeKey, coinId, symbol: coinData.symbol, cycleNum: cycle.cycle_number, hasSeries: !!series, hasChart: !!chartState.chart });
      return;
    }
    renderBoxMarks(zones, cycleMinLowIdx, cycle.data, chartState.chart.timeScale(), series, coinId, coinData.symbol, cycle.cycle_number, cycle);
  }, 80);
}

export function addBoxZoneFallback(
  coinId: string, coinData: any, cycle: any, cycleMinLowIdx: number, closeKey: string, lineSeries: any,
): void {
  if (!lineSeries) {
    console.warn('[SERIES_NULL] addBoxZoneFallback', { coinId, symbol: coinData.symbol, cycleNum: cycle.cycle_number });
    return;
  }
  chartState.boxMarksData.push({ zones: [], cycleLowIdx: cycleMinLowIdx, cycleData: cycle.data, seriesKey: closeKey, coinId, symbol: coinData.symbol, cycleNumber: cycle.cycle_number, cycleRef: cycle });
  setTimeout(() => {
    const series = chartState.seriesMap[closeKey];
    if (!series || !chartState.chart) {
      console.warn('[SERIES_NULL] addBoxZoneFallback setTimeout', { closeKey, coinId, symbol: coinData.symbol, cycleNum: cycle.cycle_number, hasSeries: !!series, hasChart: !!chartState.chart });
      return;
    }
    renderBoxMarks([], cycleMinLowIdx, cycle.data, chartState.chart.timeScale(), series, coinId, coinData.symbol, cycle.cycle_number, cycle);
  }, 80);
}

export function addActiveBoxExtensions(
  coinId: string, coinData: any, cycle: any, cycleNum: number,
): void {
  if (!cycle.box_zones) return;
  const lastRealDay = cycle.data[cycle.data.length - 1]?.x ?? 0;
  const lastRealClose = cycle.data[cycle.data.length - 1]?.close ?? 100;
  cycle.box_zones.forEach((z: any) => {
    const isAct = z.result === 'BEAR_ACTIVE' || z.result === 'BULL_ACTIVE';
    if (!isAct || z.endX <= lastRealDay) return;
    if (!isValidZone(z)) return;
    addActiveBoxExtensionForZone(z, coinId, coinData, cycle, cycleNum, lastRealDay, lastRealClose);
  });
}