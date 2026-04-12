// Crosshair tooltip rendering (per-day series values + box info)
import { chartState } from './chart-logic.js?v=1773826372';
import { timeToDay, findBoxAtDay } from './chart-logic.js?v=1773826372';
import { CYCLE_COLORS, COIN_COLORS } from './chart-logic.js?v=1773826372';
// ── Crosshair Tooltip ─────────────────────────────────
export function setupTooltip() {
    const tooltip = document.getElementById('crosshairTooltip');
    const chartEl = document.getElementById('chart');
    if (!tooltip || !chartEl) {
        return;
    }
    chartState.chart.subscribeCrosshairMove((param) => {
        if (!param || param.time == null || param.point === undefined) {
            tooltip.style.display = 'none';
            return;
        }
        const dayX = timeToDay(param.time);
        if (dayX == null) {
            tooltip.style.display = 'none';
            return;
        }
        const rows = [];
        Object.entries(chartState.seriesMetaMap).forEach(([key, meta]) => {
            const series = chartState.seriesMap[key];
            if (!series)
                return;
            const dataPoint = param.seriesData.get(series);
            if (!dataPoint)
                return;
            const cycle = meta.cycle;
            const coinId = meta.coinId;
            const coin = ALL_DATA[coinId];
            const found = cycle.data.find((d) => d.x === dayX);
            const date = found ? found.date : '';
            const col = CYCLE_COLORS[cycle.cycle_number] || CYCLE_COLORS[1];
            const color = chartState.selectedCoins.length > 1
                ? COIN_COLORS[chartState.selectedCoins.indexOf(coinId) % COIN_COLORS.length]
                : col.main;
            const boxInfo = chartState.showBoxZone
                ? findBoxAtDay(dayX, coinId, cycle.cycle_number)
                : null;
            rows.push({ color, coin, cycle, coinId, dayX, date, val: dataPoint.value, boxInfo });
        });
        if (rows.length === 0) {
            tooltip.style.display = 'none';
            return;
        }
        let html = `<div class="tt-day">Day ${dayX}</div>`;
        rows.forEach((r) => {
            const label = chartState.selectedCoins.length > 1
                ? `${r.coin.symbol} · ${r.cycle.cycle_name}`
                : r.cycle.cycle_name;
            html += `
        <div class="tt-row">
          <div class="tt-dot" style="background:${r.color}"></div>
          <div class="tt-label">${label}</div>
          <div>
            <div class="tt-val">${r.val.toFixed(2)}%</div>
            ${r.date ? `<div class="tt-date">${r.date}</div>` : ''}
          </div>
        </div>`;
            if (r.boxInfo) {
                const z = r.boxInfo.zone;
                const zi = r.boxInfo.index;
                const prev = r.boxInfo.prev;
                const cycleLow = r.boxInfo.cycleLow ?? null;
                const firstBullZi = r.boxInfo.firstBullZi ?? -1;
                const isBear = z.phase === 'BEAR';
                const isPred = z.is_prediction === 1;
                const boxColor = isBear ? '#ff4466' : '#FFB800';
                const dayInBox = dayX - z.startX + 1;
                const hiLabel = isBear
                    ? '현재박스 저점 대비'
                    : zi === firstBullZi && cycleLow != null
                        ? '사이클저점 대비'
                        : prev
                            ? '직전박스 저점 대비'
                            : '';
                const loLabel = isBear ? '직전박스 고점 대비' : '현재박스 고점 대비';
                let hiChg = '', loChg = '';
                if (isBear) {
                    const hiVsLo = ((z.hi - z.lo) / z.lo * 100).toFixed(1);
                    const hiColor = parseFloat(hiVsLo) >= 0 ? '#00ff88' : '#ff4466';
                    const hiSign = parseFloat(hiVsLo) >= 0 ? '+' : '';
                    hiChg =
                        '<span style="color:' +
                            hiColor +
                            ';margin-left:6px">' +
                            hiSign +
                            hiVsLo +
                            '%</span>' +
                            (hiLabel
                                ? ' <span style="color:#4a6080;font-size:9px">(' +
                                    hiLabel +
                                    ')</span>'
                                : '');
                    if (prev) {
                        const loVsHi = ((z.lo - prev.hi) / prev.hi * 100).toFixed(1);
                        const loColor = parseFloat(loVsHi) >= 0 ? '#00ff88' : '#ff4466';
                        const loSign = parseFloat(loVsHi) >= 0 ? '+' : '';
                        loChg =
                            '<span style="color:' +
                                loColor +
                                ';margin-left:6px">' +
                                loSign +
                                loVsHi +
                                '%</span>' +
                                ' <span style="color:#4a6080;font-size:9px">(' +
                                loLabel +
                                ')</span>';
                    }
                }
                else {
                    const loVsHi = ((z.lo - z.hi) / z.hi * 100).toFixed(1);
                    const loColor = parseFloat(loVsHi) >= 0 ? '#00ff88' : '#ff4466';
                    const loSign = parseFloat(loVsHi) >= 0 ? '+' : '';
                    loChg =
                        '<span style="color:' +
                            loColor +
                            ';margin-left:6px">' +
                            loSign +
                            loVsHi +
                            '%</span>' +
                            ' <span style="color:#4a6080;font-size:9px">(' +
                            loLabel +
                            ')</span>';
                    const refLow = zi === firstBullZi && cycleLow != null
                        ? cycleLow
                        : prev
                            ? prev.lo
                            : null;
                    if (refLow != null) {
                        const hiVsLo = ((z.hi - refLow) / refLow * 100).toFixed(1);
                        const hiColor = parseFloat(hiVsLo) >= 0 ? '#00ff88' : '#ff4466';
                        const hiSign = parseFloat(hiVsLo) >= 0 ? '+' : '';
                        hiChg =
                            '<span style="color:' +
                                hiColor +
                                ';margin-left:6px">' +
                                hiSign +
                                hiVsLo +
                                '%</span>' +
                                (hiLabel
                                    ? ' <span style="color:#4a6080;font-size:9px">(' +
                                        hiLabel +
                                        ')</span>'
                                    : '');
                    }
                }
                const rpNum = parseFloat(z.rangePct);
                const rpStr = isNaN(rpNum) ? '0.0' : rpNum.toFixed(1);
                html += `
        <div style="margin:4px 0 2px;padding:6px 8px;background:rgba(${isBear ? '255,68,102' : '255,184,0'},${isPred ? '0.04' : '0.08'});border:1px solid rgba(${isBear ? '255,68,102' : '255,184,0'},${isPred ? '0.15' : '0.25'});border-radius:4px;${isPred ? 'border-style:dashed;' : ''}">
          <div style="font-size:10px;font-weight:700;color:${boxColor};margin-bottom:4px;letter-spacing:1px;">${z.phase} Box #${z.boxIndex != null ? z.boxIndex + 1 : zi + 1}${isPred
                    ? ' <span style="color:#00d4ff;font-size:9px">[PRED]</span>'
                    : ''}</div>
          <div style="display:flex;justify-content:space-between;font-size:10px;margin:2px 0;"><span style="color:#4a6080">고점</span><span style="color:#fff;font-weight:600">${z.hi.toFixed(2)}%</span>${hiChg}</div>
          <div style="display:flex;justify-content:space-between;font-size:10px;margin:2px 0;"><span style="color:#4a6080">저점</span><span style="color:#fff;font-weight:600">${z.lo.toFixed(2)}%</span>${loChg}</div>
          <div style="display:flex;justify-content:space-between;font-size:10px;margin:2px 0;"><span style="color:#4a6080">기간</span><span style="color:#fff;">day ${z.startX}~${z.endX} (${z.duration ?? '-'}일)</span></div>
          <div style="display:flex;justify-content:space-between;font-size:10px;margin:2px 0;"><span style="color:#4a6080">현위치</span><span style="color:#fff;">${dayInBox}/${z.duration ?? '-'}일</span></div>
          <div style="display:flex;justify-content:space-between;font-size:10px;margin:2px 0;"><span style="color:#4a6080">Range</span><span style="color:#fff;">${rpStr}%</span></div>
        </div>`;
            }
        });
        tooltip.innerHTML = html;
        tooltip.style.display = 'block';
        const rect = chartEl.getBoundingClientRect();
        let left = param.point.x + 16;
        let top = param.point.y - 20;
        if (left + 260 > rect.width)
            left = param.point.x - 280;
        if (top < 0)
            top = 4;
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    });
}
