// Chart initialization & global error handling
import { chartState } from './chart-logic.js?v=1773826372';
import { scheduleRedrawBoxMarks } from './chart-render-overlays.js?v=1773826372';
// lightweight-charts Value is null 에러 감지용 전역 핸들러
window.addEventListener('error', (e) => {
    const msg = e.message ?? e.error?.message ?? '';
    if (msg.includes('Value is null')) {
        const count = (window.__nullErrorCount ?? 0) + 1;
        window.__nullErrorCount = count;
        const err = e.error;
        console.warn('[VALUE_IS_NULL]', count, msg, err?.stack);
    }
});
const MIN_CHART_WIDTH = 400;
const MIN_CHART_HEIGHT = 300;
// ── Init Chart ────────────────────────────────────────
export function initChart() {
    const el = document.getElementById('chart');
    if (!el)
        return;
    const cw = el.clientWidth ?? 0;
    const ch = el.clientHeight ?? 0;
    const w = Math.max(cw, MIN_CHART_WIDTH);
    const h = Math.max(ch, MIN_CHART_HEIGHT);
    chartState.chart = LightweightCharts.createChart(el, {
        width: w,
        height: h,
        layout: {
            background: { color: '#080c14' },
            textColor: '#c8d8f0',
        },
        grid: {
            vertLines: { color: '#1e2d45' },
            horzLines: { color: '#1e2d45' },
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: {
            borderColor: '#1e2d45',
            scaleMargins: { top: 0.05, bottom: 0.05 },
        },
        localization: {
            timeFormatter: (v) => `Day ${v}`,
        },
        timeScale: {
            borderColor: '#1e2d45',
            tickMarkFormatter: (v) => `Day ${v}`,
        },
        handleScroll: true,
        handleScale: true,
    });
    new ResizeObserver(() => {
        if (!chartState.chart)
            return;
        const width = el.clientWidth ?? 0;
        const height = el.clientHeight ?? 0;
        if (width > 0 && height > 0) {
            chartState.chart.applyOptions({ width, height });
        }
    }).observe(el);
    chartState.chart.timeScale().subscribeVisibleTimeRangeChange(() => scheduleRedrawBoxMarks());
    chartState.chart.timeScale().subscribeVisibleLogicalRangeChange(() => scheduleRedrawBoxMarks());
}
