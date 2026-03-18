declare const LightweightCharts: any;
declare const ALL_DATA: any;

// 전역에서 사용되는 차트/오버레이 함수 및 상태 최소 선언
declare function drawChart(): void;
declare function clearBoxMarks(): void;
declare function renderBoxMarks(
  zones: any[],
  cycleLowIdx: number,
  cycleData: any[],
  timeScale: any,
  series: any,
  coinId: string,
  coinSymbol: string,
  cycleNumber: number,
  cycleRef: any,
): void;

declare let chart: any;
declare let selectedCoins: string[];
declare let activeCycles: Set<number>;
declare let showHighLow: boolean;
declare let showBoxZone: boolean;
declare let showBearBull: boolean;
declare let seriesMap: Record<string, any>;
declare let seriesMetaMap: Record<string, any>;

declare function scheduleRedrawBoxMarks(): void;
declare function timeToDay(
  time: number | { day: number } | null | undefined,
): number | null;
declare function findBoxAtDay(
  dayX: number,
  coinId: string,
  cycleNum: number,
): any;

declare const COIN_COLORS: any[];
declare const CYCLE_COLORS: any;
