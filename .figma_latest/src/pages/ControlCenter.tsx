import { useState } from 'react'
import { TopBar } from '../components/Nav'

function Toggle({ on, onChange }: { on: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange} style={{ width: 40, height: 22, borderRadius: 99, background: on ? 'var(--c-dsp)' : 'var(--muted)', border: '1px solid var(--border)', cursor: 'pointer', position: 'relative', transition: 'background 0.2s', flexShrink: 0 }}>
      <div style={{ width: 16, height: 16, borderRadius: '50%', background: '#fff', position: 'absolute', top: 2, left: on ? 20 : 2, transition: 'left 0.2s' }} />
    </button>
  )
}

export default function ControlCenter() {
  const [settings, setSettings] = useState({
    notifications: true, dspAlerts: true, peerComparisons: false,
    darkMode: true, compactView: false, betaFeatures: false,
    autoResearch: false, emailDigest: true,
  })

  function toggle(key: keyof typeof settings) {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const SECTIONS = [
    {
      title: 'Notifications',
      items: [
        { key: 'notifications', label: 'Push Notifications', desc: 'Browser notifications for DSP signal changes' },
        { key: 'dspAlerts', label: 'DSP Rating Alerts', desc: 'Notify when a watchlist company rating changes' },
        { key: 'emailDigest', label: 'Weekly Email Digest', desc: 'Summary of top DSP signals every Monday' },
      ]
    },
    {
      title: 'Research Preferences',
      items: [
        { key: 'peerComparisons', label: 'Auto-show Peer Comparison', desc: 'Automatically surface peer data in research responses' },
        { key: 'autoResearch', label: 'Auto-research on Search', desc: 'Start research immediately when you select a company' },
      ]
    },
    {
      title: 'Interface',
      items: [
        { key: 'darkMode', label: 'Dark Mode', desc: 'Use dark color scheme across all pages' },
        { key: 'compactView', label: 'Compact View', desc: 'Reduce spacing in tables and lists' },
        { key: 'betaFeatures', label: 'Beta Features', desc: 'Enable experimental features (may be unstable)' },
      ]
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Control Center" subtitle="System settings · Preferences" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* Account */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'linear-gradient(135deg, #7c6af7, #2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: '#fff', fontWeight: 600 }}>U</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, color: 'var(--foreground)', fontWeight: 500 }}>User Account</div>
            <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>user@example.com · Pro Plan</div>
          </div>
          <button style={{ fontSize: 13, color: 'var(--foreground)', background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Edit Profile</button>
          <button style={{ fontSize: 13, color: 'var(--c-risk)', background: 'none', border: '1px solid rgba(251,191,36,0.3)', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Log out</button>
        </div>

        {/* Settings sections */}
        {SECTIONS.map(section => (
          <div key={section.title} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>{section.title}</span>
            </div>
            {section.items.map((item, i) => (
              <div key={item.key} style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: i < section.items.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <div>
                  <div style={{ fontSize: 13, color: 'var(--foreground)', marginBottom: 3 }}>{item.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{item.desc}</div>
                </div>
                <Toggle on={settings[item.key as keyof typeof settings]} onChange={() => toggle(item.key as keyof typeof settings)} />
              </div>
            ))}
          </div>
        ))}

        {/* Danger zone */}
        <div style={{ background: 'var(--card)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--c-risk)', marginBottom: 12 }}>Danger Zone</div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button style={{ fontSize: 13, color: 'var(--c-risk)', background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Clear Research History</button>
            <button style={{ fontSize: 13, color: 'var(--c-risk)', background: 'none', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Delete Account</button>
          </div>
        </div>
      </div>
    </div>
  )
}
