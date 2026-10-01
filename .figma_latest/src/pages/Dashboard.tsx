import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/Nav'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'

const WATCHLIST = [
  { symbol: 'TCS', name: 'Tata Consultancy', price: '₹3,842', change: '+1.2%', up: true, rating: 'A+' },
  { symbol: 'INFY', name: 'Infosys', price: '₹1,792', change: '+0.8%', up: true, rating: 'A' },
  { symbol: 'HDFC', name: 'HDFC Bank', price: '₹1,680', change: '-0.3%', up: false, rating: 'A+' },
  { symbol: 'RELIANCE', name: 'Reliance Industries', price: '₹2,945', change: '+2.1%', up: true, rating: 'B+' },
  { symbol: 'WIPRO', name: 'Wipro', price: '₹476', change: '-0.6%', up: false, rating: 'B' },
]

const RECENT_RESEARCH = [
  { symbol: 'TCS', question: 'How strong is TCS financially?', time: '2 hr ago' },
  { symbol: 'INFY', question: 'Compare Infosys vs TCS margins', time: '5 hr ago' },
  { symbol: 'HDFC', question: 'Is HDFC Bank valuation attractive?', time: 'Yesterday' },
  { symbol: 'BAJFIN', question: 'What are the biggest risks for Bajaj Finance?', time: '2 days ago' },
]

const MARKET_DATA = [
  { label: 'NIFTY 50', value: '24,831', change: '+0.4%', up: true },
  { label: 'SENSEX', value: '81,454', change: '+0.5%', up: true },
  { label: 'NIFTY IT', value: '38,290', change: '+1.1%', up: true },
  { label: 'NIFTY BANK', value: '52,140', change: '-0.2%', up: false },
]

const spark = [40, 38, 42, 41, 45, 43, 47, 46, 49, 48, 52, 51]
const sparkData = spark.map((v, i) => ({ i, v }))

const DSP_SIGNALS = [
  { symbol: 'TITAN', label: 'Quality upgrade', color: 'var(--c-profit)', from: 'B+', to: 'A' },
  { symbol: 'ZOMATO', label: 'Risk flag raised', color: 'var(--c-risk)', from: 'B', to: 'B–' },
  { symbol: 'ADANI', label: 'Watch: high leverage', color: 'var(--c-risk)', from: '–', to: '–' },
]

export default function Dashboard() {
  const navigate = useNavigate()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Dashboard" subtitle="Overview · Sep 2026" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Market bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {MARKET_DATA.map(m => (
            <div key={m.label} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{m.label}</div>
              <div style={{ fontSize: 18, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 600 }}>{m.value}</div>
              <div style={{ fontSize: 12, color: m.up ? 'var(--c-profit)' : 'var(--c-risk)', fontFamily: 'var(--font-data)', marginTop: 2 }}>{m.change}</div>
              <div style={{ height: 36, marginTop: 8 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sparkData}>
                    <Line type="monotone" dataKey="v" stroke={m.up ? 'var(--c-profit)' : 'var(--c-risk)'} strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>

        {/* Main grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }}>
          {/* Watchlist */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12 }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>Watchlist</span>
              <button onClick={() => navigate('/companies')} style={{ fontSize: 12, color: 'var(--c-dsp)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>+ Add</button>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Symbol', 'Price', 'Change', 'DSP Rating', ''].map(h => (
                    <th key={h} style={{ padding: '10px 20px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 500, borderBottom: '1px solid var(--border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {WATCHLIST.map((row, i) => (
                  <tr key={row.symbol} style={{ borderBottom: i < WATCHLIST.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <td style={{ padding: '12px 20px' }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{row.symbol}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>{row.name}</div>
                    </td>
                    <td style={{ padding: '12px 20px', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{row.price}</td>
                    <td style={{ padding: '12px 20px', fontSize: 13, color: row.up ? 'var(--c-profit)' : 'var(--c-risk)', fontFamily: 'var(--font-data)' }}>{row.change}</td>
                    <td style={{ padding: '12px 20px' }}>
                      <span style={{ fontSize: 12, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', background: 'rgba(124,106,247,0.12)', borderRadius: 6, padding: '2px 8px' }}>{row.rating}</span>
                    </td>
                    <td style={{ padding: '12px 20px' }}>
                      <button onClick={() => navigate(`/analysis?symbol=${row.symbol}`)}
                        style={{ fontSize: 11, color: 'var(--c-dsp)', background: 'none', border: '1px solid rgba(124,106,247,0.3)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
                        Research →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Recent research */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12 }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>Recent Research</span>
              </div>
              {RECENT_RESEARCH.map((r, i) => (
                <div key={i} onClick={() => navigate(`/analysis?symbol=${r.symbol}`)}
                  style={{ padding: '12px 16px', borderBottom: i < RECENT_RESEARCH.length - 1 ? '1px solid var(--border)' : 'none', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)' }}>{r.symbol}</span>
                    <span style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{r.time}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--foreground)', lineHeight: 1.4 }}>{r.question}</div>
                </div>
              ))}
            </div>

            {/* DSP Signals */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12 }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>DSP Signals</span>
              </div>
              {DSP_SIGNALS.map((s, i) => (
                <div key={i} style={{ padding: '12px 16px', borderBottom: i < DSP_SIGNALS.length - 1 ? '1px solid var(--border)' : 'none', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--foreground)', marginBottom: 2 }}>{s.symbol} — {s.label}</div>
                    {s.from !== '–' && <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{s.from} → {s.to}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
