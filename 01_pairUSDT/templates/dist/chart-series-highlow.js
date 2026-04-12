// ── High / Low dotted line series ──────────────────────
import { chartState } from './chart-logic.js?v=1773826372';
import { dayToTime } from './chart-logic.js?v=1773826372';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js?v=1773826372';
function buildOhlcFieldData(cycleData, field) {
    return filterValidPoints(cycleData
        .filter((d) => d.x != null)
        .map((d) => {
        const ts = dayToTime(d.x);
        if (ts == null)
            return null;
        return { time: ts, value: d[field] };
    })
        .filter((p) => p !== null));
}
function addSingleHiLoSeries(color, data, kind, meta) {
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
export function addHighLowSeries(coinId, coinData, cycle, color, cycleNum) {
    const meta = { coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum };
    const hiData = buildOhlcFieldData(cycle.data, 'high');
    const hiSeries = addSingleHiLoSeries(color, hiData, 'hi', meta);
    chartState.seriesMap[`${coinId}_${cycle.cycle_number}_hi`] = hiSeries;
    const loData = buildOhlcFieldData(cycle.data, 'low');
    const loSeries = addSingleHiLoSeries(color, loData, 'lo', meta);
    chartState.seriesMap[`${coinId}_${cycle.cycle_number}_lo`] = loSeries;
}
