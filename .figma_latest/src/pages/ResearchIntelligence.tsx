import { TopBar } from '../components/Nav'
import { useNavigate } from 'react-router-dom'

const SIGNALS = [
  { type: 'upgrade', symbol: 'TITAN', text: 'DSP rating upgraded from B+ to A following 3 consecutive quarters of margin expansion and improving ROCE.', time: '1 hr ago', color: 'var(--c-profit)' },
  { type: 'risk', symbol: 'ZOMATO', text: 'Risk flag: elevated cash burn rate despite revenue growth. FCF negative for 6th consecutive quarter.', time: '3 hr ago', color: 'var(--c-risk)' },
  { type: 'insight', symbol: 'HDFC', text: 'NIM compression visible in Q1 FY27 data. Net interest income growth slower than loan growth for first time since FY21.', time: '5 hr ago', color: 'var(--c-revenue)' },
  { type: 'valuation', symbol: 'PIDILITE', text: 'Approaching historical valuation peak. P/E at 78× vs 5yr median of 64×. Margin of safety reduced.', time: '8 hr ago', color: 'var(--c-valuation)' },
  { type: 'upgrade', symbol: 'SUNPHARMA', text: 'Specialty drug approvals driving margin improvement. EBITDA margins expanded 380bps YoY.', time: '12 hr ago', color: 'var(--c-profit)' },
  { type: 'risk', symbol: 'ADANI', text: 'Leverage remains elevated. Net debt to EBITDA at 5.8× across consolidated entity. Monitor closely.', time: '1 day ago', color: 'var(--c-risk)' },
  { type: 'insight', symbol: 'DMART', text: 'Same-store sales growth rebounding. Footfalls +14% YoY. Online GMV contribution now 8% of total.', time: '1 day ago', color: 'var(--c-revenue)' },
]

const TYPE_LABELS: Record<string, string> = {
  upgrade: 'Rating Change',
  risk: 'Risk Alert',
  insight: 'Research Insight',
  valuation: 'Valuation Signal',
}

const SECTORS = ['All Sectors', 'IT', 'Banking', 'FMCG', 'Pharma', 'Energy', 'Cons. Disc.']
const SIGNAL_TYPES = ['All Types', 'Rating Change', 'Risk Alert', 'Research Insight', 'Valuation Signal']

export default function ResearchIntelligence() {
  const navigate = useNavigate()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Research Intelligence" subtitle="DSP signals · Market insights · Rating changes" />
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 240px', overflow: 'hidden' }}>
        {/* Feed */}
        <div className="scroll-container" style={{ overflow: 'auto', padding: '24px 28px' }}>
          {/* Filters */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
            {SIGNAL_TYPES.map((t, i) => (
              <button key={t} style={{ fontSize: 12, padding: '6px 12px', borderRadius: 20, border: '1px solid var(--border)', background: i === 0 ? 'var(--muted)' : 'none', color: i === 0 ? 'var(--foreground)' : 'var(--muted-foreground)', cursor: 'pointer', fontFamily: 'var(--font-data)' }}>{t}</button>
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {SIGNALS.map((s, i) => (
              <div key={i} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '18px 20px', borderLeft: `3px solid ${s.color}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div style={{ display: 'flex', align: 'center', gap: 10 } as React.CSSProperties}>
                    <span style={{ fontSize: 10, color: s.color, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em', background: `${s.color}18`, borderRadius: 6, padding: '3px 8px', marginRight: 8 }}>
                      {TYPE_LABELS[s.type]}
                    </span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{s.symbol}</span>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', flexShrink: 0, marginLeft: 16 }}>{s.time}</span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.65 }}>{s.text}</p>
                <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                  <button onClick={() => navigate(`/analysis?symbol=${s.symbol}`)}
                    style={{ fontSize: 11, color: 'var(--c-dsp)', background: 'rgba(124,106,247,0.1)', border: '1px solid rgba(124,106,247,0.2)', borderRadius: 6, padding: '5px 12px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
                    Research {s.symbol} →
                  </button>
                  <button style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 12px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
                    Save
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar filters */}
        <div style={{ background: 'var(--card)', borderLeft: '1px solid var(--border)', padding: '20px 16px', overflow: 'auto' }}>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>Filter by Sector</div>
          {SECTORS.map((s, i) => (
            <button key={s} style={{ display: 'block', width: '100%', textAlign: 'left', fontSize: 12, padding: '7px 10px', borderRadius: 8, border: 'none', background: i === 0 ? 'var(--muted)' : 'none', color: i === 0 ? 'var(--foreground)' : 'var(--muted-foreground)', cursor: 'pointer', fontFamily: 'var(--font-body)', marginBottom: 2 }}>{s}</button>
          ))}
          <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>Today's Summary</div>
            {[{ label: 'New signals', value: '24' }, { label: 'Upgrades', value: '6' }, { label: 'Downgrades', value: '3' }, { label: 'Risk flags', value: '9' }].map(s => (
              <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{s.label}</span>
                <span style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 600 }}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
