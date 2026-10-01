import { Link } from 'react-router-dom'

export default function ResetPassword() {
  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 6px', letterSpacing: '-0.01em' }}>Set new password</h1>
      <p style={{ fontSize: 14, color: 'var(--muted-foreground)', margin: '0 0 32px' }}>Choose a strong password for your account.</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {['New password', 'Confirm password'].map(l => (
          <div key={l}>
            <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{l}</label>
            <input type="password" placeholder="••••••••" style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }} />
          </div>
        ))}
        <button style={{ width: '100%', background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10, padding: '13px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: 500 }}>Update password</button>
        <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted-foreground)' }}>
          <Link to="/login" style={{ color: 'var(--c-dsp)', textDecoration: 'none' }}>← Back to login</Link>
        </div>
      </div>
    </div>
  )
}
