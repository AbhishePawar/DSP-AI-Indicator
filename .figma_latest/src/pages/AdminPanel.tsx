import { useState } from 'react'
import { TopBar } from '../components/Nav'
import { verifyAdminCredentials, setAdminSession, isAdminAuthed } from '../utils/adminAuth'

function AdminLogin({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (verifyAdminCredentials(email, password)) {
      setAdminSession()
      onLogin()
    } else {
      setError('Invalid admin credentials.')
    }
  }

  return (
    <div style={{
      minHeight: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--background)',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16,
        padding: '40px 36px', width: 360, display: 'flex', flexDirection: 'column', gap: 20,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg,#7c6af7,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#fff', fontWeight: 700 }}>⊕</div>
            <span style={{ fontFamily: 'var(--font-heading)', fontSize: 16, color: 'var(--foreground)' }}>DSP Admin</span>
          </div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, color: 'var(--foreground)', fontWeight: 500, margin: '0 0 6px' }}>Admin login</h2>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: 0 }}>Restricted access — authorised personnel only.</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { label: 'Admin email', type: 'email', value: email, set: setEmail, placeholder: 'admin@dspai.in' },
            { label: 'Password', type: 'password', value: password, set: setPassword, placeholder: '••••••••' },
          ].map(f => (
            <div key={f.label}>
              <label style={{ fontSize: 11, color: 'var(--muted-foreground)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{f.label}</label>
              <input
                type={f.type} value={f.value} placeholder={f.placeholder}
                onChange={e => f.set(e.target.value)}
                style={{ width: '100%', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box' }}
              />
            </div>
          ))}
        </div>

        {error && (
          <div style={{ fontSize: 12, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', background: 'color-mix(in srgb, var(--c-risk) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--c-risk) 25%, transparent)', borderRadius: 8, padding: '8px 12px' }}>
            {error}
          </div>
        )}

        <button type="submit" style={{
          background: 'var(--c-dsp)', color: '#fff', border: 'none', borderRadius: 10,
          padding: '12px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: 500,
        }}>
          Access Admin Panel
        </button>

        <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textAlign: 'center' }}>
          Use your DSP admin credentials to proceed.
        </div>
      </form>
    </div>
  )
}

const USERS = [
  { email: 'ananya.sharma@gmail.com', plan: 'Pro', joined: 'Aug 12, 2026', sessions: 84, status: 'Active' },
  { email: 'rajesh.m@hdfc.co.in', plan: 'Institutional', joined: 'Jul 3, 2026', sessions: 241, status: 'Active' },
  { email: 'priya.k@gmail.com', plan: 'Free', joined: 'Sep 1, 2026', sessions: 9, status: 'Active' },
  { email: 'vikram@investwise.in', plan: 'Pro', joined: 'Jun 15, 2026', sessions: 132, status: 'Suspended' },
]

function AdminPanelContent() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Admin Panel" subtitle="System administration · User management" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {[
            { label: 'Total Users', value: '1,842' },
            { label: 'Active Today', value: '284' },
            { label: 'Pro Subscribers', value: '412' },
            { label: 'API Calls Today', value: '24.2K' },
            { label: 'Avg Latency', value: '1.4s' },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontSize: 20, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 600 }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Users table */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>User Management</span>
            <input placeholder="Search users..." style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 12px', fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none', width: 200 }} />
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Email', 'Plan', 'Joined', 'Sessions', 'Status', ''].map(h => (
                  <th key={h} style={{ padding: '9px 20px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textAlign: 'left', borderBottom: '1px solid var(--border)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {USERS.map((u, i) => (
                <tr key={u.email} style={{ borderBottom: i < USERS.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  <td style={{ padding: '12px 20px', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{u.email}</td>
                  <td style={{ padding: '12px 20px' }}>
                    <span style={{ fontSize: 11, color: u.plan === 'Institutional' ? 'var(--c-dsp)' : u.plan === 'Pro' ? 'var(--c-profit)' : 'var(--muted-foreground)', fontFamily: 'var(--font-data)', background: 'var(--muted)', borderRadius: 6, padding: '2px 8px' }}>{u.plan}</span>
                  </td>
                  <td style={{ padding: '12px 20px', fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{u.joined}</td>
                  <td style={{ padding: '12px 20px', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{u.sessions}</td>
                  <td style={{ padding: '12px 20px' }}>
                    <span style={{ fontSize: 11, color: u.status === 'Active' ? 'var(--c-profit)' : 'var(--c-risk)', fontFamily: 'var(--font-data)' }}>{u.status}</span>
                  </td>
                  <td style={{ padding: '12px 20px' }}>
                    <button style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '3px 8px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function AdminPanel() {
  const [authed, setAuthed] = useState(() => isAdminAuthed())
  if (!authed) return <AdminLogin onLogin={() => setAuthed(true)} />
  return <AdminPanelContent />
}
