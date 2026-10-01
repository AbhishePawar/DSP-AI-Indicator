import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/Nav'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const HOLDINGS = [
  { symbol: 'TCS', name: 'Tata Consultancy Services', qty: 50, avg: 3200, cmp: 3842, sector: 'IT', rating: 'A+' },
  { symbol: 'HDFC', name: 'HDFC Bank', qty: 100, avg: 1550, cmp: 1680, sector: 'Banking', rating: 'A+' },
  { symbol: 'INFY', name: 'Infosys', qty: 80, avg: 1620, cmp: 1792, sector: 'IT', rating: 'A' },
  { symbol: 'RELIANCE', name: 'Reliance Industries', qty: 30, avg: 2700, cmp: 2945, sector: 'Energy', rating: 'B+' },
  { symbol: 'ASIANPAINT', name: 'Asian Paints', qty: 40, avg: 2900, cmp: 2760, sector: 'FMCG', rating: 'A' },
  { symbol: 'BAJFIN', name: 'Bajaj Finance', qty: 20, avg: 6800, cmp: 7340, sector: 'NBFC', rating: 'B+' },
]

const SECTOR_DATA = [
  { name: 'IT', value: 35, color: 'var(--c-revenue)' },
  { name: 'Banking', value: 25, color: 'var(--c-profit)' },
  { name: 'Energy', value: 15, color: 'var(--c-risk)' },
  { name: 'FMCG', value: 12, color: 'var(--c-valuation)' },
  { name: 'NBFC', value: 13, color: 'var(--c-cashflow)' },
]

export default function Portfolio() {
  const navigate = useNavigate()
  const [sortBy, setSortBy] = useState<'gain' | 'value' | 'symbol'>('value')

  const totalInvested = HOLDINGS.reduce((a, h) => a + h.qty * h.avg, 0)
  const totalCurrent = HOLDINGS.reduce((a, h) => a + h.qty * h.cmp, 0)
  const totalGain = totalCurrent - totalInvested
  const gainPct = ((totalGain / totalInvested) * 100).toFixed(1)

  const sorted = [...HOLDINGS].sort((a, b) => {
    if (sortBy === 'value') return b.qty * b.cmp - a.qty * a.cmp
    if (sortBy === 'gain') return (b.cmp - b.avg) / b.avg - (a.cmp - a.avg) / a.avg
    return a.symbol.localeCompare(b.symbol)
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Portfolio" subtitle="Holdings · P&L Analysis" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Summary cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[
            { label: 'Current Value', value: `₹${(totalCurrent / 100000).toFixed(1)}L`, color: 'var(--foreground)' },
            { label: 'Total Invested', value: `₹${(totalInvested / 100000).toFixed(1)}L`, color: 'var(--muted-foreground)' },
            { label: 'Total Gain', value: `+₹${(totalGain / 1000).toFixed(0)}K`, color: 'var(--c-profit)' },
            { label: 'Returns', value: `+${gainPct}%`, color: 'var(--c-profit)' },
          ].map(c => (
            <div key={c.label} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px' }}>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{c.label}</div>
              <div style={{ fontSize: 22, color: c.color, fontFamily: 'var(--font-data)', fontWeight: 600 }}>{c.value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 20 }}>
          {/* Holdings table */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>Holdings ({HOLDINGS.length})</span>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['value', 'gain', 'symbol'] as const).map(s => (
                  <button key={s} onClick={() => setSortBy(s)}
                    style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)', background: sortBy === s ? 'var(--muted)' : 'none', color: sortBy === s ? 'var(--foreground)' : 'var(--muted-foreground)', cursor: 'pointer', fontFamily: 'var(--font-data)' }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Symbol', 'Qty', 'Avg Cost', 'CMP', 'P&L', 'Return', 'DSP', ''].map(h => (
                    <th key={h} style={{ padding: '9px 16px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 500, borderBottom: '1px solid var(--border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((h, i) => {
                  const pl = (h.cmp - h.avg) * h.qty
                  const ret = ((h.cmp - h.avg) / h.avg * 100).toFixed(1)
                  const up = h.cmp >= h.avg
                  return (
                    <tr key={h.symbol} style={{ borderBottom: i < sorted.length - 1 ? '1px solid var(--border)' : 'none' }}>
                      <td style={{ padding: '11px 16px' }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{h.symbol}</div>
                        <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>{h.sector}</div>
                      </td>
                      <td style={{ padding: '11px 16px', fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{h.qty}</td>
                      <td style={{ padding: '11px 16px', fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>₹{h.avg.toLocaleString()}</td>
                      <td style={{ padding: '11px 16px', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>₹{h.cmp.toLocaleString()}</td>
                      <td style={{ padding: '11px 16px', fontSize: 12, color: up ? 'var(--c-profit)' : 'var(--c-risk)', fontFamily: 'var(--font-data)' }}>{up ? '+' : ''}₹{Math.abs(pl / 1000).toFixed(1)}K</td>
                      <td style={{ padding: '11px 16px', fontSize: 12, color: up ? 'var(--c-profit)' : 'var(--c-risk)', fontFamily: 'var(--font-data)' }}>{up ? '+' : ''}{ret}%</td>
                      <td style={{ padding: '11px 16px' }}>
                        <span style={{ fontSize: 11, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', background: 'rgba(124,106,247,0.12)', borderRadius: 6, padding: '2px 6px' }}>{h.rating}</span>
                      </td>
                      <td style={{ padding: '11px 16px' }}>
                        <button onClick={() => navigate(`/analysis?symbol=${h.symbol}`)}
                          style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '3px 8px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
                          →
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Sector allocation */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px' }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)', marginBottom: 16 }}>Sector Allocation</div>
            <div style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={SECTOR_DATA} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {SECTOR_DATA.map((entry, i) => <Cell key={i} fill={entry.color} opacity={0.85} />)}
                  </Pie>
                  <Tooltip formatter={(v) => `${v}%`} contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, fontFamily: 'var(--font-data)' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
              {SECTOR_DATA.map(s => (
                <div key={s.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: s.color }} />
                    <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{s.name}</span>
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{s.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
