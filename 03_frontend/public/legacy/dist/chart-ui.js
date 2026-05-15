// UI interactions: coin list, buttons, search, toggles
import { chartState } from './chart-logic.js';
import { CYCLE_COLORS } from './chart-logic.js';
import { drawChart } from './chart-draw.js';
import { ensureCycleLoaded, findManifestCycle, getDashboardManifest, getCycleDisplayName, getCycleStatus, getManifestCoins, isCycleAvailable, } from './chart-lazy-load.js';
/** 매니페스트 + 이미 로드된 ALL_DATA에서 사이클 번호만 모음 (가짜 1~5 폴백 없음) */
function collectCycleNumbersForCoin(coinId) {
    const nums = new Set();
    const manifestCoin = getManifestCoins().find((c) => c.coin_id === coinId);
    for (const c of manifestCoin?.cycles || []) {
        const n = Number(c.cycle_number);
        if (Number.isFinite(n) && n > 0)
            nums.add(n);
    }
    const coinData = ALL_DATA?.[coinId];
    for (const c of coinData?.cycles || []) {
        const n = Number(c.cycle_number);
        if (Number.isFinite(n) && n > 0)
            nums.add(n);
    }
    return nums;
}
// ── Coin List UI ──────────────────────────────────────
export function buildCoinList(filter = '') {
    const el = document.getElementById('coinList');
    if (!el)
        return;
    el.innerHTML = '';
    const coins = getManifestCoins().filter((d) => {
        return ((d.symbol || '').toLowerCase().includes(filter.toLowerCase()) ||
            (d.name || '').toLowerCase().includes(filter.toLowerCase()));
    });
    coins.forEach((d) => {
        const id = d.coin_id;
        const sel = chartState.selectedCoins.includes(id);
        const div = document.createElement('div');
        div.className = 'coin-item' + (sel ? ' checked active' : '');
        div.dataset.id = id;
        div.innerHTML = `
      <div class="coin-check">
        <svg width="8" height="8" viewBox="0 0 8 8">
          <polyline points="1,4 3,6 7,2" fill="none" stroke="#080c14" stroke-width="1.5"/>
        </svg>
      </div>
      <span class="coin-rank">#${d.rank || '?'}</span>
      <span class="coin-symbol">${d.symbol}</span>
      <span class="coin-name">${d.name}</span>
    `;
        div.onclick = () => {
            void toggleCoin(id, div);
        };
        el.appendChild(div);
    });
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
async function toggleCoin(id, el) {
    const idx = chartState.selectedCoins.indexOf(id);
    if (idx >= 0) {
        // 최소 1개 코인은 항상 선택 상태 유지 (마지막 코인은 해제 불가)
        if (chartState.selectedCoins.length === 1) {
            return;
        }
        chartState.selectedCoins.splice(idx, 1);
        el.classList.remove('checked', 'active');
    }
    else {
        chartState.selectedCoins.push(id);
        el.classList.add('checked', 'active');
    }
    await loadActiveCyclesForSelection();
}
function clearAll() {
    chartState.selectedCoins = [];
    const input = document.getElementById('searchInput');
    buildCoinList(input?.value ?? '');
    drawChart();
}
// ── Cycle Toggles UI ──────────────────────────────────
export function buildCycleToggles() {
    const el = document.getElementById('cycleToggles');
    if (!el)
        return;
    el.innerHTML = '';
    const cycleNums = new Set();
    chartState.selectedCoins.forEach((id) => {
        collectCycleNumbersForCoin(id).forEach((n) => cycleNums.add(n));
    });
    // activeCycles 에 현재 표시 가능한 사이클이 하나도 없으면
    // 가장 최신 사이클(최대 cycle 번호)을 기본 선택으로 설정
    const hasActiveInView = Array.from(cycleNums).some((n) => chartState.activeCycles.has(n));
    if (cycleNums.size > 0 && !hasActiveInView) {
        const maxCycle = Math.max(...Array.from(cycleNums));
        chartState.activeCycles = new Set([maxCycle]);
    }
    [...cycleNums].sort().forEach((n) => {
        const col = CYCLE_COLORS[n] || CYCLE_COLORS[1];
        let name = `CYCLE ${n}`;
        for (const id of chartState.selectedCoins) {
            const found = findManifestCycle(id, n);
            if (found) {
                name = getCycleDisplayName(id, n).toUpperCase();
                break;
            }
        }
        const btn = document.createElement('button');
        btn.className = 'cycle-btn';
        const active = chartState.activeCycles.has(n);
        const statuses = chartState.selectedCoins.map((coinId) => ({
            available: isCycleAvailable(coinId, n),
            status: getCycleStatus(coinId, n),
        }));
        const hasUnavailable = statuses.some((item) => !item.available);
        const hasLoading = statuses.some((item) => item.status === 'loading');
        const hasError = statuses.some((item) => item.status === 'error');
        const allEmpty = statuses.length > 0 &&
            statuses.every((item) => !item.available || item.status === 'empty');
        const allLoaded = statuses.length > 0 &&
            statuses.every((item) => !item.available ||
                item.status === 'loaded' ||
                item.status === 'empty');
        btn.style.cssText = active
            ? `border-color:${col.main};color:${col.main};background:${col.band}`
            : 'border-color:#1e2d45;color:#4a6080;background:transparent';
        if (hasUnavailable) {
            btn.style.opacity = '0.45';
        }
        if (hasError) {
            btn.style.borderColor = '#ff4466';
            btn.style.color = '#ff92aa';
        }
        else if (hasLoading) {
            btn.style.borderColor = '#FFB800';
            btn.style.color = '#FFB800';
        }
        else if (allEmpty) {
            btn.style.borderColor = '#4a6080';
            btn.style.color = '#6882a7';
        }
        else if (allLoaded && !active) {
            btn.style.borderColor = '#2d4a68';
        }
        btn.textContent = hasLoading
            ? `${name} LOADING`
            : hasError
                ? `${name} ERROR`
                : allEmpty
                    ? `${name} EMPTY`
                    : name;
        btn.onclick = () => {
            if (chartState.activeCycles.has(n))
                chartState.activeCycles.delete(n);
            else
                chartState.activeCycles.add(n);
            void loadActiveCyclesForSelection();
        };
        el.appendChild(btn);
    });
}
window.buildCycleToggles = buildCycleToggles;
function toggleHighLow() {
    chartState.showHighLow = !chartState.showHighLow;
    const btn = document.getElementById('toggleRange');
    if (btn) {
        btn.style.cssText = chartState.showHighLow
            ? 'border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,0.1)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
    drawChart();
}
function toggleBoxZone() {
    chartState.showBoxZone = !chartState.showBoxZone;
    const btn = document.getElementById('toggleBox');
    if (btn) {
        btn.style.cssText = chartState.showBoxZone
            ? 'border-color:#FFB800;color:#FFB800;background:rgba(255,184,0,0.1)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
    drawChart();
}
function toggleBearBull() {
    chartState.showPrediction = !chartState.showPrediction;
    if (!chartState.showPrediction) {
        chartState.showExtendedForecast = false;
    }
    const btn = document.getElementById('toggleBearBull');
    if (btn) {
        btn.style.cssText = chartState.showPrediction
            ? 'border-color:#ff6bb5;color:#ff6bb5;background:rgba(255,107,181,0.1)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
    updateExtendedForecastButton();
    drawChart();
}
function updateExtendedForecastButton() {
    const btn = document.getElementById('toggleExtendedForecast');
    if (!btn)
        return;
    btn.disabled = !chartState.showPrediction;
    btn.style.cssText =
        chartState.showPrediction && chartState.showExtendedForecast
            ? 'border-color:#a78bfa;color:#d8ccff;background:rgba(167,139,250,0.12)'
            : chartState.showPrediction
                ? 'border-color:#4a6080;color:#4a6080;'
                : 'border-color:#26364f;color:#344966;opacity:0.55;';
}
function toggleExtendedForecast() {
    if (!chartState.showPrediction)
        return;
    chartState.showExtendedForecast = !chartState.showExtendedForecast;
    updateExtendedForecastButton();
    drawChart();
}
function toggleSubBox() {
    chartState.showSubBox = !chartState.showSubBox;
    const btn = document.getElementById('toggleSubBox');
    if (btn) {
        btn.style.cssText = chartState.showSubBox
            ? 'border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,0.10)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
    drawChart();
}
// ── Defaults & Bottom Override UI ─────────────────────
export function initDefaults() {
    const manifest = getDashboardManifest() || {};
    if (typeof manifest.default_coin_id === 'string' &&
        getManifestCoins().some((coin) => coin.coin_id === manifest.default_coin_id)) {
        chartState.selectedCoins = [manifest.default_coin_id];
    }
    if (Number.isFinite(Number(manifest.default_cycle_number))) {
        chartState.activeCycles = new Set([Number(manifest.default_cycle_number)]);
    }
    else {
        // 기본 코인: BTC 자동 선택 (이미 selectedCoins 에 세팅되어 있음)
        // 기본 사이클: CURRENT / 최신 사이클을 포함해 존재하는 사이클 중 최대 번호를 활성화
        const allCycleNums = new Set();
        getManifestCoins().forEach((coin) => {
            (coin.cycles || []).forEach((c) => allCycleNums.add(Number(c.cycle_number)));
        });
        if (allCycleNums.size > 0) {
            const maxCycle = Math.max(...Array.from(allCycleNums.values()));
            chartState.activeCycles = new Set([maxCycle]);
        }
    }
    // BOX ZONE 기본 활성화 버튼 스타일 동기화
    const boxBtn = document.getElementById('toggleBox');
    if (boxBtn) {
        boxBtn.style.cssText = chartState.showBoxZone
            ? 'border-color:#FFB800;color:#FFB800;background:rgba(255,184,0,0.1)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
    const predictionBtn = document.getElementById('toggleBearBull');
    if (predictionBtn) {
        predictionBtn.style.cssText = chartState.showPrediction
            ? 'border-color:#ff6bb5;color:#ff6bb5;background:rgba(255,107,181,0.1)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
    updateExtendedForecastButton();
    const subBoxBtn = document.getElementById('toggleSubBox');
    if (subBoxBtn) {
        subBoxBtn.style.cssText = chartState.showSubBox
            ? 'border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,0.10)'
            : 'border-color:#4a6080;color:#4a6080;';
    }
}
// ── Wire DOM events & expose toggles for onclick ───────
const searchInput = document.getElementById('searchInput');
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        const target = e.target;
        buildCoinList(target?.value ?? '');
    });
}
window.toggleHighLow = toggleHighLow;
window.toggleBoxZone = toggleBoxZone;
window.toggleBearBull = toggleBearBull;
window.toggleExtendedForecast = toggleExtendedForecast;
window.toggleSubBox = toggleSubBox;
