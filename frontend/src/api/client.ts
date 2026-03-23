const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export async function fetchCoins() {
  const res = await fetch(`${BASE_URL}/api/coins`)
  if (!res.ok) throw new Error('Failed to fetch coins')
  return res.json()
}

export async function fetchChartData(coinId: string) {
  const res = await fetch(`${BASE_URL}/api/chart-data/${coinId}`)
  if (!res.ok) throw new Error('Failed to fetch chart data')
  return res.json()
}

export async function fetchPredictions(coinId: string) {
  const res = await fetch(`${BASE_URL}/api/predictions/${coinId}`)
  if (!res.ok) throw new Error('Failed to fetch predictions')
  return res.json()
}
