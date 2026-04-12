// ── Prediction path series (bull / bear dotted lines) ──────────────────────
import { chartState } from './chart-logic.js';
import { dayToTime, buildStepSeries, sanitizePathPoints } from './chart-logic.js';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js';

declare const LightweightCharts: any;

function buildPathLinePoints(rawPts: any[]): { time: number; value: number }[] {
  return rawPts
    .map((p: any) => {
      const ts = dayToTime(p.x);
      const val = Number(p.value);
      if (ts == null || p.value == null || !Number.isFinite(ts) || !Number.isFinite(val)) return null;
      return { time: ts, value: val };
    })
    .filter((p: any): p is { time: number; value: number } => p !== null);
}

function addSinglePathSeries(
  pts: any[],
  color: string,
  kind: string,
  seriesKey: string,
  meta: { coinId: string; symbol: string; cycleName: string; cycleNum: number },
): void {
  const linePoints = buildPathLinePoints(pts);
  const seriesData = buildStepSeries(linePoints);

  const pathSeries = chartState.chart.addLineSeries({
    color,
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
  });
  setSeriesDataSafe(pathSeries, filterValidPoints(seriesData), { kind, ...meta });
  chartState.seriesMap[seriesKey] = pathSeries;
}

export function addPredictionPaths(
  coinId: string,
  coinData: any,
  cycle: any,
  cycleNum: number,
): void {
  if (!cycle.prediction_paths) return;

  let bullPts = sanitizePathPoints(cycle.prediction_paths.bull || []);
  let bearPts = sanitizePathPoints(cycle.prediction_paths.bear || []);

  const meta = { coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum };

  if (bullPts && bullPts.length > 1) {
    addSinglePathSeries(
      bullPts, 'rgba(255,217,102,0.85)', 'pred_bull',
      `${coinId}_${cycle.cycle_number}_path_bull`, meta,
    );
  }

  if (bearPts && bearPts.length > 1) {
    addSinglePathSeries(
      bearPts, 'rgba(255,107,107,0.85)', 'pred_bear',
      `${coinId}_${cycle.cycle_number}_path_bear`, meta,
    );
  }
}