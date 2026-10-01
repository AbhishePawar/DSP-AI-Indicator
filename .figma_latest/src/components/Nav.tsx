import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function SearchIcon({ size = 16, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8.5" cy="8.5" r="5.25" />
      <line x1="12.5" y1="12.5" x2="17" y2="17" />
    </svg>
  )
}

function PersonIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
    </svg>
  )
}

const RECENT_SEARCHES = [
  { label: 'Tata Consultancy Services', path: '/analysis?q=TCS' },
  { label: 'HDFC Bank Limited', path: '/analysis?q=HDFCBANK' },
  { label: 'Infosys Limited', path: '/analysis?q=INFY' },
]

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/dashboard', icon: '⬡' },
  { label: 'Research', path: '/research', icon: '◈' },
  { label: 'Companies', path: '/companies', icon: '⊞' },
  { label: 'Compare', path: '/compare', icon: '⇌' },
  { label: 'Portfolio', path: '/portfolio', icon: '◲' },
  { label: 'AI Copilot', path: '/copilot', icon: '✦' },
  { label: 'Advisor', path: '/advisor', icon: '◑' },
]

const BOTTOM_ITEMS = [
  { label: 'Financial Profile', path: '/profile', icon: '◎' },
  { label: 'Coupons & Offers', path: '/coupons', icon: '◈' },
  { label: 'Pricing', path: '/pricing', icon: '◇' },
  { label: 'Settings', path: '/control-center', icon: '⚙' },
]

function ResearchNavItem({ path, onClose }: { path: string; onClose?: () => void }) {
  const [hovered, setHovered] = useState(false)
  return (
    <NavLink
      to={path}
      onClick={onClose}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="Research"
      aria-label="Research"
      style={({ isActive }) => ({
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: 36, height: 36, borderRadius: 9, marginBottom: 2,
        textDecoration: 'none', flexShrink: 0,
        color: isActive ? 'var(--foreground)' : 'var(--muted-foreground)',
        background: isActive ? 'var(--muted)' : 'transparent',
        transition: 'color 0.15s, background 0.15s',
        position: 'relative',
      })}
    >
      <SearchIcon size={17} />
      {hovered && (
        <span style={{
          position: 'absolute', left: 'calc(100% + 10px)', top: '50%', transform: 'translateY(-50%)',
          background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 7,
          padding: '5px 11px', fontSize: 11.5, color: 'var(--foreground)', fontFamily: 'var(--font-data)',
          letterSpacing: '0.04em', whiteSpace: 'nowrap', pointerEvents: 'none', zIndex: 200,
          boxShadow: '0 4px 20px rgba(0,0,0,0.35)',
        }}>
          Research
          <span style={{
            position: 'absolute', right: '100%', top: '50%', transform: 'translateY(-50%)',
            borderWidth: '5px 5px 5px 0', borderStyle: 'solid',
            borderColor: 'transparent var(--border) transparent transparent',
          }} />
          <span style={{
            position: 'absolute', right: 'calc(100% - 1px)', top: '50%', transform: 'translateY(-50%)',
            borderWidth: '4px 4px 4px 0', borderStyle: 'solid',
            borderColor: 'transparent var(--card) transparent transparent',
          }} />
        </span>
      )}
    </NavLink>
  )
}

/** Reusable profile/account button — routes to /profile if logged in, /login if not */
function ProfileButton({ compact = false }: { compact?: boolean }) {
  const { isLoggedIn, user } = useAuth()
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(false)

  function handleClick() {
    navigate(isLoggedIn ? '/profile' : '/login')
  }

  const initials = user?.initials ?? ''

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={isLoggedIn ? 'My Profile' : 'Log in'}
      title={isLoggedIn ? `${user?.name} — My Profile` : 'Log in to your account'}
      style={{
        display: 'flex', alignItems: 'center', gap: compact ? 0 : 8,
        background: hovered ? 'var(--muted)' : 'transparent',
        border: '1px solid ' + (hovered ? 'var(--c-dsp)' : 'var(--border)'),
        borderRadius: 10, padding: compact ? '5px' : '5px 12px 5px 6px',
        cursor: 'pointer', color: hovered ? 'var(--c-dsp)' : 'var(--foreground)',
        fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500,
        transition: 'all 0.15s', flexShrink: 0,
      }}
    >
      {isLoggedIn ? (
        <div style={{
          width: 26, height: 26, borderRadius: '50%',
          background: 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, color: '#fff', fontWeight: 700, fontFamily: 'var(--font-data)',
          flexShrink: 0,
        }}>
          {initials}
        </div>
      ) : (
        <div style={{
          width: 26, height: 26, borderRadius: '50%',
          border: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--muted-foreground)', flexShrink: 0,
        }}>
          <PersonIcon size={14} />
        </div>
      )}
      {!compact && (
        <span>{isLoggedIn ? (user?.name?.split(' ')[0] ?? 'Profile') : 'Log in'}</span>
      )}
    </button>
  )
}

