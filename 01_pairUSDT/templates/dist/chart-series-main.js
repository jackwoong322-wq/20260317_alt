import { dayToTime } from './chart-logic.js?v=1773826372';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js?v=1773826372';
import { LINE_WIDTH_SINGLE, LINE_WIDTH_MULTI } from './chart-constants.js?v=1773826372';
export function buildMainLineData(cycleData, minLowDay) {
    return cycleData
        .filter((d) => d.x != null)
        .map((d) => {
        const ts = dayToTime(d.x);
        if (ts == null)
            return null;
        return {
            time: ts,
            value: minLowDay != null && d.x <= minLowDay ? d.low : d.high,
        };
    })
        .filter((p) => p !== null);
}
export function buildFallbackCloseData(coinId, symbol, cycleName, cycleNum, cycleData) {
    const fallback = cycleData
        .filter((d) => d.x != null && d.close != null && Number.isFinite(Number(d.close)))
        .map((d) => {
        const ts = dayToTime(d.x);
        if (ts == null)
            return null;
        return { time: ts, value: d.close };
    })
        .filter((p) => p !== null);
    return filterValidPoints(fallback);
}
export function addMainLineSeries(state, coinId, coinData, cycle, color, isCurr, cycleNum, cycleMinLowIdx, closeKey) {
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
