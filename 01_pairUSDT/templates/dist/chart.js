// chart.ts — Main entry point (modular build)
import { initChart } from './chart-render-init.js?v=1773826372';
import { setupTooltip } from './chart-render-tooltip.js?v=1773826372';
import { buildCoinList, buildCycleToggles, initDefaults } from './chart-ui.js?v=1773826372';
import { drawChart } from './chart-draw.js?v=1773826372';
function initApp() {
    // [Why] DOMContentLoaded 시 flex 레이아웃 미계산 → createChart 내부 Value is null.
    // 2프레임 대기로 레이아웃 완료 후 차트 생성.
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            initChart();
            setupTooltip();
            initDefaults();
            buildCoinList();
            buildCycleToggles();
            drawChart();
        });
    });
}
document.addEventListener('DOMContentLoaded', initApp);
