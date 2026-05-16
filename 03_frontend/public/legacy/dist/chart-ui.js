// UI interactions: coin select, cycle select, show select
import { chartState } from './chart-logic.js';
import { CYCLE_COLORS } from './chart-logic.js';
import { drawChart } from './chart-draw.js';
import { ensureCycleLoaded, findManifestCycle, getDashboardManifest, getCycleDisplayName, getCycleStatus, getManifestCoins, isCycleAvailable, } from './chart-lazy-load.js';

/** 매니페스트 + ALL_DATA에서 사이클 번호 수집 */
function collectCycleNumbersForCoin(coinId) {
    const nums = new Set();
    const manifestCoin = getManifestCoins().find((c) => c.coin_id === coinId);
    for (const c of manifestCoin?.cycles || []) {
        const n = Number(c.cycle_number);
        if (Number.isFinite(n) && n > 0) nums.add(n);
    }
    const coinData = ALL_DATA?.[coinId];
    for (const c of coinData?.cycles || []) {
        const n = Number(c.cycle_number);
        if (Number.isFinite(n) && n > 0) nums.add(n);
    }
    return nums;
}

// ── Coin Select UI ────────────────────────────────────
export function buildCoinList(_filter = '') {
    const select = document.getElementById('coinSelect');
    if (!select) return;

    const coins = getManifestCoins();
    const currentVal = chartState.selectedCoins[0] || '';

    select.innerHTML = '';
    coins.forEach((d) => {
        const opt = document.createElement('option');
        opt.value = d.coin_id;
        opt.textContent = `${d.symbol}  ${d.name}`;
        if (d.coin_id === currentVal) opt.selected = true;
        select.appendChild(opt);
    });

    // 처음 빌드 시 onChange 등록 (중복 방지)
    if (!select.dataset.wired) {
        select.dataset.wired = '1';
        select.onchange = () => {
            const selected = Array.from(select.selectedOptions).map((o) => o.value);
            // 최소 1개 선택 유지
            chartState.selectedCoins = selected.length > 0 ? selected : chartState.selectedCoins;
            void loadActiveCyclesForSelection();
        };
    }
    // size 자동 조정 (최대 8)
    select.size = Math.min(coins.length || 1, 8);
}

async function loadActiveCyclesForSelection() {
    const tasks = [];
    chartState.selectedCoins.forEach((coinId) => {
        chartState.activeCycles.forEach((cycleNumber) => {
            if (isCycleAvailable(coinId, cycleNumber)) {
                tasks.push(ensureCycleLoaded(coinId, cycleNumber, true, false));
            }
        });
    });
    buildCycleToggles();
    await Promise.allSettled(tasks);
    buildCycleToggles();
    drawChart();
}

// ── Cycle Select UI ────────────────────────────────────
export function buildCycleToggles() {
    const select = document.getElementById('cycleSelect');
    if (!select) return;

    const cycleNums = new Set();
    chartState.selectedCoins.forEach((id) => {
        collectCycleNumbersForCoin(id).forEach((n) => cycleNums.add(n));
    });

    // 활성 사이클이 없으면 최신 사이클 기본 선택
    const hasActiveInView = Array.from(cycleNums).some((n) => chartState.activeCycles.has(n));
    if (cycleNums.size > 0 && !hasActiveInView) {
        const maxCycle = Math.max(...Array.from(cycleNums));
        chartState.activeCycles = new Set([maxCycle]);
    }

    // 현재 선택 상태 보존 후 재빌드
    select.innerHTML = '';
    [...cycleNums].sort().forEach((n) => {
        let name = `CYCLE ${n}`;
        for (const id of chartState.selectedCoins) {
            const found = findManifestCycle(id, n);
            if (found) {
                name = getCycleDisplayName(id, n).toUpperCase();
                break;
            }
        }

        const statuses = chartState.selectedCoins.map((coinId) => ({
            available: isCycleAvailable(coinId, n),
            status: getCycleStatus(coinId, n),
        }));
        const hasLoading = statuses.some((s) => s.status === 'loading');
        const hasError   = statuses.some((s) => s.status === 'error');
        const allEmpty   = statuses.length > 0 && statuses.every((s) => !s.available || s.status === 'empty');

        const label = hasLoading ? `${name} ⟳`
                    : hasError   ? `${name} ✕`
                    : allEmpty   ? `${name} —`
                    : name;

        const opt = document.createElement('option');
        opt.value = String(n);
        opt.textContent = label;
        opt.selected = chartState.activeCycles.has(n);
        select.appendChild(opt);
    });

    // 표시 크기 자동 조정 (최대 5)
    select.size = Math.min(cycleNums.size || 1, 5);

    // onChange 등록 (중복 방지)
    if (!select.dataset.wired) {
        select.dataset.wired = '1';
        select.onchange = () => {
            chartState.activeCycles = new Set(
                Array.from(select.selectedOptions).map((o) => Number(o.value))
            );
            void loadActiveCyclesForSelection();
        };
    }
}
window.buildCycleToggles = buildCycleToggles;

