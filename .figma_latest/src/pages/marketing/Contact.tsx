import { useState } from 'react'

export default function Contact() {
  const [sent, setSent] = useState(false)
  return (
    <div>
      <section style={{ padding: '80px 48px 60px', textAlign: 'center' }}>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(32px, 5vw, 48px)', color: 'var(--foreground)', fontWeight: 500, margin: '0 0 14px', letterSpacing: '-0.02em' }}>Get in touch</h1>
        <p style={{ fontSize: 15, color: 'var(--muted-foreground)', maxWidth: 400, margin: '0 auto' }}>For enterprise inquiries, press, or general questions.</p>
      </section>

      <section style={{ padding: '0 48px 80px', maxWidth: 680, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48 }}>
        {/* Contact info */}
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 20px' }}>Contact</h2>
          {[
            { label: 'General', value: 'hello@dsp.in' },
            { label: 'Enterprise', value: 'enterprise@dsp.in' },
            { label: 'Press', value: 'press@dsp.in' },
            { label: 'Support', value: 'support@dsp.in' },
          ].map(c => (
            <div key={c.label} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{c.label}</div>
              <div style={{ fontSize: 14, color: 'var(--foreground)' }}>{c.value}</div>
            </div>
          ))}
        </div>

        {/* Form */}
        <div>
          {sent ? (
            <div style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', borderRadius: 12, padding: '24px', textAlign: 'center' }}>
              <div style={{ fontSize: 24, marginBottom: 12 }}>✓</div>
              <div style={{ fontSize: 15, color: 'var(--c-profit)', marginBottom: 8 }}>Message sent</div>
              <div style={{ fontSize: 13, color: 'var(--muted-foreground)' }}>We'll get back to you within 1–2 business days.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {['Name', 'Email'].map(l => (
                <div key={l}>
                  <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{l}</label>
                  <input type={l === 'Email' ? 'email' : 'text'} placeholder={l} style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 13px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }} />
                </div>
              ))}
              <div>
                <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Message</label>
                <textarea rows={4} placeholder="How can we help?" style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 13px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
              </div>
              <button onClick={() => setSent(true)} style={{ background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10, padding: '12px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: 500 }}>Send message</button>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
