import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/Nav'

const SAVED = [
  { symbol: 'TCS', title: 'TCS Full Financial Analysis', tags: ['Profitability', 'Balance Sheet', 'FCF'], date: 'Sep 18, 2026', turns: 12 },
  { symbol: 'INFY', title: 'Infosys vs TCS Peer Comparison', tags: ['Comparison', 'Margins', 'ROE'], date: 'Sep 15, 2026', turns: 8 },
  { symbol: 'HDFC', title: 'HDFC Bank Valuation Deep Dive', tags: ['Valuation', 'NIM', 'Asset Quality'], date: 'Sep 10, 2026', turns: 15 },
  { symbol: 'BAJFIN', title: 'Bajaj Finance Risk Assessment', tags: ['Risk', 'Leverage', 'AUM Growth'], date: 'Sep 5, 2026', turns: 6 },
]

const TEMPLATES = [
  { title: 'Full Financial Analysis', desc: 'Profitability → Balance Sheet → FCF → Valuation', turns: '~10 questions' },
  { title: 'Quick Quality Check', desc: 'ROE, ROCE, Margins, Debt levels', turns: '~4 questions' },
  { title: 'Valuation Assessment', desc: 'P/E, EV/EBITDA, intrinsic value, margin of safety', turns: '~6 questions' },
  { title: 'Risk Profile', desc: 'Debt, sector risks, promoter holding, litigation', turns: '~5 questions' },
  { title: 'Peer Comparison', desc: 'Revenue, margins, returns vs. top peers', turns: '~8 questions' },
]

export default function ResearchHub() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const filtered = SAVED.filter(s => s.title.toLowerCase().includes(search.toLowerCase()) || s.symbol.toLowerCase().includes(search.toLowerCase()))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Research Hub" subtitle="Saved analyses · Research templates" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* Start new */}
        <div style={{ background: 'linear-gradient(135deg, rgba(124,106,247,0.1) 0%, rgba(45,212,191,0.05) 100%)', border: '1px solid rgba(124,106,247,0.25)', borderRadius: 14, padding: '24px 28px' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, color: 'var(--foreground)', margin: '0 0 8px', fontWeight: 500 }}>Start new research</h2>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: '0 0 20px' }}>Enter any listed company to begin a fresh research conversation.</p>
          <div style={{ display: 'flex', gap: 10 }}>
            <input placeholder="Company name or ticker..." style={{ flex: 1, background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', maxWidth: 320 }} />
            <button onClick={() => navigate('/analysis?symbol=TCS')}
              title="Research"
              aria-label="Research"
              style={{ background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-body)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="8.5" cy="8.5" r="5.25" />
                <line x1="12.5" y1="12.5" x2="17" y2="17" />
              </svg>
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 24 }}>
          {/* Saved research */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 17, color: 'var(--foreground)', fontWeight: 500, margin: 0 }}>Saved Research</h3>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
                style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 12px', fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', width: 160 }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {filtered.map((r, i) => (
                <div key={i} onClick={() => navigate(`/analysis?symbol=${r.symbol}`)}
                  style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 20px', cursor: 'pointer', transition: 'border-color 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.4)')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div>
                      <span style={{ fontSize: 11, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', marginRight: 8 }}>{r.symbol}</span>
                      <span style={{ fontSize: 14, color: 'var(--foreground)' }}>{r.title}</span>
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', flexShrink: 0, marginLeft: 12 }}>{r.date}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                    {r.tags.map(tag => (
                      <span key={tag} style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 99, padding: '2px 8px', fontFamily: 'var(--font-data)' }}>{tag}</span>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{r.turns} conversation turns</div>
                </div>
              ))}
            </div>
          </div>

          {/* Templates */}
          <div>
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 17, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 14px' }}>Research Templates</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {TEMPLATES.map((t, i) => (
                <div key={i} onClick={() => navigate('/analysis?symbol=TCS')}
                  style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px', cursor: 'pointer', transition: 'border-color 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.4)')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
                  <div style={{ fontSize: 13, color: 'var(--foreground)', marginBottom: 4, fontWeight: 500 }}>{t.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6, lineHeight: 1.5 }}>{t.desc}</div>
                  <div style={{ fontSize: 10, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)' }}>{t.turns}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