export function AppSidebar({ onClose }: { onClose?: () => void }) {
  const { isLoggedIn, user, logout } = useAuth()
  const navigate = useNavigate()

  function go(path: string) {
    navigate(path)
    onClose?.()
  }

  return (
    <aside style={{
      width: 220, background: 'var(--card)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', height: '100vh', flexShrink: 0,
    }}>
      {/* Logo */}
      <div
        style={{ padding: '20px 18px 16px', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
        onClick={() => go('/')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 26, height: 26, borderRadius: '50%',
            background: 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)',
          }} />
          <span style={{ fontFamily: 'var(--font-heading)', fontSize: 18, color: 'var(--foreground)', letterSpacing: '-0.01em' }}>DSP</span>
        </div>
        <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em', marginTop: 3 }}>
          AI RESEARCH
        </div>
      </div>

      {/* Start New Research */}
      <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={() => go('/analysis')}
          style={{
            width: '100%', background: 'var(--muted)', border: '1px solid var(--border)',
            borderRadius: 10, padding: '9px 12px', display: 'flex', alignItems: 'center',
            gap: 8, cursor: 'pointer', color: 'var(--foreground)', fontSize: 13,
            fontFamily: 'var(--font-body)', fontWeight: 500,
          }}
        >
          <span style={{ fontSize: 16, lineHeight: 1, color: 'var(--muted-foreground)' }}>+</span>
          Start New Research
        </button>
      </div>

      {/* Recent searches */}
      <div style={{ padding: '10px 14px 4px' }}>
        <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 6 }}>TODAY</div>
        {RECENT_SEARCHES.map((item, i) => (
          <NavLink
            key={i}
            to={item.path}
            onClick={onClose}
            style={({ isActive }) => ({
              display: 'block', padding: '7px 8px', borderRadius: 8, marginBottom: 2,
              fontSize: 12, textDecoration: 'none', fontFamily: 'var(--font-body)',
              color: isActive ? 'var(--foreground)' : 'var(--muted-foreground)',
              background: isActive ? 'var(--muted)' : 'transparent',
              transition: 'all 0.15s',
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </div>

      {/* DSP Indicator Analysis promo */}
      <div style={{ padding: '4px 14px 10px' }}>
        <NavLink
          to="/analysis"
          onClick={onClose}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'color-mix(in srgb, var(--c-cashflow) 12%, transparent)',
            border: '1px solid color-mix(in srgb, var(--c-cashflow) 30%, transparent)',
            borderRadius: 'var(--card-radius)', padding: '12px 14px', textDecoration: 'none',
            transition: 'background 0.15s',
          }}
        >
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-body)', marginBottom: 2 }}>
              DSP Buffett Indicator Analysis
            </div>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)', lineHeight: 1.4 }}>
              Evaluate a company using DSP's Buffett-style investment analysis framework.
            </div>
          </div>
          <span style={{ fontSize: 14, color: 'var(--c-cashflow)', flexShrink: 0, marginLeft: 8 }}>→</span>
        </NavLink>
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1, padding: '10px 10px', overflowY: 'auto' }}>
        {NAV_ITEMS.map(item => {
          if (item.label === 'Research') return (
            <div key={item.path} style={{ padding: '2px 10px', marginBottom: 2 }}>
              <ResearchNavItem path={item.path} onClose={onClose} />
            </div>
          )
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 10px', borderRadius: 8, marginBottom: 2,
                fontSize: 13, textDecoration: 'none', fontFamily: 'var(--font-body)',
                color: isActive ? 'var(--foreground)' : 'var(--muted-foreground)',
                background: isActive ? 'var(--muted)' : 'transparent',
                transition: 'all 0.15s',
              })}
            >
              <span style={{ fontSize: 14, opacity: 0.8 }}>{item.icon}</span>
              {item.label}
            </NavLink>
          )
        })}
        <div style={{ margin: '12px 0 8px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', paddingLeft: 10 }}>
          RESEARCH
        </div>
        {[
          { label: 'Research Hub', path: '/research' },
          { label: 'Institutional', path: '/research/institutional' },
          { label: 'Canvas', path: '/research/canvas' },
          { label: 'Intelligence', path: '/research/intelligence' },
        ].map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end
            onClick={onClose}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '7px 10px', borderRadius: 8, marginBottom: 2,
              fontSize: 12, textDecoration: 'none', fontFamily: 'var(--font-body)',
              color: isActive ? 'var(--foreground)' : 'var(--muted-foreground)',
              background: isActive ? 'var(--muted)' : 'transparent',
              transition: 'all 0.15s',
            })}
          >
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'currentColor', flexShrink: 0, marginLeft: 4 }} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div style={{ padding: '10px 10px', borderTop: '1px solid var(--border)' }}>
        {BOTTOM_ITEMS.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={onClose}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '7px 10px', borderRadius: 8, marginBottom: 2,
              fontSize: 12, textDecoration: 'none', fontFamily: 'var(--font-body)',
              color: isActive ? 'var(--foreground)' : 'var(--muted-foreground)',
              transition: 'color 0.15s',
            })}
          >
            <span style={{ fontSize: 13 }}>{item.icon}</span> {item.label}
          </NavLink>
        ))}
        <NavLink
          to="/admin"
          style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', fontSize: 12, textDecoration: 'none', color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)' }}
        >
          <span style={{ fontSize: 13 }}>⊕</span> Admin
        </NavLink>

        {/* User section */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 10px 4px', marginTop: 4, borderTop: '1px solid var(--border)',
        }}>
          {isLoggedIn ? (
            <>
              <button
                onClick={() => go('/profile')}
                aria-label="My Profile"
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, background: 'none',
                  border: 'none', cursor: 'pointer', padding: 0, flex: 1, minWidth: 0,
                }}
              >
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, color: '#fff', fontWeight: 700, fontFamily: 'var(--font-data)',
                  flexShrink: 0,
                }}>
                  {user?.initials}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-body)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{user?.plan}</div>
                </div>
              </button>
              <button
                onClick={logout}
                title="Log out"
                aria-label="Log out"
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', padding: '4px',
                  color: 'var(--muted-foreground)', fontSize: 12, flexShrink: 0,
                  borderRadius: 6, transition: 'color 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--foreground)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted-foreground)')}
              >
                ↩
              </button>
            </>
          ) : (
            <button
              onClick={() => go('/login')}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, background: 'none',
                border: 'none', cursor: 'pointer', padding: 0,
                color: 'var(--muted-foreground)', fontSize: 12, fontFamily: 'var(--font-body)',
              }}
            >
              <div style={{
                width: 28, height: 28, borderRadius: '50%', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <PersonIcon size={14} />
              </div>
              Log in
            </button>
          )}
        </div>
      </div>
    </aside>
  )
}

export function TopBar({ title, subtitle }: { title: string; subtitle?: string }) {
  const navigate = useNavigate()

  return (
    <header style={{
      padding: '14px 28px', borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexShrink: 0, background: 'var(--background)',
    }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 16, fontFamily: 'var(--font-heading)', color: 'var(--foreground)', fontWeight: 500 }}>{title}</h1>
        {subtitle && <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginTop: 2 }}>{subtitle}</div>}
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button
          onClick={() => navigate('/diagnostics')}
          style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 14px', color: 'var(--muted-foreground)', fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-body)' }}
        >
          Diagnostics
        </button>
        {/* Profile / Account button */}
        <ProfileButton />
      </div>
    </header>
  )
}

/** Compact profile icon-only for mobile topbars */
export function ProfileButtonCompact() {
  return <ProfileButton compact />
}
