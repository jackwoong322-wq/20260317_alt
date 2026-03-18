// UI interactions: coin list, buttons, search, toggles
import { chartState } from './chart-logic.js';
import { CYCLE_COLORS } from './chart-logic.js';

declare const ALL_DATA: any;
declare function drawChart(): void;

// ── Coin List UI ──────────────────────────────────────
export function buildCoinList(filter: string = ''): void {
  const el = document.getElementById('coinList');
  if (!el) return;
  el.innerHTML = '';
  const keys = Object.keys(ALL_DATA).filter((id) => {
    const d = ALL_DATA[id];
    return (
      d.symbol.toLowerCase().includes(filter.toLowerCase()) ||
      d.name.toLowerCase().includes(filter.toLowerCase())
    );
  });

  keys.forEach((id) => {
    const d = ALL_DATA[id];
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
    div.onclick = () => toggleCoin(id, div);
    el.appendChild(div);
  });
}

function toggleCoin(id: string, el: HTMLElement): void {
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
  drawChart();
}

function clearAll(): void {
  chartState.selectedCoins = [];
  const input = document.getElementById('searchInput') as HTMLInputElement | null;
  buildCoinList(input?.value ?? '');
  drawChart();
}

// ── Cycle Toggles UI ──────────────────────────────────
export function buildCycleToggles(): void {
  const el = document.getElementById('cycleToggles');
  if (!el) return;
  el.innerHTML = '';
  const cycleNums = new Set<number>();
  chartState.selectedCoins.forEach((id: string) => {
    (ALL_DATA[id]?.cycles || []).forEach((c: any) =>
      cycleNums.add(Number(c.cycle_number) as number),
    );
  });
  if (cycleNums.size === 0) {
    [1, 2, 3, 4, 5].forEach((n) => cycleNums.add(n));
  }
  // activeCycles 에 현재 표시 가능한 사이클이 하나도 없으면
  // 가장 최신 사이클(최대 cycle 번호)을 기본 선택으로 설정
  const hasActiveInView = Array.from(cycleNums).some((n) =>
    chartState.activeCycles.has(n),
  );
  if (!hasActiveInView) {
    const maxCycle = Math.max(...Array.from(cycleNums));
    chartState.activeCycles = new Set([maxCycle]);
  }
  [...cycleNums].sort().forEach((n: number) => {
    const col = (CYCLE_COLORS as any)[n] || (CYCLE_COLORS as any)[1];
    let name = `CYCLE ${n}`;
    for (const id of chartState.selectedCoins) {
      const found = (ALL_DATA[id]?.cycles || []).find(
        (c: any) => c.cycle_number === n,
      );
      if (found) {
        name = found.cycle_name.toUpperCase();
        break;
      }
    }
    if (cycleNums.size === 0 || chartState.selectedCoins.length === 0) {
      name = n === 5 ? 'CURRENT' : `CYCLE ${n}`;
    }
    const btn = document.createElement('button');
    btn.className = 'cycle-btn';
    const active = chartState.activeCycles.has(n);
    (btn as HTMLButtonElement).style.cssText = active
      ? `border-color:${col.main};color:${col.main};background:${col.band}`
      : 'border-color:#1e2d45;color:#4a6080;background:transparent';
    btn.textContent = name;
    btn.onclick = () => {
      if (chartState.activeCycles.has(n)) chartState.activeCycles.delete(n);
      else chartState.activeCycles.add(n);
      buildCycleToggles();
      drawChart();
    };
    el.appendChild(btn);
  });
}

function toggleHighLow() {
  chartState.showHighLow = !chartState.showHighLow;
  const btn = document.getElementById('toggleRange') as HTMLButtonElement | null;
  if (btn) {
    btn.style.cssText = chartState.showHighLow
      ? 'border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,0.1)'
      : 'border-color:#4a6080;color:#4a6080;';
  }
  drawChart();
}

function toggleBoxZone() {
  chartState.showBoxZone = !chartState.showBoxZone;
  const btn = document.getElementById('toggleBox') as HTMLButtonElement | null;
  if (btn) {
    btn.style.cssText = chartState.showBoxZone
      ? 'border-color:#FFB800;color:#FFB800;background:rgba(255,184,0,0.1)'
      : 'border-color:#4a6080;color:#4a6080;';
  }
  drawChart();
}

function toggleBearBull() {
  chartState.showBearBull = !chartState.showBearBull;
  const btn = document.getElementById('toggleBearBull') as HTMLButtonElement | null;
  if (btn) {
    btn.style.cssText = chartState.showBearBull
      ? 'border-color:#a0f0c0;color:#a0f0c0;background:rgba(0,255,136,0.08)'
      : 'border-color:#4a6080;color:#4a6080;';
  }
  drawChart();
}

// ── Defaults & Bottom Override UI ─────────────────────
export function initDefaults() {
  // 기본 코인: BTC 자동 선택 (이미 selectedCoins 에 세팅되어 있음)
  // 기본 사이클: CURRENT / 최신 사이클을 포함해 존재하는 사이클 중 최대 번호를 활성화
  const allCycleNums = new Set<number>();
  Object.values(ALL_DATA).forEach((coin: any) => {
    (coin.cycles || []).forEach((c: any) =>
      allCycleNums.add(Number(c.cycle_number)),
    );
  });
  if (allCycleNums.size > 0) {
    const maxCycle = Math.max(...Array.from(allCycleNums.values()));
    chartState.activeCycles = new Set([maxCycle]);
  }
  // BOX ZONE 기본 활성화 버튼 스타일 동기화
  const boxBtn = document.getElementById('toggleBox') as HTMLButtonElement | null;
  if (boxBtn) {
    boxBtn.style.cssText = chartState.showBoxZone
      ? 'border-color:#FFB800;color:#FFB800;background:rgba(255,184,0,0.1)'
      : 'border-color:#4a6080;color:#4a6080;';
  }
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

