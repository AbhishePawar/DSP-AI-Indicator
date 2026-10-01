import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleLogin() {
    const name = email ? email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'User'
    const initials = name.split(' ').slice(0, 2).map((w: string) => w[0]).join('').toUpperCase()
    login({ name, email: email || 'user@example.com', initials })
    navigate('/dashboard')
  }

  function Field({ label, type, value, onChange, placeholder }: { label: string; type: string; value: string; onChange: (v: string) => void; placeholder: string }) {
    return (
      <div>
        <label style={{ fontSize: 12, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</label>
        <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }} />
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 6px', letterSpacing: '-0.01em' }}>Welcome back</h1>
      <p style={{ fontSize: 14, color: 'var(--muted-foreground)', margin: '0 0 32px' }}>Log in to your DSP account</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        {/* Google */}
        <button onClick={handleLogin} style={{
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

        <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
        <div>
          <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
          <div style={{ textAlign: 'right', marginTop: 8 }}>
            <Link to="/forgot-password" style={{ fontSize: 12, color: 'var(--c-dsp)', textDecoration: 'none' }}>Forgot password?</Link>
          </div>
        </div>
        <button
          onClick={handleLogin}
          style={{ width: '100%', background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10, padding: '13px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: 500, marginTop: 8 }}
        >
          Log in
        </button>
        <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted-foreground)' }}>
          Don't have an account?{' '}
          <Link to="/signup" style={{ color: 'var(--c-dsp)', textDecoration: 'none' }}>Sign up free</Link>
        </div>
      </div>
    </div>
  )
}
