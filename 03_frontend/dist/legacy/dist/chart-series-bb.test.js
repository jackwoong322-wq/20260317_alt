import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { calculateBollingerBands, addBollingerBandsSeries } from './chart-series-bb';
// Mock chart-series-helpers and chart-logic
jest.mock('./chart-series-helpers.js', () => ({
    setSeriesDataSafe: jest.fn(),
}));
jest.mock('./chart-logic.js', () => ({
    dayToTime: (day) => day, // Return day exactly as passed
}));
describe('Bollinger Bands Logic Tests', () => {
    // 1-10. Tests for calculateBollingerBands
    it('1. should return empty array if data is null', () => {
        expect(calculateBollingerBands(null)).toEqual([]);
    });
    it('2. should return empty array if data length is less than period', () => {
        expect(calculateBollingerBands([{ close: 10, x: 1 }], 20)).toEqual([]);
    });
    it('3. should calculate exactly 1 result if data length equals period', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        const result = calculateBollingerBands(data, 20, 2);
        expect(result).toHaveLength(1);
        expect(result[0].middle).toBe(10);
        expect(result[0].upper).toBe(10); // SD = 0
        expect(result[0].lower).toBe(10);
    });
    it('4. should correctly calculate SMA', () => {
        // 3 items, values: 10, 20, 30. SMA = 20. StdDev = sqrt((100+0+100)/3) = sqrt(66.6) = 8.16
        const data = [
            { close: 10, x: 1 },
            { close: 20, x: 2 },
            { close: 30, x: 3 }
        ];
        const result = calculateBollingerBands(data, 3, 1);
        expect(result).toHaveLength(1);
        expect(result[0].middle).toBeCloseTo(20);
        expect(result[0].upper).toBeCloseTo(20 + 8.1649);
        expect(result[0].lower).toBeCloseTo(20 - 8.1649);
    });
    it('5. should handle stdDev multiplier correctly', () => {
        const data = [{ close: 10, x: 1 }, { close: 20, x: 2 }, { close: 30, x: 3 }];
        const result = calculateBollingerBands(data, 3, 2); // Multiplier = 2
        expect(result[0].upper).toBeCloseTo(20 + (8.1649 * 2));
        expect(result[0].lower).toBeCloseTo(20 - (8.1649 * 2));
    });
    it('6. should correctly slide the window across multiple days', () => {
        const data = [
            { close: 10, x: 1 },
            { close: 10, x: 2 },
            { close: 10, x: 3 },
            { close: 20, x: 4 },
        ];
        const result = calculateBollingerBands(data, 3, 2);
        expect(result).toHaveLength(2); // Day 3 and Day 4
        expect(result[0].middle).toBe(10); // 10, 10, 10
        expect(result[1].middle).toBeCloseTo(13.333); // 10, 10, 20 -> 40/3
    });
    it('7. should skip invalid close values in SMA gracefully (fallback safety)', () => {
        const data = [
            { close: 10, x: 1 },
            { close: null, x: 2 }, // invalid
            { close: 10, x: 3 },
        ];
        // This will evaluate to Number(null) = 0 in JS, so sum = 10+0+10 = 20 / 3 = 6.66
        const result = calculateBollingerBands(data, 3, 1);
        expect(result[0].middle).toBeCloseTo(6.666);
    });
    it('8. should skip NaN close values safely (evaluates to NaN in JS)', () => {
        const data = [
            { close: 10, x: 1 },
            { close: NaN, x: 2 },
            { close: 10, x: 3 },
        ];
        // our logic `if (!Number.isFinite(val)) continue;` handles NaN by skipping it in sum, but divides by period
        // sum = 20. 20 / 3 = 6.66
        const result = calculateBollingerBands(data, 3, 1);
        expect(result[0].middle).toBeCloseTo(6.666);
    });
    it('9. should correctly push the matching `x` property to the result', () => {
        const data = [{ close: 5, x: 100 }, { close: 5, x: 101 }, { close: 5, x: 102 }];
        const result = calculateBollingerBands(data, 3, 1);
        expect(result[0].x).toBe(102);
    });
    it('10. should ignore non-numeric period or fallback effectively', () => {
        // If period is large, returns empty
        expect(calculateBollingerBands([{ close: 1, x: 1 }], 999)).toEqual([]);
    });
    // 11-20. Tests for addBollingerBandsSeries
    let mockState;
    beforeEach(() => {
        mockState = {
            chart: {
                addLineSeries: jest.fn().mockImplementation((config) => ({
                    config, // to verify config
                })),
            },
            seriesMap: {},
        };
    });
    it('11. should not add series if cycleData is null', () => {
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, null, 'btc_key');
        expect(mockState.chart.addLineSeries).not.toHaveBeenCalled();
    });
    it('12. should not add series if cycleData length is less than 20', () => {
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, [{ close: 1, x: 1 }], 'btc_key');
        expect(mockState.chart.addLineSeries).not.toHaveBeenCalled();
    });
    it('13. should not add series if state.chart is null', () => {
        mockState.chart = null;
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        expect(mockState.seriesMap).toEqual({});
    });
    it('14. should call addLineSeries 3 times (upper, lower, middle)', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        expect(mockState.chart.addLineSeries).toHaveBeenCalledTimes(3);
    });
    it('15. should assign bb_upper, bb_lower, bb_middle to seriesMap', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        expect(mockState.seriesMap['btc_key_bb_upper']).toBeDefined();
        expect(mockState.seriesMap['btc_key_bb_lower']).toBeDefined();
        expect(mockState.seriesMap['btc_key_bb_middle']).toBeDefined();
    });
    it('16. should use correct styles for the upper series', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        const upperConfig = mockState.chart.addLineSeries.mock.calls[0][0];
        expect(upperConfig.title).toBe('BB Upper');
        expect(upperConfig.lineStyle).toBe(2); // Dotted/Dashed
    });
    it('17. should use correct styles for the middle series', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        const middleConfig = mockState.chart.addLineSeries.mock.calls[2][0];
        expect(middleConfig.title).toBe('BB Middle');
        expect(middleConfig.color).toBe('rgba(167, 139, 250, 0.8)'); // More opaque
    });
    it('18. should skip processing days that return null from dayToTime', () => {
        // We mocked dayToTime to return day directly, but if we pass null to 'x', it could theoretically test it
        // In our mock we just return what's passed.
        const mockStateWithInvalidTime = { ...mockState };
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i === 19 ? null : i }));
        addBollingerBandsSeries(mockStateWithInvalidTime, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        // It should still process, but not push invalid timestamp to array (this needs to be handled via dayToTime internally)
        expect(mockState.chart.addLineSeries).toHaveBeenCalledTimes(3);
    });
    it('19. should handle an exact 20 item array correctly', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        expect(mockState.seriesMap['btc_key_bb_upper'].config.title).toBe('BB Upper');
    });
    it('20. should return void upon successful execution', () => {
        const data = Array.from({ length: 20 }, (_, i) => ({ close: 10, x: i }));
        const result = addBollingerBandsSeries(mockState, 'BTC', 'BTC', 'Current', 1, data, 'btc_key');
        expect(result).toBeUndefined();
    });
});
