import { useState } from 'react'
import { Outlet, Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { verifyAdminCredentials, setAdminSession } from '../utils/adminAuth'

function AuthControls() {
  const { isLoggedIn } = useAuth()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {isLoggedIn ? (
        <AuthControl />
      ) : (
        <>
          <Link to="/login" style={{ fontSize: 13, padding: '7px 16px', borderRadius: 8, textDecoration: 'none', color: 'var(--muted-foreground)', border: '1px solid var(--border)', fontFamily: 'var(--font-body)' }}>
            Log in
          </Link>
          <Link to="/signup" style={{ fontSize: 13, padding: '7px 16px', borderRadius: 8, textDecoration: 'none', color: '#fff', background: 'var(--c-dsp)', fontFamily: 'var(--font-body)' }}>
            Get started
          </Link>
        </>
      )}
    </div>
  )
}

function AuthControl() {
  const { isLoggedIn, user } = useAuth()
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(false)

  if (isLoggedIn) {
    return (
      <button
        onClick={() => navigate('/profile')}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        aria-label={`${user?.name} — My Profile`}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: hovered ? 'var(--muted)' : 'transparent',
          border: '1px solid ' + (hovered ? 'var(--c-dsp)' : 'transparent'),
          borderRadius: 10, padding: '4px 10px 4px 4px',
          cursor: 'pointer', transition: 'all 0.15s',
        }}
      >
        <div style={{
          width: 26, height: 26, borderRadius: '50%',
          background: 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, color: '#fff', fontWeight: 700, fontFamily: 'var(--font-data)', flexShrink: 0,
        }}>
          {user?.initials ?? 'U'}
        </div>
        <span style={{ fontSize: 13, color: hovered ? 'var(--c-dsp)' : 'var(--foreground)', fontFamily: 'var(--font-body)', fontWeight: 500, transition: 'color 0.15s' }}>
          {user?.name}
        </span>
      </button>
    )
  }

  return null
}

function AdminLoginModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setTimeout(() => {
      if (verifyAdminCredentials(email, password)) {
        setAdminSession()
        onClose()
        navigate('/admin')
      } else {
        setError('Invalid admin credentials.')
      }
      setLoading(false)
    }, 400)
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Admin Login"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
    >
      <form
        onClick={e => e.stopPropagation()}
        onSubmit={handleSubmit}
        style={{
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: 16, padding: '36px 32px', width: '100%', maxWidth: 380,
          display: 'flex', flexDirection: 'column', gap: 20,
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'linear-gradient(135deg,#7c6af7,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#fff', fontWeight: 700 }}>⊕</div>
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 15, color: 'var(--foreground)' }}>DSP Admin</span>
            </div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 20, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 4px' }}>Admin login</h2>
            <p style={{ fontSize: 12, color: 'var(--muted-foreground)', margin: 0, fontFamily: 'var(--font-body)' }}>Restricted — authorised personnel only.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)', fontSize: 18, padding: '2px 6px', borderRadius: 6, lineHeight: 1 }}
          >
            ×
          </button>
        </div>

        {/* Fields */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Admin email</label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="admin@dspai.in" required autoComplete="username"
              style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 11, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPass ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••" required autoComplete="current-password"
                style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 44px 11px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }}
              />
              <button
                type="button"
                onClick={() => setShowPass(s => !s)}
                aria-label={showPass ? 'Hide password' : 'Show password'}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)', fontSize: 13, padding: 2 }}
              >
                {showPass ? '🙈' : '👁'}
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{ fontSize: 12, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', background: 'color-mix(in srgb, var(--c-risk) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--c-risk) 25%, transparent)', borderRadius: 8, padding: '8px 12px' }}>
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          style={{
            background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10,
            padding: '12px', fontSize: 14, cursor: loading ? 'wait' : 'pointer',
            fontFamily: 'var(--font-body)', fontWeight: 500, opacity: loading ? 0.7 : 1,
            transition: 'opacity 0.15s',
          }}
        >
          {loading ? 'Verifying…' : 'Access Admin Panel'}
        </button>
      </form>
    </div>
  )
}

export default function MarketingLayout() {
  const [adminModalOpen, setAdminModalOpen] = useState(false)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--background)', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        padding: '16px 48px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'var(--card)', position: 'sticky', top: 0, zIndex: 10,
      }}>
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'linear-gradient(135deg, #7c6af7, #2dd4bf)' }} />
          <span style={{ fontFamily: 'var(--font-heading)', fontSize: 18, color: 'var(--foreground)' }}>DSP</span>
        </Link>
        <nav style={{ display: 'flex', gap: 4 }}>
          {[
            { label: 'About', path: '/about' },
            { label: 'Pricing', path: '/pricing' },
            { label: 'FAQ', path: '/faq' },
            { label: 'Contact', path: '/contact' },
          ].map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                fontSize: 13, padding: '6px 12px', borderRadius: 6, textDecoration: 'none',
                color: isActive ? 'var(--foreground)' : 'var(--muted-foreground)',
                fontFamily: 'var(--font-body)',
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <AuthControls />
      </header>

      <main style={{ flex: 1 }}>
        <Outlet />
      </main>

      <footer style={{ padding: '28px 48px', borderTop: '1px solid var(--border)' }}>
        {/* Main footer row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 16, color: 'var(--muted-foreground)' }}>DSP AI Indicator</div>
          <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>© 2026 · All rights reserved</div>
        </div>

        {/* Admin access — subtle, bottom of footer */}
        <div style={{ borderTop: '1px solid color-mix(in srgb, var(--border) 50%, transparent)', paddingTop: 14, display: 'flex', justifyContent: 'center' }}>
          <button
            onClick={() => setAdminModalOpen(true)}
            aria-label="Admin Login"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 11, color: 'color-mix(in srgb, var(--muted-foreground) 50%, transparent)',
              fontFamily: 'var(--font-data)', letterSpacing: '0.05em',
              padding: '4px 10px', borderRadius: 6,
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--muted-foreground)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'color-mix(in srgb, var(--muted-foreground) 50%, transparent)')}
          >
            Admin Login
          </button>
        </div>
      </footer>

      {adminModalOpen && <AdminLoginModal onClose={() => setAdminModalOpen(false)} />}
    </div>
  )
}
