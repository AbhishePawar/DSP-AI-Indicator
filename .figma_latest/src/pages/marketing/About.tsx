const TEAM = [
  { name: 'Arjun Mehta', role: 'CEO & Co-founder', bg: '#7c6af7' },
  { name: 'Priya Sharma', role: 'CTO & Co-founder', bg: '#2dd4bf' },
  { name: 'Vikram Iyer', role: 'Head of Research', bg: '#38bdf8' },
  { name: 'Sneha Kapoor', role: 'Head of Product', bg: '#34d399' },
]

export default function About() {
  return (
    <div>
      {/* Hero */}
      <section style={{ padding: '80px 48px', maxWidth: 760, margin: '0 auto', textAlign: 'center' }}>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(32px, 5vw, 52px)', color: 'var(--foreground)', fontWeight: 500, margin: '0 0 20px', lineHeight: 1.15, letterSpacing: '-0.02em' }}>
          Making serious equity research<br />accessible to everyone.
        </h1>
        <p style={{ fontSize: 16, color: 'var(--muted-foreground)', lineHeight: 1.7, maxWidth: 520, margin: '0 auto' }}>
          DSP AI Indicator was built on a simple belief: retail investors deserve the same quality of financial analysis that institutional investors take for granted.
        </p>
      </section>

      {/* Mission */}
      <section style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: '64px 48px', background: 'var(--card)' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48 }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 26, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 16px' }}>Our mission</h2>
            <p style={{ fontSize: 14, color: 'var(--muted-foreground)', lineHeight: 1.75 }}>
              We want every investor — from first-time buyers to seasoned professionals — to be able to have a real conversation about any listed company and get answers grounded in actual financial data.
            </p>
          </div>
          <div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 26, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 16px' }}>The DSP Indicator</h2>
            <p style={{ fontSize: 14, color: 'var(--muted-foreground)', lineHeight: 1.75 }}>
              Our proprietary quality rating system analyses 40+ financial metrics across every listed security — profitability, balance sheet strength, cash generation, and valuation — to produce a single, trustworthy score.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section style={{ padding: '60px 48px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', maxWidth: 800, margin: '0 auto', gap: 32, textAlign: 'center' }}>
        {[
          { v: '2022', l: 'Founded' },
          { v: '5,000+', l: 'Securities covered' },
          { v: '40+', l: 'Financial metrics' },
        ].map(s => (
          <div key={s.l}>
            <div style={{ fontSize: 36, fontFamily: 'var(--font-heading)', color: 'var(--c-dsp)', fontWeight: 600, marginBottom: 8 }}>{s.v}</div>
            <div style={{ fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{s.l}</div>
          </div>
        ))}
      </section>

      {/* Team */}
      <section style={{ padding: '60px 48px', borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 760, margin: '0 auto' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 32px', textAlign: 'center' }}>Team</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
            {TEAM.map(t => (
              <div key={t.name} style={{ textAlign: 'center' }}>
                <div style={{ width: 64, height: 64, borderRadius: '50%', background: t.bg, margin: '0 auto 12px', opacity: 0.85 }} />
                <div style={{ fontSize: 14, color: 'var(--foreground)', fontWeight: 500, marginBottom: 4 }}>{t.name}</div>
                <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{t.role}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
