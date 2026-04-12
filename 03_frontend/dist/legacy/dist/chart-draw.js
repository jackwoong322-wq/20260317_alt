/**
 * Chart Draw — 메인 차트 렌더링 오케스트레이션
 *
 * [설계 결정]
 * - DI: drawChart(state)는 state를 인자로 받음. chartState 기본값은 마이그레이션용
 * - SRP: clearAllSeries, drawCycleForCoin 등은 각각 한 가지 책임만 수행
 * - Early Return: selectedCoins.length === 0 등 예외를 먼저 처리
 */
import { chartState, COIN_COLORS, CYCLE_COLORS } from './chart-logic.js?v=1773826372';
import { addMainLineSeries } from './chart-series-main.js?v=1773826372';
import { addHighLowSeries } from './chart-series-highlow.js?v=1773826372';
import { addBoxZoneSeries, addBoxZoneFallback, addActiveBoxExtensions } from './chart-series-boxzone.js?v=1773826372';
import { addPredictionPaths } from './chart-series-prediction.js?v=1773826372';
import { addBearBullSeries } from './chart-series-bearbull.js?v=1773826372';
import { buildCycleToggles } from './chart-ui.js?v=1773826372';
import { updateLegend, updateStats } from './chart-render-legend-stats.js?v=1773826372';
import { clearBearBullLabels, clearBoxMarks } from './chart-render-overlays.js?v=1773826372';
/** 시리즈 키 포맷: {coinId}_{cycleNum}_close */
function buildCloseKey(coinId, cycleNumber) {
    return `${coinId}_${cycleNumber}_close`;
}
/** 단일 시리즈 제거 시도, 실패 시 로그만 남김 (방어적 설계) */
function removeSeriesSafe(chart, key, series) {
    try {
        chart.removeSeries(series);
    }
    catch {
        /* ignore */
    }
}
/** 모든 시리즈·오버레이 초기화 (SRP: clear만 담당) */
function clearAllSeries(state) {
    Object.entries(state.seriesMap).forEach(([key, s]) => {
        removeSeriesSafe(state.chart, key, s);
    });
    state.seriesMap = {};
    state.seriesMetaMap = {};
    clearBearBullLabels();
    clearBoxMarks();
    state.boxMarksData = [];
}
/** 순수 함수: 사이클 최저점 인덱스 반환 */
function findCycleMinLowIdx(cycleData) {
    let minVal = Infinity;
    let minIdx = 0;
    cycleData.forEach((d, idx) => {
        if (d.low < minVal) {
            minVal = d.low;
            minIdx = idx;
        }
    });
    return minIdx;
}
/** Bear 예측 시 저점일(startX)을 LOW로 사용. 첫 BEAR 예측 박스의 startX에 해당하는 인덱스 반환 */
function findBearStartLowIdx(cycleData, zones) {
    const firstBear = zones?.find((z) => z.is_prediction === 1 && z.phase === 'BEAR');
    if (!firstBear || !cycleData?.length)
        return null;
    const startX = Number(firstBear.startX ?? firstBear.start_x);
    if (!Number.isFinite(startX))
        return null;
    let bestIdx = -1;
    let bestDiff = Infinity;
    cycleData.forEach((d, idx) => {
        const diff = Math.abs(Number(d.x) - startX);
        if (diff < bestDiff) {
            bestDiff = diff;
            bestIdx = idx;
        }
    });
    return bestIdx >= 0 ? bestIdx : null;
}
/** 순수 함수: 코인/사이클별 색상 결정 (다중 코인 vs 단일) */
function resolveCycleColor(state, coinIdx, cycleNum) {
    const baseColor = COIN_COLORS[coinIdx % COIN_COLORS.length];
    const col = CYCLE_COLORS[cycleNum] || CYCLE_COLORS[1];
    return state.selectedCoins.length > 1 ? baseColor : col.main;
}
/** 순수 함수: 범례 아이템 문자열 (파생 데이터) */
function buildLegendLabel(state, coinData, cycle) {
    return state.selectedCoins.length > 1
        ? `${coinData.symbol} · ${cycle.cycle_name}`
        : cycle.cycle_name;
}
/** 코인·사이클 단위 렌더링 (SRP: 한 사이클만 그리기) */
function drawCycleForCoin(state, coinId, coinData, coinIdx, cycle, legendItems) {
    const cycleNum = Number(cycle.cycle_number);
    if (!state.activeCycles.has(cycleNum))
        return;
    const color = resolveCycleColor(state, coinIdx, cycleNum);
    const isCurr = cycle.cycle_name.toLowerCase().includes('current');
    // Bear 예측 시 저점일(startX)을 LOW로 표시. 없으면 기존 cycle 최저점 사용
    const bearStartIdx = findBearStartLowIdx(cycle.data, cycle.box_zones);
    const cycleMinLowIdx = bearStartIdx ?? findCycleMinLowIdx(cycle.data);
    const closeKey = buildCloseKey(coinId, cycle.cycle_number);
    const lineSeries = addMainLineSeries(state, coinId, coinData, cycle, color, isCurr, cycleNum, cycleMinLowIdx, closeKey);
    if (state.showHighLow) {
        addHighLowSeries(coinId, coinData, cycle, color, cycleNum);
    }
    if (state.showBoxZone) {
        addBoxZoneSeries(coinId, coinData, cycle, cycleNum, cycleMinLowIdx, closeKey, lineSeries);
    }
    else {
        addBoxZoneFallback(coinId, coinData, cycle, cycleMinLowIdx, closeKey, lineSeries);
    }
    addActiveBoxExtensions(coinId, coinData, cycle, cycleNum);
    addPredictionPaths(coinId, coinData, cycle, cycleNum);
    addBearBullSeries(coinId, coinData, cycle, cycleNum, lineSeries);
    legendItems.push({
        color,
        label: buildLegendLabel(state, coinData, cycle),
        peak: cycle.peak_date,
        isCurr,
    });
}
/**
 * 메인 차트 그리기 진입점
 * [DI] state 기본값은 chartState — 마이그레이션용, 이후 호출부에서 명시적 전달 권장
 */
