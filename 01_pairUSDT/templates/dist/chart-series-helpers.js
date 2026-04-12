/**
 * Series Helpers — 시리즈 데이터 검증·필터링 (순수 함수)
 *
 * [설계 결정]
 * - isValidPoint: null/NaN/Infinity 제거로 "Value is null" 방지 (방어적 설계)
 * - setSeriesDataSafe: try-catch로 Lightweight Charts 예외 처리
 */
export function isValidPoint(p) {
    if (p == null)
        return false;
    const t = Number(p.time);
    const v = Number(p.value);
    // null, undefined, NaN, ±Infinity 모두 제거 (t>=0: day 0 허용)
    return Number.isFinite(t) && t >= 0 && Number.isFinite(v);
}
export function filterValidPoints(pts) {
    return pts.filter(isValidPoint);
}
export function setSeriesDataSafe(series, data, meta) {
    if (!series) {
        console.warn('[SERIES_NULL] setSeriesDataSafe', meta);
        return;
    }
    const src = Array.isArray(data) ? data : [];
    const clean = [];
    const invalid = [];
    src.forEach((p) => {
        if (isValidPoint(p)) {
            clean.push(p);
        }
        else {
            invalid.push(p);
        }
    });
    if (invalid.length > 0) {
        console.warn('[SERIES_INVALID_POINT]', JSON.stringify({
            ...meta,
            invalidCount: invalid.length,
            sample: invalid.slice(0, 3),
        }));
    }
    try {
        if (clean.length > 0 && (clean[0]?.time == null || clean[0]?.value == null)) {
            console.warn('[SERIES_SETDATA_NULL_SAMPLE]', meta, 'firstPoint:', clean[0]);
        }
        series.setData(clean);
    }
    catch (e) {
        console.error('[SERIES_SETDATA_ERROR]', meta, 'cleanLen:', clean.length, 'first:', clean[0], e);
    }
}
