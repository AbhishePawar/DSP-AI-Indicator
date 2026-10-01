import { TopBar } from '../components/Nav'

const CLIENTS = [
  { name: 'Ananya Sharma', portfolio: '₹42L', risk: 'Moderate', rating: 'B+', sessions: 8 },
  { name: 'Rajesh Mehta', portfolio: '₹1.2Cr', risk: 'Aggressive', rating: 'A', sessions: 15 },
  { name: 'Priya Kapoor', portfolio: '₹18L', risk: 'Conservative', rating: 'A+', sessions: 4 },
  { name: 'Vikram Nair', portfolio: '₹85L', risk: 'Moderate', rating: 'A', sessions: 11 },
]

export default function Advisor() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Advisor" subtitle="Client portfolio management · Research delegation" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[
            { label: 'Total Clients', value: '4', color: 'var(--foreground)' },
            { label: 'AUM', value: '₹2.45Cr', color: 'var(--c-profit)' },
            { label: 'Avg Rating', value: 'A', color: 'var(--c-dsp)' },
            { label: 'Sessions This Month', value: '38', color: 'var(--c-revenue)' },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px' }}>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontSize: 22, color: s.color, fontFamily: 'var(--font-data)', fontWeight: 600 }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Client table */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>Client Portfolios</span>
            <button style={{ fontSize: 12, color: '#fff', background: 'var(--c-dsp)', border: 'none', borderRadius: 8, padding: '6px 14px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>+ Add Client</button>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Client', 'Portfolio Value', 'Risk Profile', 'Portfolio Rating', 'Research Sessions', ''].map(h => (
                  <th key={h} style={{ padding: '10px 20px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textAlign: 'left', borderBottom: '1px solid var(--border)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CLIENTS.map((c, i) => (
                <tr key={c.name} style={{ borderBottom: i < CLIENTS.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  <td style={{ padding: '14px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--muted)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, color: 'var(--foreground)', fontWeight: 600 }}>{c.name[0]}</div>
                      <span style={{ fontSize: 13, color: 'var(--foreground)' }}>{c.name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{c.portfolio}</td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{ fontSize: 12, color: c.risk === 'Conservative' ? 'var(--c-profit)' : c.risk === 'Moderate' ? 'var(--c-revenue)' : 'var(--c-risk)', fontFamily: 'var(--font-data)', background: 'var(--muted)', borderRadius: 6, padding: '3px 8px' }}>{c.risk}</span>
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{ fontSize: 12, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', background: 'rgba(124,106,247,0.12)', borderRadius: 6, padding: '2px 8px' }}>{c.rating}</span>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{c.sessions}</td>
                  <td style={{ padding: '14px 20px' }}>
                    <button style={{ fontSize: 11, color: 'var(--c-dsp)', background: 'rgba(124,106,247,0.1)', border: '1px solid rgba(124,106,247,0.2)', borderRadius: 6, padding: '5px 10px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>View →</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
