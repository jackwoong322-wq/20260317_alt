// chart-ui.js — 커스텀 드롭다운 (이슈 #101: 방향 B)
import { chartState } from './chart-logic.js';
import { CYCLE_COLORS } from './chart-logic.js';
import { drawChart } from './chart-draw.js';
import { ensureCycleLoaded, findManifestCycle, getDashboardManifest, getCycleDisplayName,
         getCycleStatus, getManifestCoins, isCycleAvailable } from './chart-lazy-load.js';

// ── 공통 유틸 ─────────────────────────────────────────

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

/**
 * 커스텀 드롭다운 패널 열기/닫기 관리
 * 하나가 열리면 나머지는 닫힘
 */
function initDropdownToggle(triggerId, panelId) {
    const trigger = document.getElementById(triggerId);
    const panel   = document.getElementById(panelId);
    if (!trigger || !panel || trigger.dataset.wired) return;
    trigger.dataset.wired = '1';

    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = panel.classList.contains('open');
        // 모든 패널 닫기
        document.querySelectorAll('.dropdown-panel.open')
                .forEach((p) => p.classList.remove('open'));
        document.querySelectorAll('.dropdown-trigger.active')
                .forEach((t) => t.classList.remove('active'));
        if (!isOpen) {
            panel.classList.add('open');
            trigger.classList.add('active');
        }
    });
}

/** 외부 클릭 시 모든 드롭다운 닫기 (최초 1회 등록) */
if (!window.__dropdownOutsideWired) {
    window.__dropdownOutsideWired = true;
    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-panel.open')
                .forEach((p) => p.classList.remove('open'));
        document.querySelectorAll('.dropdown-trigger.active')
                .forEach((t) => t.classList.remove('active'));
    });
}

/** trigger 버튼 레이블 업데이트 */
function updateTriggerLabel(triggerId, items, emptyText = 'None') {
    const trigger = document.getElementById(triggerId);
    if (!trigger) return;
    const label = trigger.querySelector('.trigger-label');
    if (!label) return;
    label.textContent = items.length === 0 ? emptyText
                      : items.length <= 3  ? items.join(', ')
                      : `${items[0]}, ${items[1]} +${items.length - 2}`;
}

// ── COIN 드롭다운 ──────────────────────────────────────

export function buildCoinList(_filter = '') {
    const panel = document.getElementById('coinPanel');
    if (!panel) return;

    const coins = getManifestCoins();
    panel.innerHTML = '';

    coins.forEach((d) => {
        const isSelected = chartState.selectedCoins.includes(d.coin_id);
        const item = document.createElement('div');
        item.className = 'dropdown-item' + (isSelected ? ' selected' : '');
        item.dataset.id = d.coin_id;
        item.innerHTML = `
          <div class="dropdown-check">${isSelected ? '<svg width="9" height="9" viewBox="0 0 9 9"><polyline points="1,5 3.5,7.5 8,2" fill="none" stroke="#080c14" stroke-width="1.8"/></svg>' : ''}</div>
          <span class="di-symbol">${d.symbol}</span>
          <span class="di-name">${d.name}</span>
        `;
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = chartState.selectedCoins.indexOf(d.coin_id);
            if (idx >= 0) {
                // 마지막 코인은 해제 불가
                if (chartState.selectedCoins.length === 1) return;
                chartState.selectedCoins.splice(idx, 1);
            } else {
                chartState.selectedCoins.push(d.coin_id);
            }
            buildCoinList();
            void loadActiveCyclesForSelection();
        });
        panel.appendChild(item);
    });

    // 트리거 레이블 업데이트
    updateTriggerLabel('coinTrigger',
        chartState.selectedCoins.map((id) => {
            const c = coins.find((x) => x.coin_id === id);
            return c?.symbol ?? id;
        })
    );

    // 드롭다운 토글 초기화 (1회)
    initDropdownToggle('coinTrigger', 'coinPanel');
}

// ── CYCLE 드롭다운 ─────────────────────────────────────

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

export function buildCycleToggles() {
    const panel = document.getElementById('cyclePanel');
    if (!panel) return;

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

    panel.innerHTML = '';
    [...cycleNums].sort().forEach((n) => {
        let name = `CYCLE ${n}`;
        for (const id of chartState.selectedCoins) {
            const found = findManifestCycle(id, n);
            if (found) { name = getCycleDisplayName(id, n).toUpperCase(); break; }
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
        const col = CYCLE_COLORS[n] || CYCLE_COLORS[1];
        const isSelected = chartState.activeCycles.has(n);

        const item = document.createElement('div');
        item.className = 'dropdown-item' + (isSelected ? ' selected' : '');
        item.innerHTML = `
          <div class="dropdown-check">${isSelected ? '<svg width="9" height="9" viewBox="0 0 9 9"><polyline points="1,5 3.5,7.5 8,2" fill="none" stroke="#080c14" stroke-width="1.8"/></svg>' : ''}</div>
          <span class="di-symbol" style="color:${col.main}">${label}</span>
        `;
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            if (chartState.activeCycles.has(n)) {
                if (chartState.activeCycles.size === 1) return; // 마지막 사이클 해제 불가
                chartState.activeCycles.delete(n);
            } else {
                chartState.activeCycles.add(n);
            }
            void loadActiveCyclesForSelection();
        });
        panel.appendChild(item);
    });

    // 트리거 레이블 업데이트
    updateTriggerLabel('cycleTrigger',
        [...chartState.activeCycles].sort().map((n) => {
            let name = `C${n}`;
            for (const id of chartState.selectedCoins) {
                const found = findManifestCycle(id, n);
                if (found) { name = getCycleDisplayName(id, n); break; }
            }
            return name;
        })
    );

    initDropdownToggle('cycleTrigger', 'cyclePanel');
}
window.buildCycleToggles = buildCycleToggles;

