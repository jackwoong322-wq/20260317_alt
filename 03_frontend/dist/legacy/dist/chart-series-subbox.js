// Sub-box layer: internal ranges inside the current active macro box.
import { chartState, dayToTime } from './chart-logic.js';
import { setSeriesDataSafe, filterValidPoints } from './chart-series-helpers.js';
import { renderSubBoxMarks } from './chart-render-overlays.js';
function isValidSubBox(box) {
    return (box != null &&
        Number.isFinite(Number(box.startX)) &&
        Number.isFinite(Number(box.endX)) &&
        Number.isFinite(Number(box.upper)) &&
        Number.isFinite(Number(box.lower)) &&
        Number(box.startX) <= Number(box.endX) &&
        Number(box.upper) >= Number(box.lower));
}
function addSubBoxBand(box, keyPrefix, isCandidate, meta) {
    const start = Number(box.startX);
    const end = Number(box.endX);
    const upper = Number(box.upper);
    const lower = Number(box.lower);
    const t1 = dayToTime(start);
    const t2 = dayToTime(end);
    const color = isCandidate ? 'rgba(255,217,102,0.90)' : 'rgba(0,212,255,0.88)';
    const fillTop = isCandidate ? 'rgba(255,217,102,0.080)' : 'rgba(0,212,255,0.075)';
    const fillBottom = isCandidate ? 'rgba(255,217,102,0.006)' : 'rgba(0,212,255,0.006)';
    const lineStyle = isCandidate
        ? LightweightCharts.LineStyle.Dotted
        : LightweightCharts.LineStyle.Dashed;
    const hiLine = chartState.chart.addLineSeries({
        color,
        lineWidth: isCandidate ? 1 : 1.5,
        lineStyle,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    setSeriesDataSafe(hiLine, filterValidPoints([{ time: t1, value: upper }, { time: t2, value: upper }]), { kind: isCandidate ? 'subbox_candidate_hi' : 'subbox_hi', ...meta });
    chartState.seriesMap[`${keyPrefix}_sub_hi`] = hiLine;
    const loLine = chartState.chart.addLineSeries({
        color,
        lineWidth: isCandidate ? 1 : 1.5,
        lineStyle,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    setSeriesDataSafe(loLine, filterValidPoints([{ time: t1, value: lower }, { time: t2, value: lower }]), { kind: isCandidate ? 'subbox_candidate_lo' : 'subbox_lo', ...meta });
    chartState.seriesMap[`${keyPrefix}_sub_lo`] = loLine;
    const fill = chartState.chart.addAreaSeries({
        topColor: fillTop,
        bottomColor: fillBottom,
        lineColor: 'rgba(0,0,0,0)',
        lineWidth: 0,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    fill.applyOptions({ baseValue: { type: 'price', price: lower } });
    setSeriesDataSafe(fill, filterValidPoints([{ time: t1, value: upper }, { time: t2, value: upper }]), { kind: isCandidate ? 'subbox_candidate_fill' : 'subbox_fill', ...meta });
    chartState.seriesMap[`${keyPrefix}_sub_fill`] = fill;
}
export function addSubBoxSeries(coinId, coinData, cycle, cycleNum, lineSeries) {
    if (!chartState.showSubBox || !lineSeries || !chartState.chart)
        return;
    const subBoxes = Array.isArray(cycle.sub_boxes)
        ? cycle.sub_boxes.filter(isValidSubBox)
        : [];
    const candidates = Array.isArray(cycle.sub_box_candidates)
        ? cycle.sub_box_candidates.filter(isValidSubBox)
        : [];
    if (subBoxes.length === 0 && candidates.length === 0)
        return;
    const meta = {
        coinId,
        symbol: coinData.symbol,
        cycleName: cycle.cycle_name,
        cycleNum,
    };
    subBoxes.forEach((box, idx) => {
        addSubBoxBand(box, `${coinId}_${cycle.cycle_number}_sub_${idx}`, false, meta);
    });
    candidates.forEach((box, idx) => {
        addSubBoxBand(box, `${coinId}_${cycle.cycle_number}_subcand_${idx}`, true, meta);
    });
    setTimeout(() => {
        if (!chartState.chart)
            return;
        renderSubBoxMarks(subBoxes, candidates, chartState.chart.timeScale(), lineSeries, coinId, coinData.symbol, cycle.cycle_number);
    }, 90);
}
