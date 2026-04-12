// ── High / Low dotted line series ──────────────────────
import { chartState } from './chart-logic.js';
import { dayToTime } from './chart-logic.js';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js';

declare const LightweightCharts: any;

function buildOhlcFieldData(cycleData: any[], field: 'high' | 'low'): any[] {
  return filterValidPoints(
    cycleData
      .filter((d: any) => d.x != null)
      .map((d: any) => {
        const ts = dayToTime(d.x);
        if (ts == null) return null;
        return { time: ts, value: d[field] };
      })
      .filter((p: any) => p !== null),
  );
}

function addSingleHiLoSeries(
  color: string,
  data: any[],
  kind: string,
  meta: { coinId: string; symbol: string; cycleName: string; cycleNum: number },
): any {
  const series = chartState.chart.addLineSeries({
    color: color + '55',
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
  });
  setSeriesDataSafe(series, data, { kind, ...meta });
  return series;
}

export function addHighLowSeries(
  coinId: string,
  coinData: any,
  cycle: any,
  color: string,
  cycleNum: number,
): void {
  const meta = { coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum };

  const hiData = buildOhlcFieldData(cycle.data, 'high');
  const hiSeries = addSingleHiLoSeries(color, hiData, 'hi', meta);
  chartState.seriesMap[`${coinId}_${cycle.cycle_number}_hi`] = hiSeries;

  const loData = buildOhlcFieldData(cycle.data, 'low');
  const loSeries = addSingleHiLoSeries(color, loData, 'lo', meta);
  chartState.seriesMap[`${coinId}_${cycle.cycle_number}_lo`] = loSeries;
}
