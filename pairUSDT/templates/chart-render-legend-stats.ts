// Legend & stats bar rendering
import { chartState } from './chart-logic.js';

declare const ALL_DATA: any;

// ── Legend ────────────────────────────────────────────
export function updateLegend(items: any[]): void {
  const el = document.getElementById('legend');
  if (!el) return;
  if (items.length === 0) {
    el.style.display = 'none';
    return;
  }
  el.style.display = 'block';
  const singleCoin =
    chartState.selectedCoins.length === 1 ? ALL_DATA[chartState.selectedCoins[0]] : null;
  const coinLabel = singleCoin
    ? (singleCoin.symbol || '') + '/USDT'
    : `${chartState.selectedCoins.length} COINS`;
  const isBtcSingle =
    singleCoin && (singleCoin.symbol || '').toUpperCase() === 'BTC';
  const btcNote = isBtcSingle
    ? '<div style="font-size:9px;color:#4a6080;letter-spacing:0.5px;margin-top:2px;">Based on BTC Historical Data Only</div>'
    : '';
  el.innerHTML =
    `<div class="legend-title">${coinLabel}</div>${btcNote}` +
    items
      .map(
        (i) => `
      <div class="legend-item">
        <div class="legend-dot" style="background:${i.color}"></div>
        <div>
          <div>${i.label}${
          i.isCurr
            ? ' <span style="color:#FFB800;font-size:9px">●LIVE</span>'
            : ''
        }</div>
          <div class="legend-info">Peak: ${i.peak}</div>
        </div>
      </div>
    `,
      )
      .join('') +
    `<div class="legend-item"><span style="font-size:12px">🟡</span><div><div>Bull 예측 (점선)</div><div class="legend-info">노란색</div></div></div>` +
    `<div class="legend-item"><span style="font-size:12px">🔴</span><div><div>Bear 예측 (점선)</div><div class="legend-info">빨간색</div></div></div>`;
}

// ── Stats Bar ─────────────────────────────────────────
export function updateStats(): void {
  const el = document.getElementById('statsBar');
  if (!el) return;
  if (chartState.selectedCoins.length !== 1) {
    el.innerHTML = '';
    return;
  }
  const coinData = ALL_DATA[chartState.selectedCoins[0]];
  if (!coinData) return;
  let html = '';
  coinData.cycles.forEach((cycle: any) => {
    if (!chartState.activeCycles.has(Number(cycle.cycle_number))) return;
    if (!cycle.data || cycle.data.length === 0) {
      html += `
      <div class="stat-item">
        <div class="stat-label">${(cycle.cycle_name || '').toUpperCase()}</div>
        <div class="stat-label" style="margin-top:2px">Peak: ${
          cycle.peak_date || '-'
        }</div>
      </div>
      <div class="stat-item"><div class="stat-label">실측 가격 데이터 없음</div></div>
      `;
      return;
    }
    const minRate = Math.min(...cycle.data.map((d: any) => d.close));
    const minDay = cycle.data.find((d: any) => d.close === minRate)?.x ?? '-';
    const maxDays = cycle.data[cycle.data.length - 1]?.x ?? '-';
    const lastRate = cycle.data[cycle.data.length - 1]?.close ?? 0;
    const isDown = lastRate < 100;
    html += `
      <div class="stat-item">
        <div class="stat-label">${cycle.cycle_name.toUpperCase()}</div>
        <div class="stat-label" style="margin-top:2px">Peak: ${
          cycle.peak_date
        }</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">BOTTOM</div>
        <div class="stat-value down">${minRate.toFixed(1)}%</div>
        <div class="stat-label">day ${minDay}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">DURATION</div>
        <div class="stat-value">${maxDays}d</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">CURRENT</div>
        <div class="stat-value ${
          isDown ? 'down' : 'up'
        }">${lastRate.toFixed(1)}%</div>
      </div>
    `;
  });
  el.innerHTML = html;
}

