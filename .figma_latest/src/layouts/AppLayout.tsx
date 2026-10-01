import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { AppSidebar } from '../components/Nav'
import { useAuth } from '../contexts/AuthContext'


function TopBarRight() {
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
        <span className="topbar-username" style={{ fontSize: 13, color: hovered ? 'var(--c-dsp)' : 'var(--foreground)', fontFamily: 'var(--font-body)', fontWeight: 500, transition: 'color 0.15s' }}>
          {user?.name}
        </span>
      </button>
    )
  }

  return (
    <button
      onClick={() => navigate('/login')}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label="Log in"
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'transparent',
        border: '1px solid ' + (hovered ? 'var(--c-dsp)' : 'var(--border)'),
        borderRadius: 8, padding: '5px 14px',
        cursor: 'pointer',
        color: hovered ? 'var(--c-dsp)' : 'var(--muted-foreground)',
        fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500,
        transition: 'all 0.15s',
      }}
    >
      Log in
    </button>
  )
}

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="app-shell">
      {/* Mobile overlay */}
      <div
        className={`app-sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <div className={`app-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <AppSidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <div className="app-content">
        {/* Persistent global topbar — always visible, desktop + mobile */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 16px', height: 48,
          borderBottom: '1px solid var(--border)',
          background: 'var(--card)',
          flexShrink: 0,
          position: 'sticky', top: 0, zIndex: 50,
        }}>
          {/* Left: hamburger (mobile) + logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              className="mobile-menu-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)', fontSize: 18, padding: '4px 6px', borderRadius: 6, display: 'none' }}
            >
              ☰
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'linear-gradient(135deg, #7c6af7 0%, #2dd4bf 100%)', flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 15, color: 'var(--foreground)', letterSpacing: '-0.01em' }} className="dsp-logo-text">DSP</span>
            </div>
          </div>

          {/* Right: user name + Profile button */}
          <TopBarRight />
        </div>

        <Outlet />
      </div>

      <style>{`
        @media (max-width: 768px) {
          .mobile-menu-btn { display: flex !important; }
          .topbar-username { display: none !important; }
        }
        @media (min-width: 769px) {
          .mobile-menu-btn { display: none !important; }
          .dsp-logo-text { display: inline !important; }
        }
      `}</style>
    </div>
  )
}
