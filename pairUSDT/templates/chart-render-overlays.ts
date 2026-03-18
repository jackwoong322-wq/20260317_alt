// Overlay elements: box marks, bear/bull labels, cycle low & prediction markers
import { chartState } from './chart-logic.js';
import { getBtcAnchorInfo, getPhaseBoxStatsForSymbol, dayToTime, timeToDay, getScenarioKey, SCENARIO_STYLE } from './chart-logic.js';

type TooltipSegment = {
  type: 'BEAR' | 'BULL';
  startX: number;
  endX: number;
  startVal: number;
  endVal: number;
  pct: string;
  days: number;
};

/** [Why] 확대 시 timeToCoordinate가 화면 밖 시간에 null 반환 → 가장자리로 클램프해 주석 유지 */
function clampCoordToVisible(timeScale: any, day: number, overlayWidth: number): number {
  if (overlayWidth <= 0) return 0;
  const coordToTime = timeScale.coordinateToTime;
  if (typeof coordToTime !== 'function') return 0;
  const tLeft = coordToTime(0);
  const tRight = coordToTime(overlayWidth);
  const dayLeft = timeToDay(tLeft);
  const dayRight = timeToDay(tRight);
  const result = dayLeft != null && day < dayLeft ? 0 : dayRight != null && day > dayRight ? overlayWidth : Math.floor(overlayWidth / 2);
  return result;
}

// ── Clear overlays ─────────────────────────────────────
export function clearBoxMarks() {
  const overlay = document.getElementById('boxMarksOverlay');
  if (overlay) overlay.innerHTML = '';
  chartState.boxMarkEls = [];
}

export function clearBearBullLabels() {
  const overlay = document.getElementById('bearBullOverlay');
  if (overlay) overlay.innerHTML = '';
  chartState.bearBullLabels = [];
}

