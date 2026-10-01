import { Link } from 'react-router-dom'

export default function VerifyEmail() {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', fontSize: 28 }}>✉</div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 12px', letterSpacing: '-0.01em' }}>Check your email</h1>
      <p style={{ fontSize: 14, color: 'var(--muted-foreground)', margin: '0 0 32px', lineHeight: 1.65 }}>
        We sent a verification link to your email address. Click the link to confirm your account and start researching.
      </p>
      <div style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 20px', fontSize: 13, color: 'var(--muted-foreground)', marginBottom: 24, lineHeight: 1.6 }}>
        Didn't receive it? Check your spam folder, or{' '}
        <button style={{ background: 'none', border: 'none', color: 'var(--c-dsp)', cursor: 'pointer', fontSize: 13, fontFamily: 'var(--font-body)', padding: 0 }}>resend verification email</button>.
      </div>
      <Link to="/login" style={{ fontSize: 13, color: 'var(--muted-foreground)', textDecoration: 'none' }}>← Back to login</Link>
    </div>
  )
}
