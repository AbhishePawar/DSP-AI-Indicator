import { useState, useRef, useEffect } from 'react'
import { TopBar } from '../components/Nav'
import { useNavigate } from 'react-router-dom'

const SHORTCUTS = [
  { label: 'Find top quality stocks in IT sector', icon: '⬡' },
  { label: 'Which NIFTY 50 stocks have DSP rating A+?', icon: '◈' },
  { label: 'Screen for low debt, high ROE companies', icon: '◑' },
  { label: 'What sectors are showing valuation risk?', icon: '◇' },
  { label: 'Compare TCS vs Infosys growth trajectory', icon: '⇌' },
]

interface Msg { role: 'user' | 'dsp'; text: string }

const DEMO_RESPONSES: Record<string, string> = {
  default: "I can help you research any listed company, screen for quality stocks, or compare securities. What would you like to explore?",
  quality: "Based on the DSP Quality Model, the top-rated IT stocks right now are TCS (A+), Infosys (A), and HCL Technologies (A). These score highest on profitability, balance sheet strength, and cash generation. Would you like me to drill into any of these?",
  screen: "Screening across 5,000+ securities for low debt (D/E < 0.3) and high ROE (> 20%): I found 142 companies matching your criteria. Top results include TCS, Infosys, Asian Paints, Pidilite, and Abbott India. Want the full list or a deep dive on any?",
}

export default function AICopilot() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: 'dsp', text: DEMO_RESPONSES.default }
  ])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  function send(text: string) {
    if (!text.trim() || thinking) return
    setMessages(prev => [...prev, { role: 'user', text }])
    setInput('')
    setThinking(true)
    setTimeout(() => {
      setThinking(false)
      const key = text.toLowerCase().includes('quality') || text.toLowerCase().includes('top') ? 'quality'
        : text.toLowerCase().includes('screen') || text.toLowerCase().includes('roe') ? 'screen' : 'default'
      setMessages(prev => [...prev, { role: 'dsp', text: DEMO_RESPONSES[key] }])
    }, 1800)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="AI Copilot" subtitle="Cross-market intelligence · Screening · Discovery" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '28px 40px' }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', gap: 14, marginBottom: 24, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.role === 'dsp' && (
              <div style={{ width: 30, height: 30, borderRadius: '50%', flexShrink: 0, background: 'linear-gradient(135deg, #7c6af7, #2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#fff', fontWeight: 700, fontFamily: 'var(--font-data)', marginTop: 2 }}>D</div>
            )}
            <div style={{ maxWidth: '72%', background: msg.role === 'user' ? 'var(--secondary)' : 'var(--card)', border: '1px solid var(--border)', borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '4px 16px 16px 16px', padding: '12px 18px', fontSize: 14, color: 'var(--foreground)', lineHeight: 1.65 }}>
              {msg.text}
            </div>
          </div>
        ))}
        {thinking && (
          <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
            <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'linear-gradient(135deg, #7c6af7, #2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#fff', fontFamily: 'var(--font-data)' }}>D</div>
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '4px 16px 16px 16px', padding: '14px 18px', fontSize: 13, color: 'var(--muted-foreground)' }}>
              Analysing across 5,000+ securities...
            </div>
          </div>
        )}
        {messages.length === 1 && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 16, maxWidth: 600 }}>
            {SHORTCUTS.map(s => (
              <button key={s.label} onClick={() => send(s.label)}
                style={{ display: 'flex', alignItems: 'flex-start', gap: 10, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', cursor: 'pointer', textAlign: 'left', transition: 'border-color 0.15s' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.4)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
                <span style={{ color: 'var(--c-dsp)', fontSize: 16, flexShrink: 0 }}>{s.icon}</span>
                <span style={{ fontSize: 12, color: 'var(--muted-foreground)', lineHeight: 1.5 }}>{s.label}</span>
              </button>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ padding: '14px 40px 20px', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 10, background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 14px' }}
          onFocusCapture={e => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)')}
          onBlurCapture={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') send(input) }}
            placeholder="Ask DSP Copilot anything about the market..."
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)' }} />
          <button onClick={() => send(input)} style={{ width: 32, height: 32, borderRadius: '50%', background: input.trim() ? 'var(--c-dsp)' : 'var(--muted)', border: 'none', cursor: input.trim() ? 'pointer' : 'default', color: input.trim() ? '#fff' : 'var(--muted-foreground)', fontSize: 15 }}>↑</button>
        </div>
      </div>
    </div>
  )
}
