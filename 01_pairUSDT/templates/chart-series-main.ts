/**
 * Main Line Series — close/high/low 전환 (피크 정규화)
 *
 * [설계 결정]
 * - 순수 함수: buildMainLineData, buildFallbackCloseData는 부수효과 없음
 * - 상수: LINE_WIDTH_*는 chart-constants에서 import
 */
import type { ChartState } from './chart-logic.js';
import { dayToTime } from './chart-logic.js';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js';
import { LINE_WIDTH_SINGLE, LINE_WIDTH_MULTI } from './chart-constants.js';

declare const LightweightCharts: any;

export function buildMainLineData(cycleData: any[], minLowDay: number | undefined): any[] {
  return cycleData
    .filter((d: any) => d.x != null)
    .map((d: any) => {
      const ts = dayToTime(d.x);
      if (ts == null) return null;
      return {
        time: ts,
        value: minLowDay != null && d.x <= minLowDay ? d.low : d.high,
      };
    })
    .filter((p: any) => p !== null);
}

export function buildFallbackCloseData(
  coinId: string, symbol: string, cycleName: string, cycleNum: number, cycleData: any[],
): any[] {
  const fallback = cycleData
    .filter((d: any) => d.x != null && d.close != null && Number.isFinite(Number(d.close)))
    .map((d: any) => {
      const ts = dayToTime(d.x);
      if (ts == null) return null;
      return { time: ts, value: d.close };
    })
    .filter((p: any) => p !== null);
  return filterValidPoints(fallback);
}

export function addMainLineSeries(
  state: ChartState,
  coinId: string, coinData: any, cycle: any, color: string,
  isCurr: boolean, cycleNum: number, cycleMinLowIdx: number, closeKey: string,
): any {
  const lineWidth = state.selectedCoins.length > 1 ? LINE_WIDTH_MULTI : LINE_WIDTH_SINGLE;
  const lineSeries = state.chart.addLineSeries({
    color,
    lineWidth,
    lineStyle: LightweightCharts.LineStyle.Solid,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: true,
  });

  const minLowDay = cycle.data[cycleMinLowIdx]?.x;
  const lineData = buildMainLineData(cycle.data, minLowDay);
  let filteredLineData = filterValidPoints(lineData);

  if (filteredLineData.length === 0 && Array.isArray(cycle.data) && cycle.data.length > 0) {
    filteredLineData = buildFallbackCloseData(coinId, coinData.symbol, cycle.cycle_name, cycleNum, cycle.data);
  }

  setSeriesDataSafe(lineSeries, filteredLineData, { kind: 'main', coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum });
  state.seriesMap[closeKey] = lineSeries;
  state.seriesMetaMap[closeKey] = { coinId, cycle };

  return lineSeries;
}
