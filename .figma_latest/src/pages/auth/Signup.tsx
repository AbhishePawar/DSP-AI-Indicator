import { Link } from 'react-router-dom'

export default function Signup() {
  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 6px', letterSpacing: '-0.01em' }}>Create account</h1>
      <p style={{ fontSize: 14, color: 'var(--muted-foreground)', margin: '0 0 32px' }}>Start researching with DSP for free</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Google */}
        <button style={{
          width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)',
          borderRadius: 10, padding: '12px', display: 'flex', alignItems: 'center',
          justifyContent: 'center', gap: 10, cursor: 'pointer', fontSize: 14,
          color: 'var(--foreground)', fontFamily: 'var(--font-body)', fontWeight: 500,
        }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
            <path d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.96L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </button>

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.05em' }}>OR</span>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {['First name', 'Last name'].map(l => (
            <div key={l}>
              <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{l}</label>
              <input placeholder={l} style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 13px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }} />
            </div>
          ))}
        </div>
        {['Email address', 'Password', 'Confirm password'].map((l, i) => (
          <div key={l}>
            <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{l}</label>
            <input type={i === 0 ? 'email' : 'password'} placeholder={i === 0 ? 'you@example.com' : '••••••••'} style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 13px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }} />
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginTop: 4 }}>
          <input type="checkbox" style={{ marginTop: 2, accentColor: 'var(--c-dsp)' }} />
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', lineHeight: 1.5 }}>I agree to the Terms of Service and Privacy Policy</span>
        </div>
        <button style={{ width: '100%', background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10, padding: '13px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: 500 }}>
          Create account
        </button>
        <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted-foreground)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--c-dsp)', textDecoration: 'none' }}>Log in</Link>
        </div>
      </div>
    </div>
  )
}
