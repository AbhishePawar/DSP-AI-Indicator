import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function ForgotPassword() {
  const [sent, setSent] = useState(false)
  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 6px', letterSpacing: '-0.01em' }}>Reset password</h1>
      <p style={{ fontSize: 14, color: 'var(--muted-foreground)', margin: '0 0 32px', lineHeight: 1.6 }}>
        {sent ? "We've sent a reset link to your email. Check your inbox." : "Enter your email and we'll send you a reset link."}
      </p>
      {!sent ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Email address</label>
            <input type="email" placeholder="you@example.com" style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }} />
          </div>
          <button onClick={() => setSent(true)} style={{ width: '100%', background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10, padding: '13px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: 500 }}>Send reset link</button>
        </div>
      ) : (
        <div style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.25)', borderRadius: 10, padding: '16px 20px', fontSize: 13, color: 'var(--c-profit)', marginBottom: 20 }}>
          ✓ Reset link sent — check your email inbox
        </div>
      )}
      <div style={{ marginTop: 20, textAlign: 'center', fontSize: 13, color: 'var(--muted-foreground)' }}>
        <Link to="/login" style={{ color: 'var(--c-dsp)', textDecoration: 'none' }}>← Back to login</Link>
      </div>
    </div>
  )
}