// ── SHOW 드롭다운 ──────────────────────────────────────

const SHOW_OPTIONS = [
    { value: 'highlow',  label: 'HIGH / LOW',   key: 'showHighLow' },
    { value: 'boxzone',  label: 'BOX ZONE',      key: 'showBoxZone' },
    { value: 'predict',  label: 'PREDICT',       key: 'showPrediction' },
    { value: 'extended', label: 'EXTENDED',      key: 'showExtendedForecast' },
    { value: 'subbox',   label: 'SUB-BOX',       key: 'showSubBox' },
    { value: 'bb',       label: 'BB (20,2)',      key: 'showBB' },
];

function buildShowDropdown() {
    const panel = document.getElementById('showPanel');
    if (!panel || panel.dataset.built) return;
    panel.dataset.built = '1';

    SHOW_OPTIONS.forEach((opt) => {
        const item = document.createElement('div');
        const isSelected = !!chartState[opt.key];
        item.className = 'dropdown-item' + (isSelected ? ' selected' : '');
        item.dataset.val = opt.value;
        item.innerHTML = `
          <div class="dropdown-check">${isSelected ? '<svg width="9" height="9" viewBox="0 0 9 9"><polyline points="1,5 3.5,7.5 8,2" fill="none" stroke="#080c14" stroke-width="1.8"/></svg>' : ''}</div>
          <span class="di-symbol">${opt.label}</span>
        `;
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            // EXTENDED는 PREDICT가 켜져 있어야 함
            if (opt.value === 'extended' && !chartState.showPrediction) return;
            chartState[opt.key] = !chartState[opt.key];
            if (!chartState.showPrediction) chartState.showExtendedForecast = false;
            syncShowDropdown();
            drawChart();
        });
        panel.appendChild(item);
    });

    initDropdownToggle('showTrigger', 'showPanel');
    syncShowDropdown();
}

function syncShowDropdown() {
    const panel = document.getElementById('showPanel');
    if (!panel) return;

    SHOW_OPTIONS.forEach((opt) => {
        const item = panel.querySelector(`[data-val="${opt.value}"]`);
        if (!item) return;
        const isSelected = !!chartState[opt.key];
        item.className = 'dropdown-item' + (isSelected ? ' selected' : '');
        const check = item.querySelector('.dropdown-check');
        if (check) {
            check.innerHTML = isSelected
                ? '<svg width="9" height="9" viewBox="0 0 9 9"><polyline points="1,5 3.5,7.5 8,2" fill="none" stroke="#080c14" stroke-width="1.8"/></svg>'
                : '';
        }
        // EXTENDED는 PREDICT 꺼지면 dim
        if (opt.value === 'extended') {
            item.style.opacity = chartState.showPrediction ? '1' : '0.35';
        }
    });

    // 트리거 레이블
    const active = SHOW_OPTIONS.filter((o) => chartState[o.key]).map((o) => o.label);
    updateTriggerLabel('showTrigger', active, 'None');
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
    buildShowDropdown();
}

// ── Legacy toggle stubs (기존 코드 호환) ──────────────
function toggleHighLow()          { chartState.showHighLow          = !chartState.showHighLow;          syncShowDropdown(); drawChart(); }
function toggleBoxZone()          { chartState.showBoxZone          = !chartState.showBoxZone;          syncShowDropdown(); drawChart(); }
function toggleBearBull()         { chartState.showPrediction       = !chartState.showPrediction;       syncShowDropdown(); drawChart(); }
function toggleExtendedForecast() { if (!chartState.showPrediction) return; chartState.showExtendedForecast = !chartState.showExtendedForecast; syncShowDropdown(); drawChart(); }
function toggleSubBox()           { chartState.showSubBox           = !chartState.showSubBox;           syncShowDropdown(); drawChart(); }
function toggleBB()               { chartState.showBB               = !chartState.showBB;               syncShowDropdown(); drawChart(); }

window.toggleHighLow = toggleHighLow;
window.toggleBoxZone = toggleBoxZone;
window.toggleBearBull = toggleBearBull;
window.toggleExtendedForecast = toggleExtendedForecast;
window.toggleSubBox = toggleSubBox;
window.toggleBB = toggleBB;
