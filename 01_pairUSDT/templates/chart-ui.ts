// UI interactions: coin list, buttons, search, toggles
import { chartState } from './chart-logic.js';
import { CYCLE_COLORS } from './chart-logic.js';
import { drawChart } from './chart-draw.js';
import {
  ensureCycleLoaded,
  findManifestCycle,
  getDashboardManifest,
  getCycleDisplayName,
  getCycleStatus,
  getManifestCoins,
  isCycleAvailable,
} from './chart-lazy-load.js';

declare const ALL_DATA: any;

/** 매니페스트 + 이미 로드된 ALL_DATA에서 사이클 번호만 모음 (가짜 1~5 폴백 없음) */
function collectCycleNumbersForCoin(coinId: string): Set<number> {
  const nums = new Set<number>();
  const manifestCoin = getManifestCoins().find((c: any) => c.coin_id === coinId);
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

// ── Coin List UI ──────────────────────────────────────
export function buildCoinList(filter: string = ''): void {
  const el = document.getElementById('coinList');
  if (!el) return;
  el.innerHTML = '';
  const coins = getManifestCoins().filter((d: any) => {
    return (
      (d.symbol || '').toLowerCase().includes(filter.toLowerCase()) ||
      (d.name || '').toLowerCase().includes(filter.toLowerCase())
    );
  });

  coins.forEach((d: any) => {
    const id = d.coin_id;
    const sel = chartState.selectedCoins.includes(id);
    const div = document.createElement('div');
    div.className = 'coin-item' + (sel ? ' checked active' : '');
    (div as any).dataset.id = id;
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

async function loadActiveCyclesForSelection(): Promise<void> {
  const tasks: Promise<void>[] = [];
  chartState.selectedCoins.forEach((coinId: string) => {
    chartState.activeCycles.forEach((cycleNumber: number) => {
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

async function toggleCoin(id: string, el: HTMLElement): Promise<void> {
  const idx = chartState.selectedCoins.indexOf(id);
  if (idx >= 0) {
    // 최소 1개 코인은 항상 선택 상태 유지 (마지막 코인은 해제 불가)
    if (chartState.selectedCoins.length === 1) {
      return;
    }
    chartState.selectedCoins.splice(idx, 1);
    el.classList.remove('checked', 'active');
  } else {
    chartState.selectedCoins.push(id);
    el.classList.add('checked', 'active');
  }
  await loadActiveCyclesForSelection();
}

function clearAll(): void {
  chartState.selectedCoins = [];
  const input = document.getElementById('searchInput') as HTMLInputElement | null;
  buildCoinList(input?.value ?? '');
  drawChart();
}

// ── Cycle Toggles UI ──────────────────────────────────
export function buildCycleToggles(): void {
  const el = document.getElementById('menuCycles');
  if (!el) return;
  el.innerHTML = '';
  const cycleNums = new Set<number>();
  chartState.selectedCoins.forEach((id: string) => {
    collectCycleNumbersForCoin(id).forEach((n) => cycleNums.add(n));
  });
  // activeCycles 에 현재 표시 가능한 사이클이 하나도 없으면
  // 가장 최신 사이클(최대 cycle 번호)을 기본 선택으로 설정
  const hasActiveInView = Array.from(cycleNums).some((n) =>
    chartState.activeCycles.has(n),
  );
  if (cycleNums.size > 0 && !hasActiveInView) {
    const maxCycle = Math.max(...Array.from(cycleNums));
    chartState.activeCycles = new Set([maxCycle]);
  }
  [...cycleNums].sort().forEach((n: number) => {
    const col = (CYCLE_COLORS as any)[n] || (CYCLE_COLORS as any)[1];
    let name = `CYCLE ${n}`;
    for (const id of chartState.selectedCoins) {
      const found = findManifestCycle(id, n);
      if (found) {
        name = getCycleDisplayName(id, n).toUpperCase();
        break;
      }
    }
    const label = document.createElement('label');
    label.className = 'dropdown-item';
    const active = chartState.activeCycles.has(n);
    const statuses = chartState.selectedCoins.map((coinId: string) => ({
      available: isCycleAvailable(coinId, n),
      status: getCycleStatus(coinId, n),
    }));
    const hasUnavailable = statuses.some((item) => !item.available);
    const hasLoading = statuses.some((item) => item.status === 'loading');
    const hasError = statuses.some((item) => item.status === 'error');
    const allEmpty =
      statuses.length > 0 &&
      statuses.every((item) => !item.available || item.status === 'empty');
      
    let textStr = name;
    if (hasLoading) textStr = `${name} LOADING`;
    else if (hasError) textStr = `${name} ERROR`;
    else if (allEmpty) textStr = `${name} EMPTY`;
    
    label.innerHTML = `<input type="checkbox" ${active ? 'checked' : ''} ${hasUnavailable ? 'disabled' : ''}> <span style="color:${col.main}">■</span> <span style="flex:1">${textStr}</span>`;
    
    label.querySelector('input')!.onchange = (e) => {
      if ((e.target as HTMLInputElement).checked) chartState.activeCycles.add(n);
      else chartState.activeCycles.delete(n);
      void loadActiveCyclesForSelection();
    };
    el.appendChild(label);
  });

  const badge = document.getElementById('badgeCycles');
  if (badge) badge.textContent = String(chartState.activeCycles.size);
}

(window as any).buildCycleToggles = buildCycleToggles;

function updateShowBadge() {
  const activeCount = [
    chartState.showHighLow,
    chartState.showBoxZone,
    chartState.showPrediction,
    chartState.showExtendedForecast,
    chartState.showSubBox,
    chartState.showBB
  ].filter(Boolean).length;
  const badge = document.getElementById('badgeShow');
  if (badge) badge.textContent = String(activeCount);
}

function syncCheckbox(id: string, checked: boolean) {
  const chk = document.getElementById(id) as HTMLInputElement | null;
  if (chk) chk.checked = checked;
}

function toggleHighLow() {
  const chk = document.getElementById('chkHighLow') as HTMLInputElement | null;
  if (chk) chartState.showHighLow = chk.checked;
  else chartState.showHighLow = !chartState.showHighLow;
  updateShowBadge();
  drawChart();
}

function toggleBoxZone() {
  const chk = document.getElementById('chkBoxZone') as HTMLInputElement | null;
  if (chk) chartState.showBoxZone = chk.checked;
  else chartState.showBoxZone = !chartState.showBoxZone;
  updateShowBadge();
  drawChart();
}

function toggleBearBull() {
  const chk = document.getElementById('chkBearBull') as HTMLInputElement | null;
  if (chk) chartState.showPrediction = chk.checked;
  else chartState.showPrediction = !chartState.showPrediction;
  if (!chartState.showPrediction) {
    chartState.showExtendedForecast = false;
    syncCheckbox('chkExtendedForecast', false);
  }
  updateExtendedForecastButton();
  updateShowBadge();
  drawChart();
}

function updateExtendedForecastButton(): void {
  const chk = document.getElementById('chkExtendedForecast') as HTMLInputElement | null;
  if (!chk) return;
  chk.disabled = !chartState.showPrediction;
}

function toggleExtendedForecast() {
  if (!chartState.showPrediction) return;
  const chk = document.getElementById('chkExtendedForecast') as HTMLInputElement | null;
  if (chk) chartState.showExtendedForecast = chk.checked;
  else chartState.showExtendedForecast = !chartState.showExtendedForecast;
  updateExtendedForecastButton();
  updateShowBadge();
  drawChart();
}

function toggleSubBox() {
  const chk = document.getElementById('chkSubBox') as HTMLInputElement | null;
  if (chk) chartState.showSubBox = chk.checked;
  else chartState.showSubBox = !chartState.showSubBox;
  updateShowBadge();
  drawChart();
}

function toggleBB() {
  const chk = document.getElementById('chkBB') as HTMLInputElement | null;
  if (chk) chartState.showBB = chk.checked;
  else chartState.showBB = !chartState.showBB;
  updateShowBadge();
  drawChart();
}

// ── Defaults & Bottom Override UI ─────────────────────
export function initDefaults() {
  const manifest = getDashboardManifest() || {};
  if (
    typeof manifest.default_coin_id === 'string' &&
    getManifestCoins().some((coin: any) => coin.coin_id === manifest.default_coin_id)
  ) {
    chartState.selectedCoins = [manifest.default_coin_id];
  }
  if (Number.isFinite(Number(manifest.default_cycle_number))) {
    chartState.activeCycles = new Set([Number(manifest.default_cycle_number)]);
  } else {
  // 기본 코인: BTC 자동 선택 (이미 selectedCoins 에 세팅되어 있음)
  // 기본 사이클: CURRENT / 최신 사이클을 포함해 존재하는 사이클 중 최대 번호를 활성화
  const allCycleNums = new Set<number>();
  getManifestCoins().forEach((coin: any) => {
    (coin.cycles || []).forEach((c: any) =>
      allCycleNums.add(Number(c.cycle_number)),
    );
  });
  if (allCycleNums.size > 0) {
    const maxCycle = Math.max(...Array.from(allCycleNums.values()));
    chartState.activeCycles = new Set([maxCycle]);
  }
  }
  // BOX ZONE 기본 활성화 버튼 스타일 동기화
  syncCheckbox('chkHighLow', chartState.showHighLow);
  syncCheckbox('chkBoxZone', chartState.showBoxZone);
  syncCheckbox('chkBearBull', chartState.showPrediction);
  syncCheckbox('chkSubBox', chartState.showSubBox);
  syncCheckbox('chkBB', chartState.showBB);
  updateExtendedForecastButton();
  syncCheckbox('chkExtendedForecast', chartState.showExtendedForecast);
  updateShowBadge();
}

// ── Wire DOM events & expose toggles for onclick ───────
const searchInput = document.getElementById('searchInput') as HTMLInputElement | null;
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    const target = e.target as HTMLInputElement | null;
    buildCoinList(target?.value ?? '');
  });
}
(window as any).toggleHighLow = toggleHighLow;
(window as any).toggleBoxZone = toggleBoxZone;
(window as any).toggleBearBull = toggleBearBull;
(window as any).toggleExtendedForecast = toggleExtendedForecast;
(window as any).toggleSubBox = toggleSubBox;
(window as any).toggleBB = toggleBB;

function toggleDropdown(id: string) {
  const menu = document.getElementById(id);
  if (!menu) return;
  const isVisible = menu.style.display !== 'none';
  document.querySelectorAll('.dropdown-menu').forEach((el: any) => el.style.display = 'none');
  if (!isVisible) {
    menu.style.display = 'flex';
  }
}
(window as any).toggleDropdown = toggleDropdown;

document.addEventListener('click', (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (!target.closest('.dropdown')) {
    document.querySelectorAll('.dropdown-menu').forEach((el: any) => el.style.display = 'none');
  }
});

