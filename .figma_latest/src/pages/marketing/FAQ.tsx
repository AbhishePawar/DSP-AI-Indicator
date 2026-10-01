import { useState } from 'react'

const FAQS = [
  { q: 'What is DSP AI Indicator?', a: 'DSP is a chat-first equity research platform. You ask questions in plain English about any listed company, and DSP answers with conversational responses backed by real financial data and visual evidence.' },
  { q: 'How is DSP different from a stock screener?', a: 'Screeners give you raw data. DSP gives you answers. Instead of sorting a table by P/E ratio, you ask "Is TCS expensive?" and DSP tells you whether it is, why, and what the evidence shows — with a chart to back it up.' },
  { q: 'What is the DSP Quality Rating?', a: 'The DSP Indicator is a proprietary quality score (A+ to D) built on 40+ financial metrics including profitability, balance sheet strength, cash generation, leverage, and valuation consistency. It is updated dynamically as new data becomes available.' },
  { q: 'How many companies does DSP cover?', a: 'DSP covers 5,000+ listed Indian securities. The DSP Quality Rating is available on 3,841 securities that have sufficient financial data. Coverage is expanding continuously.' },
  { q: 'Can I use DSP for free?', a: 'Yes. The Free plan gives you 10 research sessions per month, full access to Company Analysis, and the DSP Quality Rating for every covered security. No credit card required.' },
  { q: 'What is a research session?', a: 'A research session is one active research conversation about a specific company. You can ask as many follow-up questions as you want within a session — only starting a new company counts as a new session.' },
  { q: 'Does DSP give buy/sell recommendations?', a: 'No. DSP provides financial research and evidence to support your own decision-making. It is a research tool, not a financial advisor. Always consult a qualified advisor for investment decisions.' },
  { q: 'Is my data safe?', a: 'Yes. We do not share your research conversations or portfolio data with any third party. Your research history is private and encrypted.' },
]

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(0)
  return (
    <div>
      <section style={{ padding: '80px 48px 60px', textAlign: 'center' }}>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(32px, 5vw, 48px)', color: 'var(--foreground)', fontWeight: 500, margin: '0 0 14px', letterSpacing: '-0.02em' }}>Frequently asked questions</h1>
        <p style={{ fontSize: 15, color: 'var(--muted-foreground)', maxWidth: 480, margin: '0 auto' }}>Everything you need to know about DSP.</p>
      </section>
      <section style={{ padding: '0 48px 80px', maxWidth: 680, margin: '0 auto' }}>
        {FAQS.map((faq, i) => (
          <div key={i} style={{ borderBottom: '1px solid var(--border)', overflow: 'hidden' }}>
            <button onClick={() => setOpen(open === i ? null : i)}
              style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 0', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', gap: 16 }}>
              <span style={{ fontSize: 15, color: 'var(--foreground)', fontFamily: 'var(--font-body)', lineHeight: 1.4 }}>{faq.q}</span>
              <span style={{ fontSize: 18, color: 'var(--muted-foreground)', flexShrink: 0, transform: open === i ? 'rotate(45deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>+</span>
            </button>
            {open === i && (
              <div style={{ paddingBottom: 20, fontSize: 14, color: 'var(--muted-foreground)', lineHeight: 1.75 }}>{faq.a}</div>
            )}
          </div>
        ))}
      </section>
    </div>
  )
}