// ── Show Select UI ─────────────────────────────────────
function syncShowSelect() {
    const select = document.getElementById('showSelect');
    if (!select) return;
    for (const opt of select.options) {
        switch (opt.value) {
            case 'highlow':  opt.selected = chartState.showHighLow;           break;
            case 'boxzone':  opt.selected = chartState.showBoxZone;            break;
            case 'predict':  opt.selected = chartState.showPrediction;         break;
            case 'extended': opt.selected = chartState.showExtendedForecast;   break;
            case 'subbox':   opt.selected = chartState.showSubBox;             break;
            case 'bb':       opt.selected = chartState.showBB;                 break;
        }
    }
}

function initShowSelect() {
    const select = document.getElementById('showSelect');
    if (!select || select.dataset.wired) return;
    select.dataset.wired = '1';

    // 초기 상태 동기화
    syncShowSelect();

    select.onchange = () => {
        const vals = new Set(Array.from(select.selectedOptions).map((o) => o.value));
        chartState.showHighLow          = vals.has('highlow');
        chartState.showBoxZone          = vals.has('boxzone');
        chartState.showPrediction       = vals.has('predict');
        chartState.showExtendedForecast = vals.has('extended') && vals.has('predict');
        chartState.showSubBox           = vals.has('subbox');
        chartState.showBB               = vals.has('bb');
        drawChart();
    };

    // CYCLES select size: 옵션 수에 맞게
    select.size = select.options.length;
}

// ── Defaults ─────────────────────────────────────────
export function initDefaults() {
    const manifest = getDashboardManifest() || {};
    if (typeof manifest.default_coin_id === 'string' &&
        getManifestCoins().some((coin) => coin.coin_id === manifest.default_coin_id)) {
        chartState.selectedCoins = [manifest.default_coin_id];
    }
    if (Number.isFinite(Number(manifest.default_cycle_number))) {
        chartState.activeCycles = new Set([Number(manifest.default_cycle_number)]);
    } else {
        const allCycleNums = new Set();
        getManifestCoins().forEach((coin) => {
            (coin.cycles || []).forEach((c) => allCycleNums.add(Number(c.cycle_number)));
        });
        if (allCycleNums.size > 0) {
            const maxCycle = Math.max(...Array.from(allCycleNums.values()));
            chartState.activeCycles = new Set([maxCycle]);
        }
    }

    initShowSelect();
}

// ── Legacy toggle functions (공존용 — showSelect onChange가 주 경로) ──
function toggleHighLow()          { chartState.showHighLow          = !chartState.showHighLow;          syncShowSelect(); drawChart(); }
function toggleBoxZone()          { chartState.showBoxZone          = !chartState.showBoxZone;          syncShowSelect(); drawChart(); }
function toggleBearBull()         { chartState.showPrediction       = !chartState.showPrediction;       syncShowSelect(); drawChart(); }
function toggleExtendedForecast() { if (!chartState.showPrediction) return; chartState.showExtendedForecast = !chartState.showExtendedForecast; syncShowSelect(); drawChart(); }
function toggleSubBox()           { chartState.showSubBox           = !chartState.showSubBox;           syncShowSelect(); drawChart(); }
function toggleBB()               { chartState.showBB               = !chartState.showBB;               syncShowSelect(); drawChart(); }

window.toggleHighLow = toggleHighLow;
window.toggleBoxZone = toggleBoxZone;
window.toggleBearBull = toggleBearBull;
window.toggleExtendedForecast = toggleExtendedForecast;
window.toggleSubBox = toggleSubBox;
window.toggleBB = toggleBB;