export function drawChart(state = chartState) {
    clearAllSeries(state);
    buildCycleToggles();
    // F12 콘솔: 차트 그릴 때마다 항상 출력 (선택 코인 수 / 예측 데이터)
    console.log('[차트] drawChart 호출, 선택 코인 수:', state.selectedCoins.length, state.selectedCoins);
    if (state.selectedCoins.length === 0) {
        updateLegend([]);
        updateStats();
        return;
    }
    const legendItems = [];
    state.selectedCoins.forEach((coinId, coinIdx) => {
        const coinData = ALL_DATA[coinId];
        if (!coinData)
            return;
        coinData.cycles.forEach((cycle) => {
            drawCycleForCoin(state, coinId, coinData, coinIdx, cycle, legendItems);
        });
    });
    // F12 콘솔에 예측 데이터 전부 출력 (차트 그릴 때마다)
    const predictionDump = {};
    state.selectedCoins.forEach((coinId) => {
        const coinData = ALL_DATA[coinId];
        if (!coinData)
            return;
        coinData.cycles.forEach((c) => {
            const paths = c.prediction_paths;
            if (paths && (paths.bull?.length || paths.bear?.length)) {
                const key = `${coinData.symbol}_cycle${c.cycle_number}`;
                predictionDump[key] = paths;
            }
        });
    });
    if (Object.keys(predictionDump).length > 0) {
        console.log('[예측 데이터] prediction_paths 전부:', predictionDump);
    }
    else {
        console.log('[예측 데이터] 표시 중인 코인/사이클에 prediction_paths 없음 (DB coin_prediction_paths 확인)');
    }
    updateLegend(legendItems);
    updateStats();
    state.chart.timeScale().fitContent();
}
// 전역 노출: HTML onclick 등 DOM 이벤트에서 호출 (Vanilla 구조)
window.drawChart = drawChart;
