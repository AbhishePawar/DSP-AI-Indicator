import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { recordSearch, getTrending, getPersonalHistory } from '../utils/searchTracking'
import { useAuth } from '../contexts/AuthContext'

const FALLBACK_TRENDING = ['TCS', 'INFY', 'HDFCBANK', 'RELIANCE', 'WIPRO', 'ASIANPAINT', 'BAJFINANCE']

const FEATURES = [
  {
    icon: '◈',
    title: 'Conversational Research',
    desc: 'Ask questions in plain English. DSP answers with financial evidence, not jargon.',
    color: 'var(--c-dsp)',
    path: '/copilot',
  },
  {
    icon: '⬡',
    title: 'Visual Evidence',
    desc: 'Every answer is backed by charts, ratios, and trend data — not just text.',
    color: 'var(--c-revenue)',
    path: '/analysis',
  },
  {
    icon: '◑',
    title: 'DSP AI Indicator',
    desc: 'Proprietary quality ratings built on 40+ financial metrics across every listed company.',
    color: 'var(--c-profit)',
    path: '/analysis',
  },
  {
    icon: '⇌',
    title: 'Peer Comparison',
    desc: 'Compare any two companies side-by-side across revenue, margins, valuation, and more.',
    color: 'var(--c-valuation)',
    path: '/analysis/compare',
  },
]

const STATS = [
  { value: '5,000+', label: 'Listed securities' },
  { value: '40+', label: 'Financial metrics' },
  { value: '10yr', label: 'Historical data' },
  { value: 'Real-time', label: 'Market data' },
]

