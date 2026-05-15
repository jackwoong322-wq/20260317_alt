import { dayToTime } from './chart-logic.js';
import { setSeriesDataSafe } from './chart-series-helpers.js';
/**
 * 볼린저 밴드(SMA 및 표준편차)를 계산합니다.
 */
export function calculateBollingerBands(data, period = 20, stdDevMultiplier = 2) {
    if (!data || data.length < period)
        return [];
    const bb = [];
    for (let i = period - 1; i < data.length; i++) {
        // 1. Calculate SMA
        let sum = 0;
        for (let j = 0; j < period; j++) {
            const val = Number(data[i - j].close);
            if (!Number.isFinite(val))
                continue; // 안전망
            sum += val;
        }
        const currentSma = sum / period;
        // 2. Calculate Standard Deviation
        let sumSquares = 0;
        for (let j = 0; j < period; j++) {
            const val = Number(data[i - j].close);
            if (!Number.isFinite(val))
                continue;
            sumSquares += Math.pow(val - currentSma, 2);
        }
        const stdDev = Math.sqrt(sumSquares / period);
        bb.push({
            x: data[i].x,
            middle: currentSma,
            upper: currentSma + (stdDev * stdDevMultiplier),
            lower: currentSma - (stdDev * stdDevMultiplier)
        });
    }
    return bb;
}
/**
 * 3개의 라인 시리즈(Upper, Middle, Lower)를 차트에 추가합니다.
 */
export function addBollingerBandsSeries(state, coinId, symbol, cycleName, cycleNum, cycleData, closeKey) {
    if (!cycleData || cycleData.length < 20 || !state.chart)
        return;
    const bbData = calculateBollingerBands(cycleData, 20, 2);
    if (bbData.length === 0)
        return;
    const upperData = [];
    const lowerData = [];
    const middleData = [];
    for (const d of bbData) {
        const ts = dayToTime(d.x);
        if (ts == null)
            continue;
        upperData.push({ time: ts, value: d.upper });
        lowerData.push({ time: ts, value: d.lower });
        middleData.push({ time: ts, value: d.middle });
    }
    const upperSeries = state.chart.addLineSeries({ color: 'rgba(167, 139, 250, 0.4)', lineWidth: 1, lineStyle: 2, title: 'BB Upper' });
    setSeriesDataSafe(upperSeries, upperData, { kind: 'bb_upper', coinId, symbol, cycleName, cycleNum });
    state.seriesMap[`${closeKey}_bb_upper`] = upperSeries;
    const lowerSeries = state.chart.addLineSeries({ color: 'rgba(167, 139, 250, 0.4)', lineWidth: 1, lineStyle: 2, title: 'BB Lower' });
    setSeriesDataSafe(lowerSeries, lowerData, { kind: 'bb_lower', coinId, symbol, cycleName, cycleNum });
    state.seriesMap[`${closeKey}_bb_lower`] = lowerSeries;
    const middleSeries = state.chart.addLineSeries({ color: 'rgba(167, 139, 250, 0.8)', lineWidth: 1, title: 'BB Middle' });
    setSeriesDataSafe(middleSeries, middleData, { kind: 'bb_middle', coinId, symbol, cycleName, cycleNum });
    state.seriesMap[`${closeKey}_bb_middle`] = middleSeries;
}
