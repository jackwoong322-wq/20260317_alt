// Legend & stats bar rendering
import { chartState } from './chart-logic.js?v=1773826372';

export function updateLegend(items) {
  const el = document.getElementById('legend');
  if (!el) return;

  if (items.length === 0) {
    el.style.display = 'none';
    return;
  }

  el.style.display = 'block';

  const singleCoin = chartState.selectedCoins.length === 1 ? ALL_DATA[chartState.selectedCoins[0]] : null;
  const coinLabel = singleCoin ? `${singleCoin.symbol || ''}/USDT` : `${chartState.selectedCoins.length} COINS`;
  const isBtcSingle = singleCoin && (singleCoin.symbol || '').toUpperCase() === 'BTC';

  const btcNote = isBtcSingle
    ? '<div class="legend-info" style="margin-top:2px">Based on BTC historical data only</div>'
    : '';

  const cycleRows = items
    .map((i) => `
      <div class="legend-item">
        <div class="legend-dot" style="background:${i.color}"></div>
        <div>
          <div>${i.label}${i.isCurr ? ' <span class="legend-current">CURRENT</span>' : ''}</div>
          <div class="legend-info">Peak: ${i.peak}</div>
        </div>
      </div>
    `)
    .join('');

  const predictionGuide = `
    <div class="legend-item">
      <span style="color:#ffbf49">--</span>
      <div>
        <div>Bull prediction (dotted)</div>
        <div class="legend-info">yellow</div>
      </div>
    </div>
    <div class="legend-item">
      <span style="color:#ff5f86">--</span>
      <div>
        <div>Bear prediction (dotted)</div>
        <div class="legend-info">red</div>
      </div>
    </div>
  `;

  el.innerHTML = `<div class="legend-title">${coinLabel}</div>${btcNote}${cycleRows}${predictionGuide}`;
}

export function updateStats() {
  const el = document.getElementById('statsBar');
  if (!el) return;

  if (chartState.selectedCoins.length !== 1) {
    el.innerHTML = '';
    return;
  }

  const coinData = ALL_DATA[chartState.selectedCoins[0]];
  if (!coinData) return;

  let html = '';

  coinData.cycles.forEach((cycle) => {
    if (!chartState.activeCycles.has(Number(cycle.cycle_number))) return;

    if (!cycle.data || cycle.data.length === 0) {
      html += `
        <div class="stat-item">
          <div class="stat-label">${(cycle.cycle_name || '').toUpperCase()}</div>
          <div class="stat-label" style="margin-top:2px">Peak: ${cycle.peak_date || '-'}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">No cycle data</div>
        </div>
      `;
      return;
    }

    const minRate = Math.min(...cycle.data.map((d) => d.close));
    const minDay = cycle.data.find((d) => d.close === minRate)?.x ?? '-';
    const maxDays = cycle.data[cycle.data.length - 1]?.x ?? '-';
    const lastRate = cycle.data[cycle.data.length - 1]?.close ?? 0;
    const isDown = lastRate < 100;

    html += `
      <div class="stat-item">
        <div class="stat-label">${cycle.cycle_name.toUpperCase()}</div>
        <div class="stat-label" style="margin-top:2px">Peak: ${cycle.peak_date}</div>
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
        <div class="stat-value ${isDown ? 'down' : 'up'}">${lastRate.toFixed(1)}%</div>
      </div>
    `;
  });

  el.innerHTML = html;
}