// ── renderBoxMarks (overlay) ──────────────────────────
export function renderBoxMarks(
  zones: any[],
  cycleLowIdx: number,
  cycleData: any[],
  timeScale: any,
  series: any,
  coinId: string,
  coinSymbol: string,
  cycleNumber: number,
  cycleRef: any,
) {
  if (!series || !timeScale) {
    console.warn('[SERIES_NULL] renderBoxMarks', { coinId, coinSymbol, cycleNumber, hasSeries: !!series, hasTimeScale: !!timeScale });
    return;
  }
  const overlay = document.getElementById('boxMarksOverlay');
  if (!overlay) return;

  const tooltip = document.getElementById('crosshairTooltip');
  const chartEl = document.getElementById('chart');
  const chartHeight = chartEl ? chartEl.clientHeight : 0;
  const overlayWidth = chartEl ? chartEl.clientWidth : 0;

  const cycleLow = cycleData[cycleLowIdx]?.low ?? null;
  const firstBullZi = zones.findIndex((z) => z.phase === 'BULL');

  /** 이미 배치된 라벨 영역 (overlay 기준) — L3/L4 등 겹침 방지 */
  const placedLowRects: { left: number; top: number; right: number; bottom: number }[] = [];
  const placedHighRects: { left: number; top: number; right: number; bottom: number }[] = [];
  const overlayRect = overlay.getBoundingClientRect();
  const LABEL_GAP = 10;
  const NUDGE_X = 56;
  const NUDGE_Y = 24;

  function rectsOverlap(
    a: { left: number; top: number; right: number; bottom: number },
    b: { left: number; top: number; right: number; bottom: number },
    gap: number,
  ): boolean {
    return !(a.right + gap < b.left || b.right + gap < a.left || a.bottom + gap < b.top || b.bottom + gap < a.top);
  }
  function getLabelRectInOverlay(el: HTMLElement): { left: number; top: number; right: number; bottom: number } {
    const r = el.getBoundingClientRect();
    return {
      left: r.left - overlayRect.left,
      top: r.top - overlayRect.top,
      right: r.right - overlayRect.left,
      bottom: r.bottom - overlayRect.top,
    };
  }
  function nudgeUntilNoOverlap(
    el: HTMLElement,
    placed: { left: number; top: number; right: number; bottom: number }[],
    nudgeX: number,
    nudgeY: number,
  ): void {
    let left = parseFloat(el.style.left || '0');
    let top = parseFloat(el.style.top || '0');
    for (let n = 0; n < 8; n++) {
      const rect = getLabelRectInOverlay(el);
      const overlaps = placed.some((p) => rectsOverlap(rect, p, LABEL_GAP));
      if (!overlaps) break;
      left += nudgeX;
      top += nudgeY;
      el.style.left = left + 'px';
      el.style.top = top + 'px';
    }
    placed.push(getLabelRectInOverlay(el));
  }

  const btcAnchor = getBtcAnchorInfo(cycleNumber);
  const phaseBoxStats = getPhaseBoxStatsForSymbol(coinSymbol, 'BULL'); // BULL/Bear 모두 참고
  const isBtcChart = (coinSymbol || '').toUpperCase() === 'BTC';

  if (chartState.showBoxZone && zones.length > 0) {
    zones.forEach((z: any, zi: number) => {
      const isBear = z.phase === 'BEAR';
      const isPrediction = z.is_prediction === 1; // 예측 박스 플래그
      const isActive =
        !isPrediction &&
        (z.result === 'BEAR_ACTIVE' || z.result === 'BULL_ACTIVE');
      const isActiveBear = z.result === 'BEAR_ACTIVE';

      const prevBox = zones[zi - 1] || null;
      const refHighForLow = isBear ? (prevBox ? prevBox.hi : 100) : z.hi;
      const refLowForHigh = isBear
        ? z.lo
        : zi === firstBullZi && cycleLow != null
        ? cycleLow
        : prevBox
        ? prevBox.lo
        : 100;

      let hiDay, loDay;
      if (isPrediction) {
        const dur = z.endX - z.startX;
        hiDay = z.hiDay != null ? z.hiDay : z.startX + Math.floor(dur / 4);
        loDay = z.loDay != null ? z.loDay : z.startX + Math.floor((dur * 3) / 4);
      } else if (isBear && z.loDay != null) {
        loDay = z.loDay;
        let bestHi = -Infinity;
        hiDay = z.endX;
        for (const d of cycleData) {
          if (d.x > z.loDay && d.x <= z.endX) {
            if (d.high > bestHi) {
              bestHi = d.high;
              hiDay = d.x;
            }
          }
        }
      } else if (!isBear && z.hiDay != null) {
        hiDay = z.hiDay;
        let bestLo = Infinity;
        loDay = z.loDay != null ? z.loDay : z.endX;
        for (const d of cycleData) {
          if (d.x > z.hiDay && d.x <= z.endX) {
            if (d.low < bestLo) {
              bestLo = d.low;
              loDay = d.x;
            }
          }
        }
      } else {
        let bestHi = -Infinity,
          bestLo = Infinity;
        hiDay = z.startX;
        loDay = z.startX;
        for (const d of cycleData) {
          if (d.x >= z.startX && d.x <= z.endX) {
            if (d.high > bestHi) {
              bestHi = d.high;
              hiDay = d.x;
            }
            if (d.low < bestLo) {
              bestLo = d.low;
              loDay = d.x;
            }
          }
        }
      }

      const hiData = cycleData.find((d) => d.x === hiDay);
      const loData = cycleData.find((d) => d.x === loDay);
      const hiDate = hiData ? hiData.date : '';
      const loDate = loData ? loData.date : '';

      const hiDayDisp =
        z.hiDay != null && z.hiDay >= z.startX && z.hiDay <= z.endX
          ? z.hiDay
          : '-';
      const loDayDisp =
        z.loDay != null && z.loDay >= z.startX && z.loDay <= z.endX
          ? z.loDay
          : '-';
      const hiDateDisp =
        hiDayDisp !== '-'
          ? cycleData.find((d) => d.x === hiDayDisp)?.date ?? ''
          : '';
      const loDateDisp =
        loDayDisp !== '-'
          ? cycleData.find((d) => d.x === loDayDisp)?.date ?? ''
          : '';

      function estimatePixelsPerDay(ts: any, data: any[]): number {
        if (data.length < 2) return 5;
        const t1 = dayToTime(data[data.length - 2].x);
        const t2 = dayToTime(data[data.length - 1].x);
        if (t1 == null || t2 == null) return 5;
        const x1 = ts.timeToCoordinate(t1);
        const x2 = ts.timeToCoordinate(t2);
        if (x1 === null || x2 === null) return 5;
        return Math.abs(x2 - x1);
      }

      const lastReal = cycleData[cycleData.length - 1];
      const lastRealX = lastReal
        ? timeScale.timeToCoordinate(dayToTime(lastReal.x))
        : null;
      const pxPerDay = estimatePixelsPerDay(timeScale, cycleData);

      let xHi = timeScale.timeToCoordinate(dayToTime(hiDay));
      if (xHi === null && isPrediction && lastRealX !== null) {
        xHi = lastRealX + (hiDay - lastReal.x) * pxPerDay;
      }
      if (xHi === null) {
        xHi = clampCoordToVisible(timeScale, hiDay, chartEl?.clientWidth ?? 0);
      }

      let xLo = timeScale.timeToCoordinate(dayToTime(loDay));
      if (xLo === null && isPrediction && lastRealX !== null) {
        xLo = lastRealX + (loDay - lastReal.x) * pxPerDay;
      }
      if (xLo === null) {
        xLo = clampCoordToVisible(timeScale, loDay, chartEl?.clientWidth ?? 0);
      }

      const hiVal = isPrediction
        ? z.hi
        : hiData && typeof hiData.high === 'number'
        ? hiData.high
        : z.hi;
      const loVal = isPrediction
        ? z.lo
        : loData && typeof loData.low === 'number'
        ? loData.low
        : z.lo;
      if (
        hiVal == null ||
        loVal == null ||
        !Number.isFinite(hiVal) ||
        !Number.isFinite(loVal)
      ) {
        return;
      }
      let rawYHi = series.priceToCoordinate(hiVal);
      let rawYLo = series.priceToCoordinate(loVal);
      if (rawYHi === null || rawYLo === null) {
        const fallbackY = chartHeight / 2;
        if (rawYHi === null) rawYHi = rawYLo ?? fallbackY - 20;
        if (rawYLo === null) rawYLo = rawYHi ?? fallbackY + 20;
      }

      if (xHi === null || xLo === null || rawYHi === null || rawYLo === null) {
        return;
      }

      const hiVsPrevLo =
        refLowForHigh != null
          ? (((z.hi - refLowForHigh) / refLowForHigh) * 100).toFixed(1)
          : null;
      const loVsPrevHi = (
        ((z.lo - refHighForLow) / refHighForLow) *
        100
      ).toFixed(1);

      const sKey = isPrediction ? getScenarioKey(z.result) : null;
      const sStyle = sKey ? SCENARIO_STYLE[sKey] : null;

      const effectiveBear = isActive ? isActiveBear : isBear;

      const hiDotColor = isPrediction
        ? effectiveBear
          ? '#FF6B6B'
          : '#FFD966'
        : effectiveBear
        ? '#ff4466'
        : '#FFB800';
      const hiDotBg = isPrediction
        ? effectiveBear
          ? 'rgba(255,107,107,0.30)'
          : 'rgba(255,217,102,0.30)'
        : effectiveBear
        ? 'rgba(255,68,102,0.35)'
        : 'rgba(255,184,0,0.35)';
      const loDotColor = isPrediction ? '#66FFBB' : '#00ff88';
      const loDotBg = isPrediction
        ? 'rgba(102,255,187,0.25)'
        : 'rgba(0,255,136,0.25)';
      const hiLblColor = isPrediction
        ? effectiveBear
          ? '#FF6B6B'
          : '#FFD966'
        : effectiveBear
        ? '#ff6688'
        : '#FFD700';
      const loLblColor = isPrediction ? '#66FFBB' : '#00ff88';
      const scenTag = sStyle ? ' ' + sStyle.tag : '';
      const useDashed = isPrediction || isActive;

      // high dot
      const dotHi = document.createElement('div');
      dotHi.className = 'bz-mark' + (useDashed ? ' prediction' : '');
      dotHi.innerHTML = `<div class="bz-dot" style="background:${hiDotBg};border-color:${hiDotColor};width:9px;height:9px;${useDashed ? 'border-style:dashed;' : ''}"></div>`;
      dotHi.style.left = xHi + 'px';
      dotHi.style.top = (rawYHi ?? 0) + 'px';
      overlay.appendChild(dotHi);
      chartState.boxMarkEls.push(dotHi);

      const lblHi = document.createElement('div');
      lblHi.className = 'bz-label' + (isPrediction ? ' prediction' : '');
      lblHi.style.color = hiLblColor;
      let hiText;
      if (isPrediction) {
        const chg =
          hiVsPrevLo !== null
            ? ` ${parseFloat(hiVsPrevLo) >= 0 ? '+' : ''}${parseFloat(
                hiVsPrevLo,
              ).toFixed(1)}%`
            : '';
        hiText = `H${z.boxIndex != null ? z.boxIndex + 1 : zi + 1} ${z.hi.toFixed(
          1,
        )}%${chg}${scenTag}`;
      } else {
        const chg =
          hiVsPrevLo !== null
            ? ` ${parseFloat(hiVsPrevLo) >= 0 ? '+' : ''}${parseFloat(
                hiVsPrevLo,
              ).toFixed(1)}%`
            : '';
        hiText = `H${zi + 1} ${z.hi.toFixed(1)}%${chg}`;
      }
      lblHi.textContent = hiText;

      const startPxHi = timeScale.timeToCoordinate(dayToTime(z.startX));
      const endPxHi = timeScale.timeToCoordinate(dayToTime(z.endX));
      let xLabelHi: number;
      if (startPxHi != null && endPxHi != null) {
        xLabelHi = (startPxHi + endPxHi) / 2;
      } else if (startPxHi != null) {
        xLabelHi = startPxHi;
      } else if (endPxHi != null) {
        xLabelHi = endPxHi;
      } else {
        xLabelHi = xHi;
      }
      const pad = 40;
      xLabelHi = Math.max(pad, Math.min(overlayWidth - pad, xLabelHi));
      lblHi.style.left = xLabelHi + 'px';
      lblHi.style.transform = 'translateX(-50%)';
      const rawTopHi = rawYHi - 18;
      const visibleHi = rawTopHi >= 0 && rawTopHi <= chartHeight;
      lblHi.style.display = visibleHi ? 'block' : 'none';
      if (visibleHi) {
        lblHi.style.top = rawTopHi + 'px';
      }
      overlay.appendChild(lblHi);
      chartState.boxMarkEls.push(lblHi);
      if (visibleHi) {
        nudgeUntilNoOverlap(lblHi, placedHighRects, NUDGE_X, -NUDGE_Y);
      } else {
        placedHighRects.push({ left: 0, top: 0, right: 0, bottom: 0 });
      }

      // low dot
      const dotLo = document.createElement('div');
      dotLo.className = 'bz-mark' + (useDashed ? ' prediction' : '');
      dotLo.innerHTML = `<div class="bz-dot" style="background:${loDotBg};border-color:${loDotColor};width:9px;height:9px;${useDashed ? 'border-style:dashed;' : ''}"></div>`;
      dotLo.style.left = xLo + 'px';
      dotLo.style.top = (rawYLo ?? 0) + 'px';
      overlay.appendChild(dotLo);
      chartState.boxMarkEls.push(dotLo);

      // low label
      const lblLo = document.createElement('div');
      lblLo.className = 'bz-label' + (isPrediction ? ' prediction' : '');
      lblLo.style.color = loLblColor;
      let loText;
      if (isPrediction) {
        const chg =
          loVsPrevHi !== null
            ? ` ${parseFloat(loVsPrevHi) >= 0 ? '+' : ''}${parseFloat(
                loVsPrevHi,
              ).toFixed(1)}%`
            : '';
        loText = `L${z.boxIndex != null ? z.boxIndex + 1 : zi + 1} ${z.lo.toFixed(
          1,
        )}%${chg}`;
      } else {
        const chg =
          loVsPrevHi !== null
            ? ` ${parseFloat(loVsPrevHi) >= 0 ? '+' : ''}${parseFloat(
                loVsPrevHi,
              ).toFixed(1)}%`
            : '';
        loText = `L${zi + 1} ${z.lo.toFixed(1)}%${chg}`;
      }
      lblLo.textContent = loText;

      const startPxLo = timeScale.timeToCoordinate(dayToTime(z.startX));
      const endPxLo = timeScale.timeToCoordinate(dayToTime(z.endX));
      let xLabelLo: number;
      if (startPxLo != null && endPxLo != null) {
        xLabelLo = (startPxLo + endPxLo) / 2;
      } else if (startPxLo != null) {
        xLabelLo = startPxLo;
      } else if (endPxLo != null) {
        xLabelLo = endPxLo;
      } else {
        xLabelLo = xLo;
      }
      xLabelLo = Math.max(pad, Math.min(overlayWidth - pad, xLabelLo));
      lblLo.style.left = xLabelLo + 'px';
      lblLo.style.transform = 'translateX(-50%)';
      const rawTopLo = rawYLo + 6;
      const visibleLo = rawTopLo >= 0 && rawTopLo <= chartHeight;
      lblLo.style.display = visibleLo ? 'block' : 'none';
      if (visibleLo) {
        lblLo.style.top = rawTopLo + 'px';
      }

      overlay.appendChild(lblLo);
      chartState.boxMarkEls.push(lblLo);
      if (visibleLo) {
        nudgeUntilNoOverlap(lblLo, placedLowRects, NUDGE_X, NUDGE_Y);
      }

      // tooltip hitbox
      [dotHi, dotLo].forEach((dot) => {
        dot.style.pointerEvents = 'all';
        dot.addEventListener('mouseenter', (e) => {
          if (!tooltip || !chartEl) {
            return;
          }
          const hiChg =
            hiVsPrevLo !== null
              ? `<span class="${
                  parseFloat(hiVsPrevLo) >= 0 ? 'bt-up' : 'bt-down'
                }">${parseFloat(hiVsPrevLo) >= 0 ? '+' : ''}${hiVsPrevLo}%</span>`
              : '<span style="color:#666">-</span>';
          const loChg =
            loVsPrevHi !== null
              ? `<span class="${
                  parseFloat(loVsPrevHi) >= 0 ? 'bt-up' : 'bt-down'
                }">${parseFloat(loVsPrevHi) >= 0 ? '+' : ''}${loVsPrevHi}%</span>`
              : '<span style="color:#666">-</span>';

          let reasonLine = '';
          if (isPrediction) {
            let btcText = '';
            if (btcAnchor) {
              const pct = (btcAnchor.progress * 100).toFixed(0);
              const riskLabel =
                btcAnchor.level === 'HIGH'
                  ? 'High Risk'
                  : btcAnchor.level === 'MID'
                  ? 'Caution'
                  : 'Normal';
              btcText = `BTC Cycle Pos: ${pct}% (${riskLabel})`;
            }
            let boxText = '';
            if (phaseBoxStats) {
              const avgBoxes = phaseBoxStats.avg.toFixed(1);
              const curBoxNo = zi + 1;
              boxText = `Avg Box Count: ${avgBoxes} / now #${curBoxNo}`;
            }
            if (isBtcChart) {
              boxText =
                (boxText ? boxText + ' · ' : '') +
                'Based on BTC Historical Data Only';
            }
            if (btcText || boxText) {
              reasonLine = `<div class="bt-row"><span class="bt-key" style="font-size:9px;opacity:0.7">Reason</span><span class="bt-val" style="font-size:9px;text-align:right;">${btcText}${
                btcText && boxText ? ' · ' : ''
              }${boxText}</span></div>`;
            }
          }

          const highRiskCaution =
            isPrediction && btcAnchor && btcAnchor.level === 'HIGH';
          let targetLine = '';
          if (isPrediction) {
            const targetLabel = isBear
              ? 'Target: Cycle Bottom'
              : 'Target: Next Peak';
            targetLine = `<div class="bt-row"><span class="bt-key">Target</span><span class="bt-val">${targetLabel}</span></div>`;
          }
          let titleLabel = isBear ? 'BEAR Box' : 'BULL Box';
          if (isPrediction && isBear) {
            titleLabel = 'TREND CHANGING [!]';
          }
          const predBadge = isPrediction
            ? ` <span style="color:${
                highRiskCaution ? '#ff4466' : '#00d4ff'
              };font-size:9px;opacity:0.8">[PREDICTION${
                highRiskCaution ? ' · CAUTION: BEAR TRANSITION' : ''
              }]</span>`
            : '';
          const hiRefLabel = isBear
            ? '현재박스 저점대비'
            : zi === firstBullZi && cycleLow != null
            ? '최저점(CYCLE LOW)대비'
            : prevBox
            ? '직전 박스 저점대비'
            : '100%대비';
          const loRefLabel = isBear
            ? prevBox
              ? '직전 박스 고점대비'
              : '100%대비'
            : '현재 박스 고점대비';

          tooltip.innerHTML =
            '<div class="bt-title" style="color:' +
            (isBear ? '#ff4466' : '#FFB800') +
            '">' +
            titleLabel +
            ' #' +
            (z.boxIndex != null ? z.boxIndex + 1 : zi + 1) +
            predBadge +
            '</div>' +
            '<div class="bt-row"><span class="bt-key">고점</span><span class="bt-val">' +
            z.hi.toFixed(2) +
            '%</span>' +
            hiChg +
            '</div>' +
            '<div class="bt-row"><span class="bt-key" style="font-size:9px;opacity:0.6">&nbsp;' +
            hiRefLabel +
            '</span></div>' +
            '<div class="bt-row"><span class="bt-key">저점</span><span class="bt-val">' +
            z.lo.toFixed(2) +
            '%</span>' +
            loChg +
            '</div>' +
            '<div class="bt-row"><span class="bt-key" style="font-size:9px;opacity:0.6">&nbsp;' +
            loRefLabel +
            '</span></div>' +
            '<div class="bt-row"><span class="bt-key">기간</span><span class="bt-val">day ' +
            z.startX +
            '~' +
            z.endX +
            ' (' +
            (z.duration || '-') +
            '일)</span></div>' +
            '<div class="bt-row"><span class="bt-key">Range</span><span class="bt-val">' +
            (z.rangePct || '0') +
            '%</span></div>' +
            targetLine +
            reasonLine +
            '<div class="bt-row"><span class="bt-key">고점일</span><span class="bt-val">Day ' +
            hiDayDisp +
            (hiDateDisp ? ' (' + hiDateDisp + ')' : '') +
            '</span></div>' +
            '<div class="bt-row"><span class="bt-key">저점일</span><span class="bt-val">Day ' +
            loDayDisp +
            (loDateDisp ? ' (' + loDateDisp + ')' : '') +
            '</span></div>';
          const rect = chartEl.getBoundingClientRect();
          tooltip.style.display = 'block';
          let left = e.clientX - rect.left + 16;
          let top = e.clientY - rect.top - 20;
          if (left + 280 > rect.width) left = e.clientX - rect.left - 290;
          if (top < 0) top = 4;
          if (top + 400 > rect.height) top = rect.height - 410;
          tooltip.style.left = left + 'px';
          tooltip.style.top = top + 'px';
        });
        dot.addEventListener('mousemove', (e) => {
          if (!tooltip || !chartEl) {
            return;
          }
          const rect = chartEl.getBoundingClientRect();
          let left = e.clientX - rect.left + 16;
          let top = e.clientY - rect.top - 20;
          if (left + 280 > rect.width) left = e.clientX - rect.left - 290;
          if (top < 0) top = 4;
          tooltip.style.left = left + 'px';
          tooltip.style.top = top + 'px';
        });
        dot.addEventListener('mouseleave', () => {
          if (!tooltip) {
            return;
          }
          tooltip.style.display = 'none';
        });
      });
    });
  }

  // cycle low marker
  const lowD = cycleData[cycleLowIdx];
  if (!lowD || lowD.low == null) return;
  const xCL = timeScale.timeToCoordinate(dayToTime(lowD.x));
  if (lowD.low == null || !Number.isFinite(lowD.low)) return;
  const yCL = series.priceToCoordinate(lowD.low);
  if (xCL === null || yCL === null) return;

  const diamond = document.createElement('div');
  diamond.className = 'cycle-low-mark';
  diamond.style.left = xCL + 'px';
  diamond.style.top = yCL + 'px';
  overlay.appendChild(diamond);
  chartState.boxMarkEls.push(diamond);

  const clLabel = document.createElement('div');
  clLabel.className = 'cycle-low-label';
  clLabel.textContent = `▼ LOW ${lowD.low.toFixed(1)}%`;
  clLabel.style.left = xCL + 12 + 'px';
  clLabel.style.top = yCL - 8 + 'px';
  overlay.appendChild(clLabel);
  chartState.boxMarkEls.push(clLabel);

  diamond.style.pointerEvents = 'all';
  diamond.addEventListener('mouseenter', (e) => {
    if (!tooltip || !chartEl) {
      return;
    }
    tooltip.innerHTML = `
      <div class="bt-title" style="color:#00d4ff">★ CYCLE LOW</div>
      <div class="bt-row"><span class="bt-key">저점</span><span class="bt-val" style="color:#00d4ff">${lowD.low.toFixed(
        2,
      )}%</span></div>
      <div class="bt-row"><span class="bt-key">날짜</span><span class="bt-val">${
        lowD.date || ''
      }</span></div>
      <div class="bt-row"><span class="bt-key">Day</span><span class="bt-val">${
        lowD.x
      }</span></div>
    `;
    const rect = chartEl.getBoundingClientRect();
    tooltip.style.display = 'block';
    let left = e.clientX - rect.left + 16;
    let top = e.clientY - rect.top - 20;
    if (left + 280 > rect.width) left = e.clientX - rect.left - 290;
    if (top < 0) top = 4;
    if (top + 400 > rect.height) top = rect.height - 410;
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
  });
  diamond.addEventListener('mousemove', (e) => {
    if (!tooltip || !chartEl) {
      return;
    }
    const rect = chartEl.getBoundingClientRect();
    let left = e.clientX - rect.left + 16;
    let top = e.clientY - rect.top - 20;
    if (left + 280 > rect.width) left = e.clientX - rect.left - 290;
    if (top < 0) top = 4;
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
  });
  diamond.addEventListener('mouseleave', () => {
    if (!tooltip) {
      return;
    }
    tooltip.style.display = 'none';
  });

  // peak/bottom prediction markers
  if (cycleRef && cycleRef.peak_predictions && cycleRef.peak_predictions.length > 0) {
    cycleRef.peak_predictions.forEach((p: any) => {
      const dayX = p.day_x;
      if (p.value == null || !Number.isFinite(p.value)) return;
      let val = p.value;
      const maxDisp = 299.9;
      const dispVal = typeof val === 'number' ? Math.min(val, maxDisp) : val;
      const x = timeScale.timeToCoordinate(dayToTime(dayX));
      if (x == null) return;
      const y = series.priceToCoordinate(val);
      if (y == null) return;
      const isPeak = p.type === 'PEAK';
      const mk = document.createElement('div');
      mk.style.position = 'absolute';
      mk.style.left = x + 'px';
      mk.style.top = y + 'px';
      mk.style.transform = 'translate(-50%, -50%)';
      mk.style.pointerEvents = 'none';
      mk.style.zIndex = '22';
      mk.style.fontSize = '14px';
      mk.style.fontWeight = '700';
      mk.style.color = isPeak
        ? 'rgba(255,217,102,0.95)'
        : 'rgba(102,217,255,0.95)';
      mk.style.textShadow = '0 0 4px rgba(0,0,0,0.8)';
      mk.textContent = isPeak ? '▲' : '▼';
      overlay.appendChild(mk);
      chartState.boxMarkEls.push(mk);
      const lbl = document.createElement('div');
      lbl.style.position = 'absolute';
      lbl.style.left = x + 10 + 'px';
      lbl.style.top = y + 'px';
      lbl.style.transform = 'translateY(-50%)';
      lbl.style.fontSize = '10px';
      lbl.style.fontWeight = '600';
      lbl.style.color = isPeak
        ? 'rgba(255,217,102,0.95)'
        : 'rgba(102,217,255,0.95)';
      lbl.style.whiteSpace = 'nowrap';
      lbl.style.pointerEvents = 'none';
      lbl.style.zIndex = '22';
      if (typeof dispVal === 'number') {
        const txt = dispVal.toFixed(1) + '%';
        lbl.textContent = isPeak ? `Peak ${txt}` : `Bottom ${txt}`;
      } else {
        lbl.textContent = isPeak ? `Peak ${dispVal}` : `Bottom ${dispVal}`;
      }
      overlay.appendChild(lbl);
      chartState.boxMarkEls.push(lbl);
    });
  }

  // prediction path end labels
  if (cycleRef && cycleRef.prediction_paths) {
    const bullPts = cycleRef.prediction_paths.bull;
    const bearPts = cycleRef.prediction_paths.bear;
    if (bullPts && bullPts.length > 1) {
      const lastU = bullPts[bullPts.length - 1];
      if (lastU && lastU.value != null && Number.isFinite(lastU.value)) {
        const xU = timeScale.timeToCoordinate(dayToTime(lastU.x));
        if (xU == null) return;
        const yU = series.priceToCoordinate(lastU.value);
        if (yU != null) {
          const endMark = document.createElement('div');
          endMark.className = 'pred-path-end';
          endMark.textContent = 'BULL 예측';
          endMark.style.color = 'rgba(255,217,102,0.95)';
          endMark.style.left = xU + 4 + 'px';
          endMark.style.top = yU + 'px';
          overlay.appendChild(endMark);
          chartState.boxMarkEls.push(endMark);
        }
      }
    }
    if (bearPts && bearPts.length > 1) {
      const lastB = bearPts[bearPts.length - 1];
      if (lastB && lastB.value != null && Number.isFinite(lastB.value)) {
        const xEnd = timeScale.timeToCoordinate(dayToTime(lastB.x));
        if (xEnd == null) return;
        const yEnd = series.priceToCoordinate(lastB.value);
        if (yEnd != null) {
          const endMark = document.createElement('div');
          endMark.className = 'pred-path-end';
          endMark.textContent = 'BEAR 예측';
          endMark.style.color = 'rgba(255,107,107,0.95)';
          endMark.style.left = xEnd + 4 + 'px';
          endMark.style.top = yEnd + 'px';
          overlay.appendChild(endMark);
          chartState.boxMarkEls.push(endMark);
        }
      }
    }
  }
}

