function getLoadState() {
    const win = window;
    if (!win.__DASHBOARD_LOAD_STATE__) {
        win.__DASHBOARD_LOAD_STATE__ = {
            loadedCycles: new Set(),
            loadingCycles: new Map(),
            loadError: new Map(),
        };
    }
    return win.__DASHBOARD_LOAD_STATE__;
}
export function cycleKey(coinId, cycleNumber) {
    return `${coinId}:${cycleNumber}`;
}
export function getDashboardManifest() {
    return window.__DASHBOARD_MANIFEST__ || null;
}
function getMeta() {
    return window.__DASHBOARD_META__ || null;
}
function getApiBaseUrl() {
    const value = String(window.__API_BASE_URL__ || '').replace(/\/$/, '');
    return value === '__API_BASE_URL__' ? '' : value;
}
export function findManifestCoin(coinId) {
    const manifest = getDashboardManifest();
    return (manifest?.coins?.find((coin) => coin.coin_id === coinId) || null);
}
export function getManifestCoins() {
    const manifest = getDashboardManifest();
    if (manifest?.coins?.length)
        return manifest.coins;
    return Object.entries(ALL_DATA || {}).map(([coinId, coinData]) => ({
        coin_id: coinId,
        symbol: coinData?.symbol,
        name: coinData?.name,
        rank: coinData?.rank,
        cycles: coinData?.cycles || [],
    }));
}
export function findManifestCycle(coinId, cycleNumber) {
    const coin = findManifestCoin(coinId);
    return (coin?.cycles?.find((cycle) => Number(cycle.cycle_number) === Number(cycleNumber)) || null);
}
export function getCycleDisplayName(coinId, cycleNumber) {
    const manifestCycle = findManifestCycle(coinId, cycleNumber);
    if (manifestCycle?.cycle_name)
        return String(manifestCycle.cycle_name);
    const loadedCycle = findLoadedCycle(coinId, cycleNumber);
    if (loadedCycle?.cycle_name)
        return String(loadedCycle.cycle_name);
    return `Cycle ${cycleNumber}`;
}
function findLoadedCycle(coinId, cycleNumber) {
    return (ALL_DATA?.[coinId]?.cycles?.find((cycle) => Number(cycle.cycle_number) === Number(cycleNumber)) || null);
}
function cycleHasSeries(cycle) {
    return Boolean(cycle &&
        Array.isArray(cycle.data) &&
        cycle.data.length > 0);
}
export function initLoadStateFromInitial() {
    const state = getLoadState();
    Object.entries(ALL_DATA || {}).forEach(([coinId, coinData]) => {
        (coinData?.cycles || []).forEach((cycle) => {
            const number = Number(cycle.cycle_number);
            if (Number.isFinite(number)) {
                state.loadedCycles.add(cycleKey(coinId, number));
            }
        });
    });
}
export function isCycleAvailable(coinId, cycleNumber) {
    const manifestCycle = findManifestCycle(coinId, cycleNumber);
    return Boolean(manifestCycle && manifestCycle.can_lazy_load !== false);
}
export function getCycleStatus(coinId, cycleNumber) {
    const key = cycleKey(coinId, cycleNumber);
    const state = getLoadState();
    if (state.loadingCycles.has(key))
        return 'loading';
    if (state.loadError.has(key))
        return 'error';
    if (state.loadedCycles.has(key)) {
        return cycleHasSeries(findLoadedCycle(coinId, cycleNumber))
            ? 'loaded'
            : 'empty';
    }
    return 'unloaded';
}
async function reloadInitialSnapshot() {
    const baseUrl = getApiBaseUrl();
    const [manifestRes, initialRes] = await Promise.all([
        fetch(`${baseUrl}/api/dashboard-manifest`),
        fetch(`${baseUrl}/api/dashboard-initial-data`),
    ]);
    if (!manifestRes.ok || !initialRes.ok) {
        throw new Error('Failed to reload dashboard snapshot');
    }
    const manifest = await manifestRes.json();
    const initial = await initialRes.json();
    window.__DASHBOARD_MANIFEST__ = manifest;
    window.__DASHBOARD_META__ = {
        data_version: initial.data_version,
        generated_at: initial.generated_at,
        cache_status: initial.cache_status,
    };
    window.__LEGACY_CHART_DATA__ = initial.data || {};
    Object.keys(ALL_DATA).forEach((key) => delete ALL_DATA[key]);
    Object.assign(ALL_DATA, initial.data || {});
    const state = getLoadState();
    state.loadedCycles = new Set();
    state.loadingCycles = new Map();
    state.loadError = new Map();
    initLoadStateFromInitial();
}
function mergeCycle(coinId, cycle) {
    if (!ALL_DATA[coinId]) {
        const manifestCoin = findManifestCoin(coinId);
        ALL_DATA[coinId] = {
            symbol: manifestCoin?.symbol || coinId,
            name: manifestCoin?.name || coinId,
            rank: manifestCoin?.rank,
            cycles: [],
        };
    }
    if (!Array.isArray(ALL_DATA[coinId].cycles)) {
        ALL_DATA[coinId].cycles = [];
    }
    const cycleNumber = Number(cycle.cycle_number);
    const idx = ALL_DATA[coinId].cycles.findIndex((item) => Number(item.cycle_number) === cycleNumber);
    if (idx >= 0)
        ALL_DATA[coinId].cycles[idx] = cycle;
    else
        ALL_DATA[coinId].cycles.push(cycle);
}
export async function ensureCycleLoaded(coinId, cycleNumber) {
    if (!isCycleAvailable(coinId, cycleNumber))
        return;
    const status = getCycleStatus(coinId, cycleNumber);
    if (status === 'loaded' || status === 'empty')
        return;
    const key = cycleKey(coinId, cycleNumber);
    const state = getLoadState();
    const existing = state.loadingCycles.get(key);
    if (existing)
        return existing;
    const promise = (async () => {
        try {
            const baseUrl = getApiBaseUrl();
            const params = new URLSearchParams({
                coin_id: coinId,
                cycle_number: String(cycleNumber),
            });
            const response = await fetch(`${baseUrl}/api/dashboard-cycle-data?${params}`);
            if (!response.ok) {
                throw new Error(`${response.status} ${response.statusText}`);
            }
            const payload = await response.json();
            const currentVersion = getMeta()?.data_version;
            if (currentVersion && payload.data_version !== currentVersion) {
                await reloadInitialSnapshot();
                throw new Error('Dashboard data version changed. Please try again.');
            }
            mergeCycle(coinId, payload.cycle);
            state.loadedCycles.add(key);
            state.loadError.delete(key);
        }
        catch (error) {
            state.loadError.set(key, error instanceof Error ? error.message : String(error));
            throw error;
        }
        finally {
            state.loadingCycles.delete(key);
        }
    })();
    state.loadingCycles.set(key, promise);
    return promise;
}
window.ensureCycleLoaded = ensureCycleLoaded;
window.getCycleStatus = getCycleStatus;
initLoadStateFromInitial();
