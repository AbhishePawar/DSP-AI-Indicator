import { TopBar } from '../components/Nav'

const CHECKS = [
  { label: 'DSP API Gateway', status: 'Operational', latency: '142ms', color: 'var(--c-profit)' },
  { label: 'Financial Data Feed', status: 'Operational', latency: '38ms', color: 'var(--c-profit)' },
  { label: 'AI Research Engine', status: 'Operational', latency: '1.2s', color: 'var(--c-profit)' },
  { label: 'Database Cluster', status: 'Operational', latency: '8ms', color: 'var(--c-profit)' },
  { label: 'Market Data Provider', status: 'Degraded', latency: '890ms', color: 'var(--c-risk)' },
  { label: 'Email Service', status: 'Operational', latency: '22ms', color: 'var(--c-profit)' },
]

const LOGS = [
  { time: '14:32:01', level: 'INFO', msg: 'Research session initiated for TCS by user 1842' },
  { time: '14:31:58', level: 'WARN', msg: 'Market data provider latency spike detected: 890ms' },
  { time: '14:31:44', level: 'INFO', msg: 'DSP rating recalculated for TITAN: B+ → A' },
  { time: '14:31:30', level: 'INFO', msg: '24,201 API calls processed in last 24hr' },
  { time: '14:30:12', level: 'ERROR', msg: 'Market data provider: 3 timeouts in last 60s' },
  { time: '14:29:55', level: 'INFO', msg: 'Nightly financial data sync completed: 5,024 securities updated' },
]

export default function Diagnostics() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Diagnostics" subtitle="System health · Service status · Logs" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Overall status */}
        <div style={{ background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 12, padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--c-risk)' }} />
          <span style={{ fontSize: 14, color: 'var(--foreground)' }}>Partial degradation — Market data provider experiencing elevated latency.</span>
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginLeft: 'auto' }}>Sep 20, 2026 · 14:32 IST</span>
        </div>

        {/* Service checks */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>Service Status</span>
          </div>
          {CHECKS.map((c, i) => (
            <div key={c.label} style={{ padding: '14px 20px', borderBottom: i < CHECKS.length - 1 ? '1px solid var(--border)' : 'none', display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: c.color, flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: 'var(--foreground)', flex: 1 }}>{c.label}</span>
              <span style={{ fontSize: 12, color: c.color, fontFamily: 'var(--font-data)', width: 100 }}>{c.status}</span>
              <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', width: 60, textAlign: 'right' }}>{c.latency}</span>
            </div>
          ))}
        </div>

        {/* Log output */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>System Logs</span>
            <button style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontFamily: 'var(--font-data)' }}>Refresh</button>
          </div>
          <div style={{ background: '#06080e', padding: '16px 20px', fontFamily: 'var(--font-data)', fontSize: 12 }}>
            {LOGS.map((log, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 8, lineHeight: 1.5 }}>
                <span style={{ color: 'var(--muted-foreground)', flexShrink: 0 }}>{log.time}</span>
                <span style={{ color: log.level === 'ERROR' ? 'var(--c-risk)' : log.level === 'WARN' ? 'var(--c-risk)' : 'var(--c-profit)', flexShrink: 0, width: 44 }}>{log.level}</span>
                <span style={{ color: 'var(--foreground)' }}>{log.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
