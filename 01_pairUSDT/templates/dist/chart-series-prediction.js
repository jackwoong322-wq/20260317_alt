// ── Prediction path series (bull / bear dotted lines) ──────────────────────
import { chartState } from './chart-logic.js?v=1773826372';
import { dayToTime, buildStepSeries, sanitizePathPoints } from './chart-logic.js?v=1773826372';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js?v=1773826372';
function buildPathLinePoints(rawPts) {
    return rawPts
        .map((p) => {
        const ts = dayToTime(p.x);
        const val = Number(p.value);
        if (ts == null || p.value == null || !Number.isFinite(ts) || !Number.isFinite(val))
            return null;
        return { time: ts, value: val };
    })
        .filter((p) => p !== null);
}
function addSinglePathSeries(pts, color, kind, seriesKey, meta) {
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
export function addPredictionPaths(coinId, coinData, cycle, cycleNum) {
    if (!cycle.prediction_paths)
        return;
    let bullPts = sanitizePathPoints(cycle.prediction_paths.bull || []);
    let bearPts = sanitizePathPoints(cycle.prediction_paths.bear || []);
    const meta = { coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum };
    if (bullPts && bullPts.length > 1) {
        addSinglePathSeries(bullPts, 'rgba(255,217,102,0.85)', 'pred_bull', `${coinId}_${cycle.cycle_number}_path_bull`, meta);
    }
    if (bearPts && bearPts.length > 1) {
        addSinglePathSeries(bearPts, 'rgba(255,107,107,0.85)', 'pred_bear', `${coinId}_${cycle.cycle_number}_path_bear`, meta);
    }
}
