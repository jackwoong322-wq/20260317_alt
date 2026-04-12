// ── Bear/Bull background area series ───────────────────
import { chartState } from './chart-logic.js?v=1773826372';
import { dayToTime, detectBearBull } from './chart-logic.js?v=1773826372';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js?v=1773826372';
function getBearBullColors(type) {
    return type === 'BEAR'
        ? { bgColor: 'rgba(255,68,102,0.07)', lineCol: 'rgba(255,68,102,0.0)' }
        : { bgColor: 'rgba(0,255,136,0.07)', lineCol: 'rgba(0,255,136,0.0)' };
}
function getMaxCloseValue(cycleData) {
    const maxClose = cycleData
        .map((d) => d.close)
        .reduce((m, v) => (Number.isFinite(Number(v)) ? Math.max(m, Number(v)) : m), -Infinity);
    // 유효한 close 값이 하나도 없으면 null 반환 → 시리즈 추가 자체를 skip
    if (!Number.isFinite(maxClose))
        return null;
    return maxClose * 1.05;
}
function addBearBullSegmentSeries(seg, si, cycle, coinId, coinData, cycleNum) {
    const { bgColor, lineCol } = getBearBullColors(seg.type);
    const bgSeries = chartState.chart.addAreaSeries({
        topColor: bgColor,
        bottomColor: bgColor,
        lineColor: lineCol,
        lineWidth: 0,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    const maxV = getMaxCloseValue(cycle.data);
    if (maxV === null)
        return; // 유효한 close 데이터 없음 → skip
    const bt1 = dayToTime(seg.startX);
    const bt2 = dayToTime(seg.endX);
    if (bt1 != null && bt2 != null && Number.isFinite(bt1) && Number.isFinite(bt2)) {
        setSeriesDataSafe(bgSeries, filterValidPoints([{ time: bt1, value: maxV }, { time: bt2, value: maxV }]), { kind: 'bearbull_bg', coinId, symbol: coinData.symbol, cycleName: cycle.cycle_name, cycleNum });
    }
    chartState.seriesMap[`${coinId}_${cycle.cycle_number}_bb${si}`] = bgSeries;
}
export function addBearBullSeries(coinId, coinData, cycle, cycleNum, lineSeries) {
    if (!chartState.showBearBull || chartState.selectedCoins.length !== 1)
        return;
    const segs = detectBearBull(cycle.data);
    segs.forEach((seg, si) => {
        addBearBullSegmentSeries(seg, si, cycle, coinId, coinData, cycleNum);
    });
    setTimeout(() => {
        const ts = chartState.chart.timeScale();
        const segs2 = detectBearBull(cycle.data);
        renderBearBullLabels(segs2, ts, lineSeries);
    }, 80);
}
