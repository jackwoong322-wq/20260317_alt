import { useEffect, useState } from 'react'
import { fetchCoins } from '../api/client'

interface Props {
  selected: string | null
  onChange: (coinId: string) => void
}

export function CoinSelector({ selected, onChange }: Props) {
  const [coins, setCoins] = useState<any[]>([])

  useEffect(() => {
    fetchCoins().then(setCoins).catch(console.error)
  }, [])

  return (
    <select
      value={selected ?? ''}
      onChange={e => onChange(e.target.value)}
      style={{ padding: '6px 12px', fontSize: 14 }}
    >
      <option value="" disabled>코인 선택</option>
      {coins.map(c => (
        <option key={c.id} value={c.id}>
          #{c.rank} {c.symbol}
        </option>
      ))}
    </select>
  )
}
