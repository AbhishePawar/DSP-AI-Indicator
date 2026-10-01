import { Outlet, Link } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', background: 'var(--background)',
    }}>
      {/* Left brand panel */}
      <div style={{
        width: 420, flexShrink: 0, background: 'var(--card)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', padding: '48px 40px',
      }}>
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'linear-gradient(135deg, #7c6af7, #2dd4bf)' }} />
          <span style={{ fontFamily: 'var(--font-heading)', fontSize: 20, color: 'var(--foreground)' }}>DSP</span>
        </Link>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 32 }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 32, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 16px', lineHeight: 1.2 }}>
              Research-grade<br />AI for every investor.
            </h2>
            <p style={{ fontSize: 14, color: 'var(--muted-foreground)', lineHeight: 1.7, margin: 0 }}>
              Ask DSP anything about any listed company. Get conversational answers backed by real financial evidence.
            </p>
          </div>
          {[
            'Chat-first equity research',
            'Visual financial evidence',
            'DSP AI Indicator ratings',
            'Multi-security comparison',
          ].map(f => (
            <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ color: 'var(--c-profit)', fontSize: 14 }}>✓</span>
              <span style={{ fontSize: 13, color: 'var(--muted-foreground)' }}>{f}</span>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>
          © 2026 DSP AI Indicator
        </div>
      </div>

      {/* Right form panel */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{ width: '100%', maxWidth: 400 }}>
          <Outlet />
        </div>
      </div>
    </div>
  )
}
