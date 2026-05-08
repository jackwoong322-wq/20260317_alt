// chart.ts — Main entry point (modular build)
import { initChart } from './chart-render-init.js';
import { setupTooltip } from './chart-render-tooltip.js';
import { buildCoinList, buildCycleToggles, initDefaults } from './chart-ui.js';
import { drawChart } from './chart-draw.js';
import { initLoadStateFromInitial, scheduleBackgroundCyclePreload, } from './chart-lazy-load.js';
function initApp() {
    // [Why] DOMContentLoaded 시 flex 레이아웃 미계산 → createChart 내부 Value is null.
    // 2프레임 대기로 레이아웃 완료 후 차트 생성.
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            initChart();
            setupTooltip();
            initLoadStateFromInitial();
            initDefaults();
            buildCoinList();
            buildCycleToggles();
            drawChart();
            scheduleBackgroundCyclePreload();
        });
    });
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
}
else {
    initApp();
}
