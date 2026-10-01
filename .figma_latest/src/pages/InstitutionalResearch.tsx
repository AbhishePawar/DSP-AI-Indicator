import { TopBar } from '../components/Nav'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

const SCREENER_DATA = [
  { symbol: 'TCS', rating: 'A+', pe: 27.4, roe: 51.2, mcap: 'L', growth: 12.4, sector: 'IT' },
  { symbol: 'INFY', rating: 'A', pe: 24.1, roe: 32.8, mcap: 'L', growth: 9.1, sector: 'IT' },
  { symbol: 'HDFC', rating: 'A+', pe: 18.2, roe: 16.4, mcap: 'L', growth: 18.2, sector: 'Banking' },
  { symbol: 'ASIAN', rating: 'A', pe: 58.1, roe: 28.9, mcap: 'M', growth: 7.1, sector: 'FMCG' },
  { symbol: 'BAJFIN', rating: 'B+', pe: 35.2, roe: 22.1, mcap: 'M', growth: 24.8, sector: 'NBFC' },
  { symbol: 'TITAN', rating: 'A', pe: 66.2, roe: 31.4, mcap: 'M', growth: 21.3, sector: 'Cons.' },
]

const TREND_DATA = [
  { month: 'Apr', covered: 140, rated: 118 },
  { month: 'May', covered: 148, rated: 125 },
  { month: 'Jun', covered: 155, rated: 132 },
  { month: 'Jul', covered: 162, rated: 140 },
  { month: 'Aug', covered: 170, rated: 151 },
  { month: 'Sep', covered: 178, rated: 159 },
]

export default function InstitutionalResearch() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Institutional Research" subtitle="Screener · Coverage · Bulk analysis" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Summary stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[
            { label: 'Securities Covered', value: '5,024' },
            { label: 'DSP Rated', value: '3,841' },
            { label: 'A / A+ Rated', value: '621' },
            { label: 'Last Updated', value: 'Live' },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px' }}>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontSize: 22, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 600 }}>{s.value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>
          {/* Screener */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>Quality Screener</span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                {['All', 'A+', 'A', 'B+', 'B'].map(f => (
                  <button key={f} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)', background: f === 'All' ? 'var(--muted)' : 'none', color: f === 'All' ? 'var(--foreground)' : 'var(--muted-foreground)', cursor: 'pointer', fontFamily: 'var(--font-data)' }}>{f}</button>
                ))}
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Symbol', 'DSP Rating', 'Sector', 'P/E', 'ROE', 'Rev Growth'].map(h => (
                    <th key={h} style={{ padding: '9px 16px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textAlign: 'left', borderBottom: '1px solid var(--border)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SCREENER_DATA.map((row, i) => (
                  <tr key={row.symbol} style={{ borderBottom: i < SCREENER_DATA.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <td style={{ padding: '11px 16px', fontSize: 13, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{row.symbol}</td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{ fontSize: 11, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', background: 'rgba(124,106,247,0.12)', borderRadius: 6, padding: '2px 8px' }}>{row.rating}</span>
                    </td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: 'var(--muted-foreground)' }}>{row.sector}</td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{row.pe}×</td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: 'var(--c-profit)', fontFamily: 'var(--font-data)' }}>{row.roe}%</td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: 'var(--c-revenue)', fontFamily: 'var(--font-data)' }}>+{row.growth}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Coverage trend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px' }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)', marginBottom: 16 }}>Coverage Growth</div>
              <div style={{ height: 160 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={TREND_DATA} margin={{ left: -20, right: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, fontFamily: 'var(--font-data)' }} />
                    <Line type="monotone" dataKey="covered" name="Covered" stroke="var(--c-revenue)" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="rated" name="Rated" stroke="var(--c-dsp)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px' }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)', marginBottom: 14 }}>Rating Distribution</div>
              <div style={{ height: 130 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[{ r: 'A+', v: 180 }, { r: 'A', v: 441 }, { r: 'B+', v: 820 }, { r: 'B', v: 1240 }, { r: 'C', v: 960 }, { r: 'D', v: 200 }]} margin={{ left: -20, right: 4 }}>
                    <XAxis dataKey="r" tick={{ fontSize: 11, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, fontFamily: 'var(--font-data)' }} />
                    <Bar dataKey="v" fill="var(--c-dsp)" radius={[3, 3, 0, 0]} opacity={0.8} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
