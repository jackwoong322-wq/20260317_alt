// chart.ts — Main entry point (modular build)
const V = '?v=1778932100';
const base = location.protocol === 'file:' ? './dist/' : '/legacy/dist/';

const { initChart }                 = await import(base + 'chart-render-init.js' + V);
const { setupTooltip }              = await import(base + 'chart-render-tooltip.js' + V);
const { buildCoinList, buildCycleToggles, initDefaults } = await import(base + 'chart-ui.js' + V);
const { drawChart }                 = await import(base + 'chart-draw.js' + V);
const { initLoadStateFromInitial }  = await import(base + 'chart-lazy-load.js' + V);

function initApp() {
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            initChart();
            setupTooltip();
            initLoadStateFromInitial();
            initDefaults();
            buildCoinList();
            buildCycleToggles();
            drawChart();
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