export default function LandingPage() {
  const { isLoggedIn, user } = useAuth()
  const [query, setQuery] = useState('')
  const [trending, setTrending] = useState<string[]>(() => getTrending(5, FALLBACK_TRENDING))
  const [personalHistory, setPersonalHistory] = useState<string[]>(() => getPersonalHistory(user?.email, 5))
  const navigate = useNavigate()

  // Refresh both lists when window regains focus (other tabs, login/logout)
  useEffect(() => {
    function refresh() {
      setTrending(getTrending(5, FALLBACK_TRENDING))
      setPersonalHistory(getPersonalHistory(user?.email, 5))
    }
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [user?.email])

  // Re-derive personal history whenever the logged-in user changes
  useEffect(() => {
    setPersonalHistory(getPersonalHistory(user?.email))
  }, [user?.email])

  function searchAndNavigate(symbol: string, extra = '') {
    const s = symbol.trim().toUpperCase()
    if (s) {
      recordSearch(s, user?.email)
      setTrending(getTrending(5, FALLBACK_TRENDING))
      setPersonalHistory(getPersonalHistory(user?.email, 5))
    }
    navigate(`/analysis?symbol=${encodeURIComponent(s)}${extra}`)
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (query.trim()) searchAndNavigate(query)
  }

  function goBuffett() {
    searchAndNavigate(query.trim() || 'TCS')
  }

  return (
    <div>
      {/* Hero */}
      <section style={{
        padding: '80px 48px 100px',
        textAlign: 'center',
        background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgba(124,106,247,0.08) 0%, transparent 70%)',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'var(--muted)', border: '1px solid var(--border)',
          borderRadius: 99, padding: '5px 14px', marginBottom: 32,
          fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--c-profit)', display: 'inline-block' }} />
          Live · 5,000+ securities covered
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)', fontSize: 'clamp(36px, 6vw, 68px)',
          color: 'var(--foreground)', fontWeight: 500,
          margin: '0 0 20px', lineHeight: 1.1, letterSpacing: '-0.02em',
        }}>
          Ask DSP anything<br />about any company.
        </h1>
        <p style={{
          fontSize: 18, color: 'var(--muted-foreground)', maxWidth: 520,
          margin: '0 auto 48px', lineHeight: 1.65,
        }}>
          Chat-first equity research. Financial evidence when you need it.
          No dashboards, no noise.
        </p>

        {/* Search bar */}
        <div style={{ maxWidth: 560, margin: '0 auto 24px' }}>
          <div style={{ position: 'relative', marginBottom: 12 }}>
            <form onSubmit={handleSearch}>
              <div style={{
                display: 'flex', gap: 0, background: 'var(--secondary)',
                border: '1px solid var(--border)',
                borderRadius: 14,
                overflow: 'hidden', transition: 'border-color 0.15s',
              }}
                onFocusCapture={e => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)')}
                onBlurCapture={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              >
                <input
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Enter company name or ticker — e.g. TCS, HDFC Bank"
                  style={{
                    flex: 1, background: 'none', border: 'none', outline: 'none',
                    padding: '16px 20px', fontSize: 15, color: 'var(--foreground)',
                    fontFamily: 'var(--font-body)',
                  }}
                />
                <button
                  type="submit"
                  title="Research"
                  aria-label="Research"
                  style={{
                    background: 'var(--c-dsp)', border: 'none', padding: '0 24px',
                    color: '#fff', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)',
                    fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="8.5" cy="8.5" r="5.25" />
                    <line x1="12.5" y1="12.5" x2="17" y2="17" />
                  </svg>
                </button>
              </div>
            </form>
          </div>

          {/* DSP Buffett Indicator Analysis — always visible full-width button */}
          <button
            type="button"
            onClick={goBuffett}
            style={{
              width: '100%', background: 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)',
              border: 'none', borderRadius: 14, padding: '13px 24px',
              color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
              fontFamily: 'var(--font-body)', letterSpacing: '-0.01em',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.88')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            <span style={{ fontSize: 13, opacity: 0.85, fontWeight: 400 }}>DSP</span>
            <span>Buffett Indicator Analysis</span>
          </button>

        </div>

        {/* Your Recent Searches — shown only when logged in and history exists */}
        {isLoggedIn && personalHistory.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 12, fontFamily: 'var(--font-data)', letterSpacing: '0.03em',
              display: 'flex', alignItems: 'center', gap: 5,
              color: 'var(--c-dsp)', opacity: 0.85,
            }}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>
              </svg>
              Your Recent Searches:
            </span>
            {personalHistory.map(t => (
              <button
                key={t}
                onClick={() => { setQuery(t) }}
                title={`Search ${t}`}
                style={{
                  fontSize: 12, fontFamily: 'var(--font-data)',
                  color: 'var(--c-dsp)',
                  background: 'color-mix(in srgb, var(--c-dsp) 10%, transparent)',
                  border: '1px solid color-mix(in srgb, var(--c-dsp) 30%, transparent)',
                  borderRadius: 99, padding: '4px 12px',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'color-mix(in srgb, var(--c-dsp) 18%, transparent)'
                  e.currentTarget.style.borderColor = 'var(--c-dsp)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'color-mix(in srgb, var(--c-dsp) 10%, transparent)'
                  e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--c-dsp) 30%, transparent)'
                }}
              >
                {t}
              </button>
            ))}
          </div>
        )}

        {/* Trending */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>Trending:</span>
          {trending.map(t => (
            <button
              key={t}
              onClick={() => searchAndNavigate(t)}
              style={{
                fontSize: 12, color: 'var(--muted-foreground)', background: 'var(--muted)',
                border: '1px solid var(--border)', borderRadius: 99, padding: '4px 12px',
                cursor: 'pointer', fontFamily: 'var(--font-data)',
                transition: 'color 0.15s, border-color 0.15s',
              }}
              onMouseEnter={e => { const b = e.currentTarget; b.style.color = 'var(--c-dsp)'; b.style.borderColor = 'var(--c-dsp)' }}
              onMouseLeave={e => { const b = e.currentTarget; b.style.color = 'var(--muted-foreground)'; b.style.borderColor = 'var(--border)' }}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        borderBottom: '1px solid var(--border)',
      }}>
        {STATS.map((s, i) => (
          <div key={s.label} style={{
            padding: '32px 40px', textAlign: 'center',
            borderRight: i < 3 ? '1px solid var(--border)' : 'none',
          }}>
            <div style={{ fontSize: 28, fontFamily: 'var(--font-heading)', color: 'var(--c-dsp)', fontWeight: 600, marginBottom: 6 }}>{s.value}</div>
            <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{s.label}</div>
          </div>
        ))}
      </section>

      {/* Features */}
      <section style={{ padding: '80px 48px' }}>
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 36, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 12px', letterSpacing: '-0.02em' }}>
            Research the way you think.
          </h2>
          <p style={{ fontSize: 15, color: 'var(--muted-foreground)', maxWidth: 480, margin: '0 auto' }}>
            No complex dashboards to learn. Just ask, and DSP builds the picture.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20, maxWidth: 840, margin: '0 auto' }}>
          {FEATURES.map(f => (
            <Link
              key={f.title}
              to={f.path}
              className="feature-card"
              style={{
                display: 'block', textDecoration: 'none',
                background: 'var(--card)', border: '1px solid var(--border)',
                borderRadius: 14, padding: '28px 28px',
                borderTop: `2px solid ${f.color}`,
                cursor: 'pointer',
                transition: 'border-color 0.18s, box-shadow 0.18s, background 0.18s',
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLAnchorElement
                el.style.borderColor = `color-mix(in srgb, ${f.color} 55%, var(--border))`
                el.style.borderTopColor = f.color
                el.style.boxShadow = `0 8px 24px rgba(0,0,0,0.18)`
                el.style.background = `color-mix(in srgb, ${f.color} 4%, var(--card))`
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLAnchorElement
                el.style.borderColor = 'var(--border)'
                el.style.borderTopColor = f.color
                el.style.boxShadow = 'none'
                el.style.background = 'var(--card)'
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 14, color: f.color }}>{f.icon}</div>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 18, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 8px' }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: 'var(--muted-foreground)', lineHeight: 1.65, margin: 0 }}>{f.desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{
        padding: '80px 48px', textAlign: 'center',
        borderTop: '1px solid var(--border)',
        background: 'radial-gradient(ellipse 60% 80% at 50% 100%, rgba(124,106,247,0.07) 0%, transparent 70%)',
      }}>
        <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 40, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 16px', letterSpacing: '-0.02em' }}>
          Start researching free.
        </h2>
        <p style={{ fontSize: 15, color: 'var(--muted-foreground)', margin: '0 0 32px' }}>No credit card required. 10 free research sessions per month.</p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <Link to="/signup" style={{
            padding: '13px 32px', background: 'var(--c-dsp)', color: '#fff',
            borderRadius: 10, textDecoration: 'none', fontSize: 15, fontWeight: 500,
            fontFamily: 'var(--font-body)',
          }}>
            Create free account
          </Link>
          <Link to="/about" style={{
            padding: '13px 32px', background: 'var(--muted)', color: 'var(--foreground)',
            border: '1px solid var(--border)', borderRadius: 10, textDecoration: 'none',
            fontSize: 15, fontFamily: 'var(--font-body)',
          }}>
            Learn more
          </Link>
        </div>
      </section>
    </div>
  )
}