// ── Bear/Bull labels ──────────────────────────────────
function renderBearBullLabels(
  segments: TooltipSegment[],
  timeScale: any,
  series: any,
): void {
  clearBearBullLabels();
  if (!chartState.showBearBull || segments.length === 0) return;
  const overlay = document.getElementById('bearBullOverlay');
  if (!overlay) return;
  segments.forEach((seg) => {
    const midDay = Math.round((seg.startX + seg.endX) / 2);
    const x = timeScale.timeToCoordinate(dayToTime(midDay));
    const midPrice = (seg.startVal + seg.endVal) / 2;
    if (!Number.isFinite(midPrice)) return;
    const y = series ? series.priceToCoordinate(midPrice) : null;
    if (x === null || y === null) return;
    const lbl = document.createElement('div');
    lbl.className = `bb-label ${seg.type === 'BEAR' ? 'bb-bear' : 'bb-bull'}`;
    lbl.style.left = x - 40 + 'px';
    lbl.style.top = y - 12 + 'px';
    lbl.innerHTML = `${seg.type} <span style="font-size:9px;opacity:0.7">${seg.days}d / ${seg.pct}%</span>`;
    overlay.appendChild(lbl);
    chartState.bearBullLabels.push(lbl);
  });
}

// ── Box mark redraw scheduling (used by initChart) ───
let boxRedrawTimer: number | null = null;

export function scheduleRedrawBoxMarks(): void {
  if (chartState.boxMarksData.length === 0) return;
  if (boxRedrawTimer !== null) {
    cancelAnimationFrame(boxRedrawTimer);
  }
  boxRedrawTimer = requestAnimationFrame(() => {
    boxRedrawTimer = null;
    redrawBoxMarks();
  });
}

function redrawBoxMarks(): void {
  if (chartState.boxMarksData.length === 0 || !chartState.chart) return;
  const overlay = document.getElementById('boxMarksOverlay');
  clearBoxMarks();
  chartState.boxMarksData.forEach((d: any) => {
    const series = chartState.seriesMap[d.seriesKey];
    if (!series) return;
    const ts = chartState.chart.timeScale();
    renderBoxMarks(
      d.zones,
      d.cycleLowIdx,
      d.cycleData,
      ts,
      series,
      d.coinId,
      d.symbol,
      d.cycleNumber,
      d.cycleRef,
    );
  });
}

