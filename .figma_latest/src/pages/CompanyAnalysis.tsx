import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { recordSearch } from '../utils/searchTracking'
import { useAuth } from '../contexts/AuthContext'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

// ─── Types ───────────────────────────────────────────────────────────────────

type Phase = 'select' | 'simple-loading' | 'simple-result' | 'buffett-loading' | 'buffett-result'
type Status = 'strong' | 'adequate' | 'weak' | 'unavailable'
type ChatMsg = { role: 'user' | 'dsp'; text: string }

// ─── Demo data (TCS) ─────────────────────────────────────────────────────────

const revenueData = [
  { year: 'FY22', value: 1917 }, { year: 'FY23', value: 2254 },
  { year: 'FY24', value: 2408 }, { year: 'FY25', value: 2551 }, { year: 'FY26', value: 2703 },
]
const profitData = [
  { year: 'FY22', value: 382 }, { year: 'FY23', value: 421 },
  { year: 'FY24', value: 455 }, { year: 'FY25', value: 487 }, { year: 'FY26', value: 519 },
]
const marginData = [
  { year: 'FY22', value: 19.9 }, { year: 'FY23', value: 18.7 },
  { year: 'FY24', value: 18.9 }, { year: 'FY25', value: 19.1 }, { year: 'FY26', value: 19.2 },
]
const cashData = [
  { year: 'FY22', value: 5900 }, { year: 'FY23', value: 6800 },
  { year: 'FY24', value: 7400 }, { year: 'FY25', value: 8100 }, { year: 'FY26', value: 8420 },
]

const LOADING_STEPS = [
  'Identifying company',
  'Collecting financial evidence',
  'Analysing business quality',
  'Evaluating economic moat',
  'Evaluating management',
  'Analysing earnings & growth',
  'Evaluating valuation',
  'Assessing risks',
  'Validating research',
  'Preparing analysis report',
]

// ─── TOC with groups ──────────────────────────────────────────────────────────

const TOC_GROUPS = [
  {
    label: 'ANALYSIS',
    items: [
      { id: 's01', label: 'Summary' },
      { id: 's03', label: 'Buffett Assessment' },
      { id: 's04', label: 'Financials' },
      { id: 's09', label: 'Valuation' },
      { id: 's02', label: 'Business Quality' },
      { id: 's11', label: 'Key Risks' },
    ],
  },
  {
    label: 'DEEP DIVE',
    items: [
      { id: 's06', label: 'Management' },
      { id: 's07', label: 'Earnings Quality' },
      { id: 's08', label: 'Growth Quality' },
      { id: 's10', label: 'Margin of Safety' },
      { id: 's12', label: 'Strengths & Weaknesses' },
      { id: 's13', label: 'Investment Context' },
      { id: 's14', label: 'Evidence' },
    ],
  },
]

const BUFFETT_ROWS: { dim: string; result: string; status: Status }[] = [
  { dim: 'Understandable Business', result: 'Strong', status: 'strong' },
  { dim: 'Durable Economic Moat', result: 'Strong', status: 'strong' },
  { dim: 'Management Quality', result: 'Strong', status: 'strong' },
  { dim: 'Financial Strength', result: 'Strong', status: 'strong' },
  { dim: 'Earnings Consistency', result: 'Strong', status: 'strong' },
  { dim: 'Debt Position', result: 'Minimal debt', status: 'strong' },
  { dim: 'Return on Equity', result: '49%', status: 'strong' },
  { dim: 'Cash Generation', result: 'Strong', status: 'strong' },
  { dim: 'Valuation', result: 'Premium to intrinsic value', status: 'weak' },
  { dim: 'Margin of Safety', result: 'Negative (−18%)', status: 'weak' },
]

const DOMAIN_SCORES = [
  { label: 'Economic Moat', weight: 25, score: 88, color: 'var(--c-dsp)' },
  { label: 'Management Quality', weight: 20, score: 84, color: 'var(--c-revenue)' },
  { label: 'Financial Strength', weight: 20, score: 91, color: 'var(--c-profit)' },
  { label: 'Earnings Quality', weight: 20, score: 86, color: 'var(--c-cashflow)' },
  { label: 'Growth Quality', weight: 15, score: 78, color: 'var(--c-valuation)' },
]

const RISKS = [
  { risk: 'Valuation Risk', evidence: 'Trading at 27× PE vs sector median 22×', implication: 'Limited upside; elevated downside risk if growth slows' },
  { risk: 'Revenue Concentration', evidence: 'BFSI segment ~32% of revenue', implication: 'Vulnerability to financial-sector spending cycles' },
  { risk: 'Margin Pressure', evidence: 'Wage inflation 8–10% annually, offshore utilisation at ceiling', implication: 'Operating leverage may compress if revenue growth decelerates' },
  { risk: 'Currency Risk', evidence: '85% revenue in foreign currency (USD/EUR/GBP)', implication: 'INR appreciation materially reduces rupee-reported earnings' },
]

const STRENGTHS = [
  'Consistently high ROE (49%) sustained over 5+ years',
  'Near-zero debt with ₹8,420 Bn cash equivalents',
  'Market leadership across BFSI, retail, manufacturing verticals',
  'Attrition normalised to 12.5% vs peak 17.4%',
  'Dividend yield supported by strong free cash flow',
]

const WEAKNESSES = [
  'Current market price implies negative margin of safety',
  'Revenue growth decelerating (7% FY26 vs 10% FY24)',
  'Large employee base creates execution complexity',
  'Low differentiation risk from commoditised IT services',
]

const EVIDENCE_ITEMS = [
  { metric: 'ROE', value: '49%', period: 'FY26', source: 'Company Filings / NSE', stage: 'Financial Analysis', confidence: 'High' },
  { metric: 'Revenue', value: '₹2,703 Bn', period: 'FY26', source: 'Company Filings', stage: 'Financial Analysis', confidence: 'High' },
  { metric: 'Net Profit', value: '₹519 Bn', period: 'FY26', source: 'Company Filings', stage: 'Financial Analysis', confidence: 'High' },
  { metric: 'D/E Ratio', value: '0.03×', period: 'FY26', source: 'BSE / Screener', stage: 'Financial Strength', confidence: 'High' },
  { metric: 'Intrinsic Value', value: '₹3,240', period: 'FY26 est.', source: 'DSP Valuation Engine', stage: 'Valuation', confidence: 'Medium' },
  { metric: 'Market Price', value: '₹3,850', period: 'Current', source: 'NSE', stage: 'Valuation', confidence: 'High' },
]

const CHAT_RESPONSES: Record<string, string> = {
  moat: "TCS's economic moat is assessed as Strong based on client switching costs — large enterprises typically face 18–24 month migration cycles, deep integration of TCS systems into core banking and ERP infrastructure, and established workforce pipelines. The moat is further supported by the Tata brand, which reduces procurement risk for institutional buyers.",
  valuation: "The current market price of ₹3,850 exceeds the DSP Intrinsic Value estimate of ₹3,240, producing a negative margin of safety of approximately −18.8%. This means a buyer at current prices is paying a premium to the assessed intrinsic value. Business quality remains high; the valuation concern is price, not fundamentals.",
  quality: "The Business Quality score of 87 reflects a weighted composite: Financial Strength (91/100, weight 20%), Economic Moat (88/100, weight 25%), Earnings Quality (86/100, weight 20%), Management Quality (84/100, weight 20%), and Growth Quality (78/100, weight 15%). The primary drag is growth deceleration.",
  risk: "The most material risk is valuation — the stock trades at a premium to intrinsic value. Secondary risks are revenue concentration in BFSI (~32%) and margin pressure from annual wage inflation. Currency risk is structural given 85% of revenue is denominated in foreign currency.",
  default: "I can answer questions about this TCS analysis — business quality, the Buffett assessment, specific financial metrics, valuation assumptions, or the evidence behind any conclusion. What would you like to understand better?",
}

// ─── Shared components ────────────────────────────────────────────────────────

function StatusBadge({ status, text }: { status: Status; text?: string }) {
  const map: Record<Status, { color: string; bg: string; label: string }> = {
    strong:      { color: 'var(--c-profit)',    bg: 'rgba(52,211,153,0.1)',  label: 'Strong' },
    adequate:    { color: 'var(--c-revenue)',   bg: 'rgba(56,189,248,0.1)',  label: 'Adequate' },
    weak:        { color: 'var(--c-risk)',      bg: 'rgba(251,191,36,0.1)',  label: 'Weak' },
    unavailable: { color: 'var(--muted-foreground)', bg: 'rgba(107,122,153,0.1)', label: 'Unavailable' },
  }
  const s = map[status]
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 99,
      background: s.bg, border: `1px solid ${s.color}33`,
      fontSize: 11, color: s.color, fontFamily: 'var(--font-data)',
      letterSpacing: '0.04em', whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
      {text ?? s.label}
    </span>
  )
}

function SectionHead({ id, num, title, status, subtitle }: {
  id: string; num: string; title: string; status?: Status; subtitle?: string
}) {
  return (
    <div id={id} style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em' }}>{num}</span>
        <h2 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 500, color: 'var(--foreground)', letterSpacing: '-0.01em' }}>{title}</h2>
        {status && <StatusBadge status={status} />}
      </div>
      {subtitle && <p style={{ margin: 0, fontSize: 13, color: 'var(--muted-foreground)', lineHeight: 1.6 }}>{subtitle}</p>}
    </div>
  )
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '20px 22px', ...style,
    }}>
      {children}
    </div>
  )
}

function AskButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'none', border: '1px solid var(--border)', borderRadius: 20,
        padding: '5px 13px', fontSize: 12, color: 'var(--muted-foreground)',
        cursor: 'pointer', fontFamily: 'var(--font-body)',
        transition: 'border-color 0.15s, color 0.15s',
        whiteSpace: 'nowrap',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)'; e.currentTarget.style.color = 'var(--foreground)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--muted-foreground)' }}
    >
      {label}
    </button>
  )
}

function ChartTip({ active, payload, label, suffix = '' }: {
  active?: boolean; payload?: Array<{ value: number; color: string }>; label?: string; suffix?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: 11, fontFamily: 'var(--font-data)' }}>
      <div style={{ color: 'var(--muted-foreground)', marginBottom: 3 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>{p.value.toLocaleString()}{suffix}</div>
      ))}
    </div>
  )
}

// ─── Selection screen ─────────────────────────────────────────────────────────

function SelectionScreen({ symbol, onSimple, onBuffett }: {
  symbol: string; onSimple: () => void; onBuffett: () => void
}) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px' }}>
      <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em' }}>COMPANY ANALYSIS</div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(24px,4vw,36px)', fontWeight: 500, color: 'var(--foreground)', margin: '0 0 8px', letterSpacing: '-0.02em', textAlign: 'center' }}>
        {symbol || 'Select a company'}
      </h1>
      <p style={{ fontSize: 14, color: 'var(--muted-foreground)', margin: '0 0 48px', textAlign: 'center' }}>Choose your research depth</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, width: '100%', maxWidth: 660 }}>
        <button
          onClick={onSimple}
          style={{
            background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14,
            padding: '28px 28px', textAlign: 'left', cursor: 'pointer',
            transition: 'border-color 0.18s, box-shadow 0.18s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(56,189,248,0.5)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.2)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
        >
          <div style={{ fontSize: 22, marginBottom: 12 }}>◈</div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 17, fontWeight: 500, color: 'var(--foreground)', marginBottom: 8 }}>Simple Research</div>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', lineHeight: 1.65, margin: '0 0 20px' }}>
            Get a quick overview — key metrics, financial summary, strengths, risks, and valuation context.
          </p>
          <span style={{ display: 'inline-block', padding: '8px 18px', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, color: 'var(--c-revenue)', fontFamily: 'var(--font-body)' }}>
            Research →
          </span>
        </button>

        <button
          onClick={onBuffett}
          style={{
            background: 'var(--card)', border: '1px solid rgba(124,106,247,0.35)', borderRadius: 14,
            padding: '28px 28px', textAlign: 'left', cursor: 'pointer',
            transition: 'border-color 0.18s, box-shadow 0.18s',
            boxShadow: '0 0 0 1px rgba(124,106,247,0.08)',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(124,106,247,0.7)'; e.currentTarget.style.boxShadow = '0 8px 32px rgba(124,106,247,0.18)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(124,106,247,0.35)'; e.currentTarget.style.boxShadow = '0 0 0 1px rgba(124,106,247,0.08)' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: 'linear-gradient(135deg,#7c6af7,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#fff', fontWeight: 700 }}>D</div>
            <span style={{ fontSize: 10, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em' }}>FLAGSHIP</span>
          </div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 17, fontWeight: 500, color: 'var(--foreground)', marginBottom: 8 }}>DSP Buffett Indicator Analysis</div>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', lineHeight: 1.65, margin: '0 0 20px' }}>
            Complete evidence-driven analysis — business quality, economic moat, management, earnings, growth, valuation, and margin of safety.
          </p>
          <span style={{ display: 'inline-block', padding: '8px 18px', background: 'var(--c-dsp)', border: 'none', borderRadius: 8, fontSize: 13, color: '#fff', fontFamily: 'var(--font-body)' }}>
            Analyse →
          </span>
        </button>
      </div>
    </div>
  )
}

// ─── Skeleton primitives ──────────────────────────────────────────────────────

function Skel({ w, h, style }: { w?: string | number; h?: number; style?: React.CSSProperties }) {
  return (
    <div style={{
      width: w ?? '100%', height: h ?? 14,
      background: 'var(--secondary)', borderRadius: 6,
      animation: 'skel-pulse 1.6s ease-in-out infinite',
      flexShrink: 0,
      ...style,
    }} />
  )
}

function SkeletonReport() {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header skeleton */}
      <div style={{ padding: '18px 28px 16px', borderBottom: '1px solid var(--border)', background: 'var(--card)', flexShrink: 0 }}>
        <Skel w={120} h={10} style={{ marginBottom: 10 }} />
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
          <Skel w={280} h={26} />
          <Skel w={80} h={20} style={{ borderRadius: 99 }} />
        </div>
        <div style={{ display: 'flex', gap: 0, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
          {[100, 70, 60, 55, 55, 120, 100].map((w, i) => (
            <div key={i} style={{ paddingRight: 20, paddingLeft: i === 0 ? 0 : 20, borderLeft: i > 0 ? '1px solid var(--border)' : 'none' }}>
              <Skel w={w * 0.6} h={9} style={{ marginBottom: 6 }} />
              <Skel w={w} h={12} />
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar skeleton */}
        <div style={{ width: 200, flexShrink: 0, borderRight: '1px solid var(--border)', padding: '16px', display: 'flex', flexDirection: 'column', gap: 8 }} className="toc-sidebar">
          {[80, 100, 90, 85, 95, 88, 0, 80, 90, 85, 92, 88, 86].map((w, i) =>
            w === 0 ? <div key={i} style={{ height: 1, background: 'var(--border)', margin: '4px 0' }} />
            : <Skel key={i} w={w} h={11} />
          )}
        </div>
        {/* Content skeleton */}
        <div style={{ flex: 1, padding: '28px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Summary hero */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: 22 }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <Skel w={140} h={16} style={{ borderRadius: 99 }} />
              <Skel w={120} h={16} style={{ borderRadius: 99 }} />
            </div>
            <Skel h={18} style={{ marginBottom: 8 }} />
            <Skel w="85%" h={18} style={{ marginBottom: 20 }} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 20 }}>
              {[0,1,2].map(i => <div key={i} style={{ background: 'var(--secondary)', borderRadius: 10, padding: 14 }}><Skel w={70} h={9} style={{ marginBottom: 8 }} /><Skel w="60%" h={22} style={{ marginBottom: 6 }} /><Skel w={80} h={10} /></div>)}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[0,1].map(i => <div key={i} style={{ background: 'var(--secondary)', borderRadius: 10, padding: 14 }}>{[0,1,2].map(j => <Skel key={j} h={12} style={{ marginBottom: 8 }} />)}</div>)}
            </div>
          </div>
          {/* Table skeleton */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 22 }}>
            <Skel w={160} h={12} style={{ marginBottom: 16 }} />
            {[0,1,2,3,4].map(i => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '11px 0', borderBottom: '1px solid var(--border)' }}>
                <Skel w={180} h={12} />
                <Skel w={80} h={20} style={{ borderRadius: 99 }} />
              </div>
            ))}
          </div>
        </div>
      </div>
      <style>{`@keyframes skel-pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
    </div>
  )
}

// ─── Staged loader ────────────────────────────────────────────────────────────

function StagedLoader({ steps, active, onDone }: { steps: string[]; active: number; onDone: () => void }) {
  useEffect(() => {
    if (active >= steps.length) { onDone(); return }
  }, [active, steps.length, onDone])

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px' }}>
      <div style={{ marginBottom: 8, fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em' }}>DSP BUFFETT INDICATOR ANALYSIS</div>
      <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, fontWeight: 500, color: 'var(--foreground)', margin: '0 0 6px' }}>Preparing your analysis…</h2>
      <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: '0 0 36px' }}>This typically takes 10–15 seconds.</p>
      <div style={{ width: '100%', maxWidth: 440 }}>
        {steps.map((step, i) => {
          const done = i < active
          const current = i === active
          return (
            <div key={step} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '11px 0', borderBottom: '1px solid var(--border)',
              opacity: i > active + 1 ? 0.35 : 1,
              transition: 'opacity 0.3s',
            }}>
              <span style={{
                fontSize: 13, fontFamily: 'var(--font-body)',
                color: done ? 'var(--muted-foreground)' : current ? 'var(--foreground)' : 'var(--muted-foreground)',
                fontWeight: current ? 500 : 400,
              }}>{step}</span>
              {done && <span style={{ color: 'var(--c-profit)', fontSize: 13 }}>✓</span>}
              {current && (
                <span style={{ display: 'flex', gap: 3 }}>
                  {[0,1,2].map(d => (
                    <span key={d} style={{
                      width: 5, height: 5, borderRadius: '50%', background: 'var(--c-dsp)',
                      animation: `pulse 1.2s ${d * 0.2}s ease-in-out infinite`,
                    }} />
                  ))}
                </span>
              )}
              {!done && !current && <span style={{ color: 'var(--border)', fontSize: 13 }}>○</span>}
            </div>
          )
        })}
      </div>
      <style>{`@keyframes pulse { 0%,100%{opacity:0.3;transform:scale(0.8)} 50%{opacity:1;transform:scale(1)} }`}</style>
    </div>
  )
}

// ─── Simple research result ───────────────────────────────────────────────────

function SimpleResult({ symbol, onUpgrade }: { symbol: string; onUpgrade: () => void }) {
  return (
    <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '28px 28px' }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 6 }}>SIMPLE RESEARCH</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, fontWeight: 500, color: 'var(--foreground)', margin: 0 }}>
            {symbol || 'TCS'} — Tata Consultancy Services
          </h1>
          <StatusBadge status="strong" text="High Quality" />
        </div>
        <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>NSE: TCS</span>
          <span style={{ fontSize: 12, color: 'var(--c-revenue)', fontFamily: 'var(--font-data)' }}>₹3,850.40</span>
          <span style={{ fontSize: 12, color: 'var(--c-risk)', fontFamily: 'var(--font-data)' }}>−0.8% today</span>
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>Mcap ₹13.9L Cr</span>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 16 }}>
        <Card>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 14 }}>KEY METRICS</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(130px,1fr))', gap: 12 }}>
            {[
              { l: 'ROE', v: '49%', c: 'var(--c-profit)' },
              { l: 'ROCE', v: '66%', c: 'var(--c-profit)' },
              { l: 'Revenue', v: '₹2,703 Bn', c: 'var(--c-revenue)' },
              { l: 'Net Profit', v: '₹519 Bn', c: 'var(--c-cashflow)' },
              { l: 'D/E', v: '0.03×', c: 'var(--muted-foreground)' },
              { l: 'PE Ratio', v: '27.4×', c: 'var(--c-valuation)' },
            ].map(m => (
              <div key={m.l} style={{ background: 'var(--secondary)', borderRadius: 8, padding: '12px 14px' }}>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 6 }}>{m.l}</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: m.c, fontFamily: 'var(--font-data)' }}>{m.v}</div>
              </div>
            ))}
          </div>
        </Card>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 16 }}>
          <Card>
            <div style={{ fontSize: 11, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 12 }}>KEY STRENGTHS</div>
            {STRENGTHS.slice(0, 3).map((s, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 10, fontSize: 13, color: 'var(--foreground)', lineHeight: 1.5 }}>
                <span style={{ color: 'var(--c-profit)', flexShrink: 0, marginTop: 2 }}>+</span>{s}
              </div>
            ))}
          </Card>
          <Card>
            <div style={{ fontSize: 11, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 12 }}>KEY RISKS</div>
            {RISKS.slice(0, 3).map((r, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 13, color: 'var(--foreground)', fontWeight: 500, marginBottom: 2 }}>{r.risk}</div>
                <div style={{ fontSize: 12, color: 'var(--muted-foreground)', lineHeight: 1.5 }}>{r.evidence}</div>
              </div>
            ))}
          </Card>
        </div>

        <Card>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 14 }}>VALUATION SUMMARY</div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 12 }}>
            {[
              { l: 'Market Price', v: '₹3,850', c: 'var(--foreground)' },
              { l: 'Intrinsic Value (DSP)', v: '₹3,240', c: 'var(--c-cashflow)' },
              { l: 'Margin of Safety', v: '−18.8%', c: 'var(--c-risk)' },
            ].map(v => (
              <div key={v.l}>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 4 }}>{v.l}</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: v.c, fontFamily: 'var(--font-data)' }}>{v.v}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.6 }}>
            TCS trades at a premium to its assessed intrinsic value, resulting in a negative margin of safety.
            Business quality is high; the concern is price, not fundamentals.
          </p>
        </Card>

        <div style={{
          border: '1px solid rgba(124,106,247,0.3)', borderRadius: 12, padding: '20px 22px',
          background: 'rgba(124,106,247,0.04)',
        }}>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 15, color: 'var(--foreground)', marginBottom: 6 }}>Want the complete analysis?</div>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: '0 0 14px', lineHeight: 1.6 }}>
            Get the full DSP Buffett Indicator Analysis — economic moat, earnings quality, management assessment, intrinsic value methodology, and follow-up chat.
          </p>
          <button onClick={onUpgrade}
            style={{ padding: '9px 20px', background: 'var(--c-dsp)', border: 'none', borderRadius: 8, fontSize: 13, color: '#fff', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
            Run DSP Buffett Indicator Analysis →
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Company header bar ───────────────────────────────────────────────────────

function CompanyHeader({ symbol }: { symbol: string }) {
  return (
    <div style={{
      padding: '18px 28px 16px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--card)',
      flexShrink: 0,
    }}>
      {/* Identity row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 5 }}>
            DSP BUFFETT INDICATOR ANALYSIS
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(20px,2.8vw,28px)', fontWeight: 500, color: 'var(--foreground)', margin: 0, letterSpacing: '-0.02em' }}>
              Tata Consultancy Services
            </h1>
            <span style={{ fontFamily: 'var(--font-data)', fontSize: 13, color: 'var(--muted-foreground)' }}>
              {symbol || 'TCS'} · NSE · BSE: 532540
            </span>
            <StatusBadge status="strong" text="High Quality" />
          </div>
        </div>
        {/* Market snapshot */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <span style={{ fontFamily: 'var(--font-data)', fontSize: 22, fontWeight: 700, color: 'var(--foreground)', letterSpacing: '-0.01em' }}>₹3,850.40</span>
          <span style={{ fontFamily: 'var(--font-data)', fontSize: 12, color: 'var(--c-risk)', padding: '2px 7px', background: 'rgba(251,191,36,0.1)', borderRadius: 4 }}>−0.8% −31.20</span>
        </div>
      </div>
      {/* Metrics strip */}
      <div className="company-header-metrics" style={{ display: 'flex', gap: 0, flexWrap: 'wrap', borderTop: '1px solid var(--border)', paddingTop: 12 }}>
        {[
          { l: 'Market Cap', v: '₹13.9L Cr' },
          { l: 'Sector', v: 'IT Services' },
          { l: 'ROE', v: '49%' },
          { l: 'D/E', v: '0.03×' },
          { l: 'PE', v: '27.4×' },
          { l: '52W Range', v: '₹3,311 – ₹4,592' },
          { l: 'Analysis date', v: new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) },
        ].map((m, i, arr) => (
          <div key={m.l} style={{
            paddingRight: 20, paddingLeft: i === 0 ? 0 : 20,
            borderLeft: i > 0 ? '1px solid var(--border)' : 'none',
            marginBottom: 4,
          }}>
            <div style={{ fontSize: 9, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 3 }}>{m.l.toUpperCase()}</div>
            <div style={{ fontSize: 12, fontWeight: 500, color: i < arr.length - 2 ? 'var(--foreground)' : 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{m.v}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Investment summary section (S01) ─────────────────────────────────────────

function InvestmentSummary({ onAsk }: { onAsk: (ctx: string) => void }) {
  return (
    <div id="s01" style={{ marginBottom: 36 }}>
      {/* Thesis card */}
      <div style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 14,
        overflow: 'hidden',
        marginBottom: 16,
      }}>
        {/* Header band */}
        <div style={{
          padding: '16px 22px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10,
          background: 'rgba(124,106,247,0.04)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em' }}>01 — ANALYSIS SUMMARY</span>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <StatusBadge status="strong" text="High Business Quality" />
            <StatusBadge status="weak" text="Valuation Premium" />
          </div>
        </div>

        {/* Thesis body */}
        <div style={{ padding: '20px 22px' }}>
          <p style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(14px,1.6vw,17px)', color: 'var(--foreground)', lineHeight: 1.75, margin: '0 0 16px', fontWeight: 400, letterSpacing: '-0.005em' }}>
            TCS is a high-quality business with a strong economic moat, consistently excellent financials, and conservative capital structure. The primary concern at current prices is valuation — the stock trades above assessed intrinsic value, offering a negative margin of safety. This is a research finding, not a buy or sell instruction.
          </p>

          {/* Three-column scorecard */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 12, marginBottom: 20 }}>
            {[
              { l: 'Business Quality', v: '86 / 100', sub: 'High Quality', color: 'var(--c-profit)', border: 'var(--c-profit)' },
              { l: 'Valuation', v: '−18.8%', sub: 'Negative margin of safety', color: 'var(--c-risk)', border: 'var(--c-risk)' },
              { l: 'Intrinsic Value', v: '₹3,240', sub: 'vs price ₹3,850', color: 'var(--c-cashflow)', border: 'var(--border)' },
            ].map(s => (
              <div key={s.l} style={{ background: 'var(--secondary)', borderRadius: 10, padding: '14px 16px', borderTop: `2px solid ${s.border}` }}>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 6 }}>{s.l.toUpperCase()}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: s.color, fontFamily: 'var(--font-heading)', lineHeight: 1, marginBottom: 4 }}>{s.v}</div>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{s.sub}</div>
              </div>
            ))}
          </div>

          {/* Positives / Concerns two-col */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12, marginBottom: 20 }}>
            <div style={{ background: 'rgba(52,211,153,0.04)', border: '1px solid rgba(52,211,153,0.15)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 10, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 10 }}>WHAT'S WORKING</div>
              {STRENGTHS.slice(0, 3).map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, fontSize: 12, color: 'var(--foreground)', lineHeight: 1.55 }}>
                  <span style={{ color: 'var(--c-profit)', flexShrink: 0 }}>+</span>{s}
                </div>
              ))}
            </div>
            <div style={{ background: 'rgba(251,191,36,0.04)', border: '1px solid rgba(251,191,36,0.15)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 10, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 10 }}>WHAT TO WATCH</div>
              {WEAKNESSES.slice(0, 3).map((w, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, fontSize: 12, color: 'var(--foreground)', lineHeight: 1.55 }}>
                  <span style={{ color: 'var(--c-risk)', flexShrink: 0 }}>−</span>{w}
                </div>
              ))}
            </div>
          </div>

          {/* Contextual ask chips */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', alignSelf: 'center' }}>Ask:</span>
            {[
              { label: 'Why is valuation a concern?', ctx: 'valuation and intrinsic value' },
              { label: 'What is the biggest risk?', ctx: 'key risks' },
              { label: 'Explain the moat', ctx: 'economic moat' },
              { label: 'How good is the quality score?', ctx: 'Business Quality score' },
            ].map(c => (
              <AskButton key={c.label} label={c.label} onClick={() => onAsk(c.ctx)} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Buffett report ───────────────────────────────────────────────────────────

function BuffettReport({ symbol, chatOpen, onChatOpen, chatCtx, onChatCtx }: {
  symbol: string
  chatOpen: boolean
  onChatOpen: () => void
  chatCtx: string
  onChatCtx: (ctx: string) => void
}) {
  const [activeSection, setActiveSection] = useState('s01')
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [tocOpen, setTocOpen] = useState(false)
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({})

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        for (const e of entries) {
          if (e.isIntersecting) setActiveSection(e.target.id)
        }
      },
      { rootMargin: '-30% 0px -60% 0px', threshold: 0 },
    )
    Object.values(sectionRefs.current).forEach(el => el && observer.observe(el))
    return () => observer.disconnect()
  }, [])

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setTocOpen(false)
  }

  function askAbout(ctx: string) {
    onChatCtx(ctx)
    onChatOpen()
  }

  function sectionRef(id: string) {
    return (el: HTMLDivElement | null) => { sectionRefs.current[id] = el }
  }

  const bqScore = 86

  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative', flexDirection: 'column' }}>
      {/* Company header */}
      <CompanyHeader symbol={symbol} />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        {/* Sidebar TOC — desktop */}
        <aside style={{
          width: 200, flexShrink: 0, borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', overflow: 'auto',
          padding: '16px 0',
        }} className="toc-sidebar">
          {TOC_GROUPS.map(group => (
            <div key={group.label} style={{ marginBottom: 8 }}>
              <div style={{ padding: '0 16px 8px', fontSize: 9, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.12em' }}>
                {group.label}
              </div>
              {group.items.map(t => (
                <button key={t.id} onClick={() => scrollTo(t.id)}
                  style={{
                    background: activeSection === t.id ? 'var(--muted)' : 'none',
                    border: 'none', padding: '7px 16px', textAlign: 'left', cursor: 'pointer', width: '100%',
                    fontSize: 12, fontFamily: 'var(--font-body)',
                    color: activeSection === t.id ? 'var(--foreground)' : 'var(--muted-foreground)',
                    borderLeft: activeSection === t.id ? '2px solid var(--c-dsp)' : '2px solid transparent',
                    transition: 'all 0.15s',
                  }}>
                  {t.label}
                </button>
              ))}
              <div style={{ height: 1, background: 'var(--border)', margin: '8px 16px' }} />
            </div>
          ))}

          {/* Tools section */}
          <div style={{ padding: '0 16px 8px', fontSize: 9, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.12em' }}>TOOLS</div>
          <button onClick={onChatOpen}
            style={{
              margin: '0 10px 6px', padding: '9px 12px', background: chatOpen ? 'var(--c-dsp)' : 'var(--secondary)',
              border: `1px solid ${chatOpen ? 'var(--c-dsp)' : 'var(--border)'}`,
              borderRadius: 8, color: chatOpen ? '#fff' : 'var(--muted-foreground)', fontSize: 12, cursor: 'pointer',
              fontFamily: 'var(--font-body)', fontWeight: 500, transition: 'all 0.15s',
              display: 'flex', alignItems: 'center', gap: 7,
            }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 2.5C1 1.67 1.67 1 2.5 1h7C10.33 1 11 1.67 11 2.5v5c0 .83-.67 1.5-1.5 1.5H7l-2.5 2v-2H2.5C1.67 9 1 8.33 1 7.5v-5z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
            </svg>
            Ask DSP
          </button>
          <button
            style={{
              margin: '0 10px', padding: '9px 12px', background: 'none',
              border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--muted-foreground)', fontSize: 12, cursor: 'pointer',
              fontFamily: 'var(--font-body)', fontWeight: 400,
              display: 'flex', alignItems: 'center', gap: 7,
            }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1v6M3.5 5l2.5 2.5L8.5 5M2.5 9.5h7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Export
          </button>
        </aside>

        {/* Mobile bottom sheet nav */}
        <div className="toc-mobile-toggle">
          {/* Floating action bar */}
          <div style={{
            position: 'fixed', bottom: chatOpen ? 292 : 16, left: 16, right: 16, zIndex: 60,
            display: 'flex', gap: 10, justifyContent: 'center',
            transition: 'bottom 0.25s ease',
          }}>
            <button onClick={() => setTocOpen(v => !v)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 20px', background: 'var(--card)',
                border: '1px solid var(--border)', borderRadius: 99,
                fontSize: 13, color: 'var(--foreground)', cursor: 'pointer',
                fontFamily: 'var(--font-body)', fontWeight: 500,
                boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
              }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 3h12M1 7h8M1 11h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Sections
            </button>
            <button onClick={onChatOpen}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 20px', background: chatOpen ? 'var(--c-dsp)' : 'var(--card)',
                border: `1px solid ${chatOpen ? 'var(--c-dsp)' : 'var(--border)'}`, borderRadius: 99,
                fontSize: 13, color: chatOpen ? '#fff' : 'var(--foreground)', cursor: 'pointer',
                fontFamily: 'var(--font-body)', fontWeight: 500,
                boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
              }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 3C1 2 2 1 3 1h8c1 0 2 1 2 2v5c0 1-1 2-2 2H8L5 13v-3H3c-1 0-2-1-2-2V3z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
              </svg>
              Ask DSP
            </button>
          </div>

          {/* Bottom sheet overlay */}
          {tocOpen && (
            <>
              <div
                onClick={() => setTocOpen(false)}
                style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 70 }}
              />
              <div style={{
                position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 80,
                background: 'var(--card)', borderTop: '1px solid var(--border)',
                borderRadius: '16px 16px 0 0',
                paddingBottom: 'env(safe-area-inset-bottom, 16px)',
                animation: 'slide-up 0.22s ease',
                maxHeight: '75vh', overflow: 'auto',
              }}>
                {/* Handle */}
                <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 4px' }}>
                  <div style={{ width: 36, height: 4, background: 'var(--border)', borderRadius: 99 }} />
                </div>
                <div style={{ padding: '8px 0 20px' }}>
                  {TOC_GROUPS.map(group => (
                    <div key={group.label} style={{ marginBottom: 4 }}>
                      <div style={{ padding: '8px 20px 6px', fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em' }}>
                        {group.label}
                      </div>
                      {group.items.map(t => (
                        <button key={t.id} onClick={() => scrollTo(t.id)}
                          style={{
                            display: 'flex', width: '100%', alignItems: 'center',
                            background: activeSection === t.id ? 'var(--muted)' : 'none',
                            border: 'none', padding: '11px 20px', textAlign: 'left', cursor: 'pointer',
                            fontSize: 14, fontFamily: 'var(--font-body)',
                            color: activeSection === t.id ? 'var(--foreground)' : 'var(--muted-foreground)',
                            gap: 10,
                          }}>
                          {activeSection === t.id && <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--c-dsp)', flexShrink: 0 }} />}
                          {t.label}
                        </button>
                      ))}
                      <div style={{ height: 1, background: 'var(--border)', margin: '4px 20px' }} />
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
          <style>{`@keyframes slide-up { from { transform: translateY(100%) } to { transform: translateY(0) } }`}</style>
        </div>

        {/* Report content */}
        <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '28px 28px', paddingBottom: chatOpen ? '280px' : '40px' }}>

          {/* S01 — Investment Summary (new hero) */}
          <div ref={sectionRef('s01')}>
            <InvestmentSummary onAsk={askAbout} />
          </div>

          {/* S03 — Buffett Assessment */}
          <div ref={sectionRef('s03')} style={{ marginBottom: 36 }}>
            <SectionHead id="s03" num="02" title="Buffett-Style Assessment" subtitle="DSP analytical outputs organised through a Buffett-inspired investment framework." />
            <Card>
              <div className="table-scroll">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ textAlign: 'left', padding: '8px 12px', fontFamily: 'var(--font-data)', fontSize: 10, letterSpacing: '0.08em', color: 'var(--muted-foreground)', fontWeight: 400 }}>DIMENSION</th>
                      <th style={{ textAlign: 'left', padding: '8px 12px', fontFamily: 'var(--font-data)', fontSize: 10, letterSpacing: '0.08em', color: 'var(--muted-foreground)', fontWeight: 400 }}>RESULT</th>
                      <th style={{ textAlign: 'left', padding: '8px 12px', fontFamily: 'var(--font-data)', fontSize: 10, letterSpacing: '0.08em', color: 'var(--muted-foreground)', fontWeight: 400 }}>STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {BUFFETT_ROWS.map((r, i) => (
                      <tr key={r.dim} style={{ borderBottom: i < BUFFETT_ROWS.length - 1 ? '1px solid var(--border)' : 'none' }}>
                        <td style={{ padding: '11px 12px', color: 'var(--foreground)', fontFamily: 'var(--font-body)' }}>{r.dim}</td>
                        <td style={{ padding: '11px 12px', color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', fontSize: 12 }}>{r.result}</td>
                        <td style={{ padding: '11px 12px' }}><StatusBadge status={r.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
              <AskButton label="Ask about this assessment" onClick={() => askAbout('Buffett assessment')} />
            </div>
          </div>

          {/* S04 — Financial Analysis */}
          <div ref={sectionRef('s04')} style={{ marginBottom: 36 }}>
            <SectionHead id="s04" num="03" title="Financial Analysis" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(130px,1fr))', gap: 10, marginBottom: 16 }}>
              {[
                { l: 'Revenue FY26', v: '₹2,703 Bn', c: 'var(--c-revenue)' },
                { l: 'Net Profit', v: '₹519 Bn', c: 'var(--c-profit)' },
                { l: 'ROE', v: '49%', c: 'var(--c-profit)' },
                { l: 'ROCE', v: '66%', c: 'var(--c-profit)' },
                { l: 'EBITDA Margin', v: '26.4%', c: 'var(--c-cashflow)' },
                { l: 'D/E Ratio', v: '0.03×', c: 'var(--muted-foreground)' },
                { l: 'EPS (FY26)', v: '₹140.8', c: 'var(--c-valuation)' },
                { l: 'Free Cash Flow', v: '₹498 Bn', c: 'var(--c-cashflow)' },
              ].map(m => (
                <div key={m.l} style={{ background: 'var(--secondary)', borderRadius: 8, padding: '12px 14px' }}>
                  <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em', marginBottom: 4 }}>{m.l}</div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: m.c, fontFamily: 'var(--font-data)' }}>{m.v}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
              <Card>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 12 }}>REVENUE TREND · ₹ Bn · Source: Company Filings</div>
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={revenueData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <defs><linearGradient id="gr" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--c-revenue)" stopOpacity={0.15} /><stop offset="95%" stopColor="var(--c-revenue)" stopOpacity={0} /></linearGradient></defs>
                    <XAxis dataKey="year" tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTip />} />
                    <Area type="monotone" dataKey="value" stroke="var(--c-revenue)" strokeWidth={2} fill="url(#gr)" name="Revenue" />
                  </AreaChart>
                </ResponsiveContainer>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginTop: 8 }}>Steady growth — CAGR 7.1% over 5 years, decelerating from 10% in FY24.</div>
              </Card>
              <Card>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 12 }}>NET PROFIT TREND · ₹ Bn · Source: Company Filings</div>
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={profitData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <defs><linearGradient id="gp" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--c-profit)" stopOpacity={0.15} /><stop offset="95%" stopColor="var(--c-profit)" stopOpacity={0} /></linearGradient></defs>
                    <XAxis dataKey="year" tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTip />} />
                    <Area type="monotone" dataKey="value" stroke="var(--c-profit)" strokeWidth={2} fill="url(#gp)" name="Profit" />
                  </AreaChart>
                </ResponsiveContainer>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginTop: 8 }}>Consistent profit expansion — margins stable between 18.7–19.2% over 5 years.</div>
              </Card>
            </div>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
              <AskButton label="Ask about the financials" onClick={() => askAbout('financial analysis')} />
            </div>
          </div>

          {/* S09 — Valuation */}
          <div ref={sectionRef('s09')} style={{ marginBottom: 36 }}>
            <SectionHead id="s09" num="04" title="Valuation & Intrinsic Value" status="weak" />
            <Card style={{ marginBottom: 14 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 24, marginBottom: 20 }}>
                {[
                  { l: 'Current Market Price', v: '₹3,850', c: 'var(--foreground)', sub: 'NSE · Current' },
                  { l: 'DSP Intrinsic Value', v: '₹3,240', c: 'var(--c-cashflow)', sub: 'FY26 estimate' },
                  { l: 'Margin of Safety', v: '−18.8%', c: 'var(--c-risk)', sub: 'Negative · Price above value' },
                ].map(v => (
                  <div key={v.l} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 6 }}>{v.l}</div>
                    <div style={{ fontSize: 32, fontWeight: 700, color: v.c, fontFamily: 'var(--font-heading)', lineHeight: 1, marginBottom: 4 }}>{v.v}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{v.sub}</div>
                  </div>
                ))}
              </div>
              <div style={{ margin: '0 0 16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontFamily: 'var(--font-data)', color: 'var(--muted-foreground)', marginBottom: 6 }}>
                  <span>₹0</span><span>₹3,240 Intrinsic</span><span>₹3,850 Price</span>
                </div>
                <div style={{ height: 10, background: 'var(--border)', borderRadius: 99, overflow: 'hidden', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${(3240 / 4200) * 100}%`, background: 'var(--c-cashflow)', borderRadius: 99 }} />
                  <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${(3850 / 4200) * 100}%`, background: 'var(--c-risk)', borderRadius: 99, opacity: 0.4 }} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginTop: 6 }}>
                  Premium of ₹610 (18.8%) above assessed intrinsic value.
                </div>
              </div>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 6 }}>METHODOLOGY</div>
              <p style={{ fontSize: 13, color: 'var(--foreground)', margin: 0, lineHeight: 1.7 }}>
                DSP Intrinsic Value is calculated using normalised earnings, growth assumptions, and a risk-adjusted discount rate. The result is backend-authoritative and is not a frontend estimate.
              </p>
            </Card>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <AskButton label="Why is valuation a concern?" onClick={() => askAbout('valuation and intrinsic value')} />
            </div>
          </div>

          {/* S02 — Business Quality */}
          <div ref={sectionRef('s02')} style={{ marginBottom: 36 }}>
            <SectionHead id="s02" num="05" title="Business Quality" status="strong" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 16, marginBottom: 16 }} className="bq-grid">
              <Card style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', gap: 8, borderTop: '2px solid var(--c-profit)' }}>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em' }}>COMPOSITE SCORE</div>
                <div style={{ fontSize: 56, fontWeight: 700, color: 'var(--c-profit)', fontFamily: 'var(--font-heading)', lineHeight: 1 }}>{bqScore}</div>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>/ 100</div>
                <StatusBadge status="strong" text="High Quality" />
                <p style={{ fontSize: 12, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.6 }}>
                  Weighted across 5 analytical domains.
                </p>
              </Card>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(140px,1fr))', gap: 10 }}>
                {DOMAIN_SCORES.map(d => (
                  <Card key={d.label} style={{ borderTop: `2px solid ${d.color}`, padding: '14px 16px' }}>
                    <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em', marginBottom: 6 }}>{d.label.toUpperCase()}</div>
                    <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginBottom: 8 }}>Weight: {d.weight}%</div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, marginBottom: 8 }}>
                      <span style={{ fontSize: 24, fontWeight: 700, color: d.color, fontFamily: 'var(--font-heading)', lineHeight: 1 }}>{d.score}</span>
                      <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>/100</span>
                    </div>
                    <div style={{ height: 3, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
                      <div style={{ width: `${d.score}%`, height: '100%', background: d.color, borderRadius: 99 }} />
                    </div>
                  </Card>
                ))}
              </div>
            </div>

            {/* Economic Moat inline */}
            <Card style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 4 }}>ECONOMIC MOAT</div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--c-profit)', fontFamily: 'var(--font-heading)', marginBottom: 10 }}>Strong</div>
                  <p style={{ fontSize: 13, color: 'var(--foreground)', lineHeight: 1.7, margin: '0 0 12px' }}>
                    Enterprise migrations average 18–24 months. Deep integration across core banking, ERP, and supply chain infrastructure creates high switching costs. The Tata brand further reduces procurement risk for institutional buyers.
                  </p>
                  <AskButton label="Explain the moat" onClick={() => askAbout('economic moat')} />
                </div>
                <div style={{ textAlign: 'center', flexShrink: 0 }}>
                  <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 4 }}>SCORE</div>
                  <div style={{ fontSize: 48, fontWeight: 700, color: 'var(--c-dsp)', fontFamily: 'var(--font-heading)', lineHeight: 1, marginBottom: 4 }}>88</div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>/ 100</div>
                </div>
              </div>
            </Card>

            <Card style={{ borderLeft: '3px solid var(--c-risk)' }}>
              <div style={{ fontSize: 10, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 6 }}>QUALITY NOTE</div>
              <p style={{ fontSize: 13, color: 'var(--foreground)', margin: '0 0 8px', lineHeight: 1.65 }}>
                Growth quality is partially offset by revenue growth deceleration — 7% FY26 vs 10% FY24 — reducing the durability assessment relative to the financial strength score.
              </p>
              <AskButton label="Ask why this score was assigned" onClick={() => askAbout('Business Quality score and the quality conflict')} />
            </Card>
          </div>

          {/* S11 — Key Risks */}
          <div ref={sectionRef('s11')} style={{ marginBottom: 36 }}>
            <SectionHead id="s11" num="06" title="Key Risks" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {RISKS.map((r, i) => (
                <Card key={i} style={{ borderLeft: '3px solid var(--c-risk)' }}>
                  <div style={{ fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 500, color: 'var(--foreground)', marginBottom: 6 }}>{r.risk}</div>
                  <div style={{ display: 'flex', gap: 6, marginBottom: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 10, fontFamily: 'var(--font-data)', color: 'var(--muted-foreground)', letterSpacing: '0.07em' }}>EVIDENCE</span>
                    <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{r.evidence}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 10, fontFamily: 'var(--font-data)', color: 'var(--c-risk)', letterSpacing: '0.07em' }}>IMPLICATION</span>
                    <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{r.implication}</span>
                  </div>
                </Card>
              ))}
            </div>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
              <AskButton label="What is the biggest risk?" onClick={() => askAbout('key risks')} />
            </div>
          </div>

          {/* ── DEEP DIVE sections ── */}

          {/* S06 — Management */}
          <div ref={sectionRef('s06')} style={{ marginBottom: 36 }}>
            <SectionHead id="s06" num="— Management & Capital Allocation" title="" status="strong"
              subtitle="How is the business being led and how is capital being deployed?" />
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Management & Capital Allocation
              <StatusBadge status="strong" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
              <Card>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 10 }}>MANAGEMENT QUALITY</div>
                <StatusBadge status="strong" />
                <p style={{ fontSize: 13, color: 'var(--foreground)', margin: '12px 0 0', lineHeight: 1.7 }}>
                  Leadership has maintained consistent delivery through multiple economic cycles. Attrition normalised to 12.5% from peak 17.4%, signalling operational stability.
                </p>
              </Card>
              <Card>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 10 }}>CAPITAL ALLOCATION</div>
                {[
                  { l: 'Dividends', v: '₹126 Bn (FY26)', s: 'strong' as Status },
                  { l: 'Buybacks', v: '₹17,000 Cr (FY26)', s: 'strong' as Status },
                  { l: 'Acquisitions', v: 'Selective / bolt-on', s: 'adequate' as Status },
                  { l: 'Reinvestment', v: 'R&D + AI platforms', s: 'adequate' as Status },
                ].map(r => (
                  <div key={r.l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 13, color: 'var(--foreground)' }}>{r.l}</span>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{r.v}</span>
                      <StatusBadge status={r.s} />
                    </div>
                  </div>
                ))}
              </Card>
            </div>
          </div>

          {/* S07 — Earnings Quality */}
          <div ref={sectionRef('s07')} style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Earnings Quality
              <StatusBadge status="strong" />
            </div>
            <SectionHead id="s07" num="" title="Earnings Quality" status="strong"
              subtitle="Are reported earnings durable and supported by the underlying business?" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
              <Card>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 12 }}>NET MARGIN TREND · % · FY22–FY26</div>
                <ResponsiveContainer width="100%" height={110}>
                  <AreaChart data={marginData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <XAxis dataKey="year" tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} domain={[17, 22]} />
                    <Tooltip content={<ChartTip suffix="%" />} />
                    <Area type="monotone" dataKey="value" stroke="var(--c-cashflow)" strokeWidth={2} fill="rgba(45,212,191,0.08)" name="Margin" />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
              <Card>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 10 }}>INDICATORS</div>
                {[
                  { l: 'Cash Conversion', v: '96%', s: 'strong' as Status },
                  { l: 'Margin Stability', v: '18.7–19.2% (5yr)', s: 'strong' as Status },
                  { l: 'Earnings Consistency', v: 'Positive 10yr+', s: 'strong' as Status },
                  { l: 'Revenue Visibility', v: 'High (long-cycle)', s: 'strong' as Status },
                ].map(r => (
                  <div key={r.l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 13, color: 'var(--foreground)' }}>{r.l}</span>
                    <StatusBadge status={r.s} text={r.v} />
                  </div>
                ))}
              </Card>
            </div>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
              <AskButton label="Ask about earnings" onClick={() => askAbout('earnings quality')} />
            </div>
          </div>

          {/* S08 — Growth Quality */}
          <div ref={sectionRef('s08')} style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Growth Quality
              <StatusBadge status="adequate" />
            </div>
            <SectionHead id="s08" num="" title="Growth Quality" status="adequate"
              subtitle="Growth assessed together with cash generation, margins, and capital allocation — not in isolation." />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
              <Card>
                <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 12 }}>FREE CASH FLOW · ₹ Bn · FY22–FY26</div>
                <ResponsiveContainer width="100%" height={110}>
                  <BarChart data={cashData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <XAxis dataKey="year" tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTip />} />
                    <Bar dataKey="value" fill="var(--c-cashflow)" radius={[3, 3, 0, 0]} name="FCF" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
              <Card>
                <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 10 }}>GROWTH INDICATORS</div>
                {[
                  { l: 'Revenue CAGR (5yr)', v: '7.1%', s: 'adequate' as Status },
                  { l: 'Earnings CAGR (5yr)', v: '7.9%', s: 'adequate' as Status },
                  { l: 'FCF Growth (5yr)', v: 'Strong', s: 'strong' as Status },
                  { l: 'Margin Behaviour', v: 'Stable, slight pressure', s: 'adequate' as Status },
                  { l: 'Growth Sustainability', v: 'Moderate', s: 'adequate' as Status },
                ].map(r => (
                  <div key={r.l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 13, color: 'var(--foreground)' }}>{r.l}</span>
                    <StatusBadge status={r.s} text={r.v} />
                  </div>
                ))}
              </Card>
            </div>
          </div>

          {/* S10 — Margin of Safety */}
          <div ref={sectionRef('s10')} style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Margin of Safety
            </div>
            <SectionHead id="s10" num="" title="Margin of Safety" status="weak"
              subtitle="Business quality and valuation are separate analytical questions. A high-quality business can still carry an unattractive valuation." />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
              <Card style={{ borderTop: '2px solid var(--c-profit)' }}>
                <div style={{ fontSize: 10, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 8 }}>BUSINESS QUALITY</div>
                <div style={{ fontSize: 36, fontWeight: 700, color: 'var(--c-profit)', fontFamily: 'var(--font-heading)', marginBottom: 6 }}>86 / 100</div>
                <StatusBadge status="strong" text="High Quality" />
                <p style={{ fontSize: 12, color: 'var(--muted-foreground)', margin: '10px 0 0', lineHeight: 1.6 }}>The business fundamentals are strong. Financial strength, economic moat, and earnings quality are all high.</p>
              </Card>
              <Card style={{ borderTop: '2px solid var(--c-risk)' }}>
                <div style={{ fontSize: 10, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 8 }}>MARGIN OF SAFETY</div>
                <div style={{ fontSize: 36, fontWeight: 700, color: 'var(--c-risk)', fontFamily: 'var(--font-heading)', marginBottom: 6 }}>−18.8%</div>
                <StatusBadge status="weak" text="Negative" />
                <p style={{ fontSize: 12, color: 'var(--muted-foreground)', margin: '10px 0 0', lineHeight: 1.6 }}>Current market price is 18.8% above the DSP assessed intrinsic value. Investors are paying a premium to intrinsic worth.</p>
              </Card>
            </div>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
              <AskButton label="Ask about the margin of safety" onClick={() => askAbout('margin of safety')} />
            </div>
          </div>

          {/* S12 — Strengths & Weaknesses */}
          <div ref={sectionRef('s12')} style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Strengths & Weaknesses
            </div>
            <SectionHead id="s12" num="" title="Strengths & Weaknesses" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14 }}>
              <Card style={{ borderTop: '2px solid var(--c-profit)' }}>
                <div style={{ fontSize: 10, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 12 }}>KEY STRENGTHS</div>
                {STRENGTHS.map((s, i) => (
                  <div key={i} style={{ display: 'flex', gap: 9, marginBottom: 10, fontSize: 13, color: 'var(--foreground)', lineHeight: 1.55 }}>
                    <span style={{ color: 'var(--c-profit)', flexShrink: 0, marginTop: 1, fontSize: 12 }}>+</span>{s}
                  </div>
                ))}
              </Card>
              <Card style={{ borderTop: '2px solid var(--c-risk)' }}>
                <div style={{ fontSize: 10, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 12 }}>KEY WEAKNESSES</div>
                {WEAKNESSES.map((w, i) => (
                  <div key={i} style={{ display: 'flex', gap: 9, marginBottom: 10, fontSize: 13, color: 'var(--foreground)', lineHeight: 1.55 }}>
                    <span style={{ color: 'var(--c-risk)', flexShrink: 0, marginTop: 1, fontSize: 12 }}>−</span>{w}
                  </div>
                ))}
              </Card>
            </div>
          </div>

          {/* S13 — Investment Context */}
          <div ref={sectionRef('s13')} style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Investment Context
            </div>
            <SectionHead id="s13" num="" title="Investment Context"
              subtitle="Backend-authoritative DSP analytical context. This is not an independent frontend recommendation." />
            <Card>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12, marginBottom: 16 }}>
                {[
                  { l: 'Business Quality', v: '86 / 100', s: 'strong' as Status },
                  { l: 'Valuation', v: 'Premium', s: 'weak' as Status },
                  { l: 'Margin of Safety', v: '−18.8%', s: 'weak' as Status },
                  { l: 'Risk Level', v: 'Moderate', s: 'adequate' as Status },
                  { l: 'Confidence', v: 'High', s: 'strong' as Status },
                ].map(c => (
                  <div key={c.l} style={{ background: 'var(--secondary)', borderRadius: 8, padding: '12px 14px' }}>
                    <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em', marginBottom: 6 }}>{c.l}</div>
                    <div style={{ marginBottom: 6, fontSize: 14, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{c.v}</div>
                    <StatusBadge status={c.s} />
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.7 }}>
                TCS demonstrates high business quality with a strong economic moat, consistent financial performance, and conservative capital structure. The primary concern at current prices is valuation. This is a research finding, not a buy or sell instruction.
              </p>
            </Card>
          </div>

          {/* S14 — Evidence */}
          <div ref={sectionRef('s14')} style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ padding: '2px 8px', background: 'var(--secondary)', borderRadius: 4 }}>DEEP DIVE</span>
              Evidence & Sources
            </div>
            <SectionHead id="s14" num="" title="Evidence & Sources"
              subtitle="Every key conclusion is traceable to analytical evidence." />
            <button onClick={() => setEvidenceOpen(v => !v)}
              style={{ marginBottom: 12, background: 'none', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 16px', fontSize: 13, color: 'var(--muted-foreground)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
              {evidenceOpen ? '▲ Hide evidence trail' : '▼ View evidence trail'}
            </button>
            {evidenceOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {EVIDENCE_ITEMS.map((e, i) => (
                  <Card key={i} style={{ padding: '14px 18px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(130px,1fr))', gap: 12 }}>
                      {[
                        { l: 'METRIC', v: e.metric },
                        { l: 'VALUE', v: e.value },
                        { l: 'PERIOD', v: e.period },
                        { l: 'SOURCE', v: e.source },
                        { l: 'STAGE', v: e.stage },
                        { l: 'CONFIDENCE', v: e.confidence },
                      ].map(f => (
                        <div key={f.l}>
                          <div style={{ fontSize: 9, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.09em', marginBottom: 3 }}>{f.l}</div>
                          <div style={{ fontSize: 12, color: 'var(--foreground)', fontFamily: 'var(--font-data)' }}>{f.v}</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .toc-sidebar { display: none !important; }
          .bq-grid { grid-template-columns: 1fr !important; }
          .company-header-metrics { display: none !important; }
          .company-header-price { font-size: 18px !important; }
        }
        @media (min-width: 769px) {
          .toc-mobile-toggle { display: none !important; }
        }
        @keyframes skel-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
      `}</style>
    </div>
  )
}

// ─── Chat drawer ──────────────────────────────────────────────────────────────

function ChatDrawer({ symbol, open, onClose, initCtx }: {
  symbol: string; open: boolean; onClose: () => void; initCtx: string
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: 'dsp', text: CHAT_RESPONSES.default },
  ])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (initCtx && open) {
      const question = `Tell me about the ${initCtx}.`
      setMessages([{ role: 'dsp', text: CHAT_RESPONSES.default }])
      setTimeout(() => sendMsg(question), 300)
    }
  }, [initCtx, open])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  function sendMsg(text: string) {
    if (!text.trim() || thinking) return
    setMessages(prev => [...prev, { role: 'user', text }])
    setInput('')
    setThinking(true)
    setTimeout(() => {
      setThinking(false)
      const t = text.toLowerCase()
      const key = t.includes('moat') ? 'moat'
        : (t.includes('valuat') || t.includes('intrinsic') || t.includes('price')) ? 'valuation'
        : (t.includes('quality') || t.includes('score') || t.includes('bq')) ? 'quality'
        : (t.includes('risk')) ? 'risk'
        : 'default'
      setMessages(prev => [...prev, { role: 'dsp', text: CHAT_RESPONSES[key] }])
    }, 1400)
  }

  if (!open) return null

  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 100,
      background: 'var(--card)', borderTop: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', height: 280,
      boxShadow: '0 -4px 24px rgba(0,0,0,0.4)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 18px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 22, height: 22, borderRadius: 6, background: 'linear-gradient(135deg,#7c6af7,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#fff', fontWeight: 700 }}>D</div>
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--foreground)', fontFamily: 'var(--font-body)' }}>Ask DSP about this analysis</span>
          <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>· {symbol || 'TCS'}</span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)', fontSize: 16, lineHeight: 1, padding: '4px 8px' }}>×</button>
      </div>

      {/* Suggestion chips */}
      {messages.length <= 1 && (
        <div style={{ padding: '10px 18px 0', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {[
            { label: 'Why is valuation expensive?', ctx: 'valuation and intrinsic value' },
            { label: 'Explain the moat simply', ctx: 'economic moat' },
            { label: 'What is the biggest risk?', ctx: 'key risks' },
            { label: 'How was the quality score derived?', ctx: 'Business Quality score' },
          ].map(c => (
            <button key={c.label}
              onClick={() => sendMsg(`Tell me about the ${c.ctx}.`)}
              style={{
                background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 16,
                padding: '4px 12px', fontSize: 11, color: 'var(--muted-foreground)',
                cursor: 'pointer', fontFamily: 'var(--font-body)',
              }}>
              {c.label}
            </button>
          ))}
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto', padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {m.role === 'dsp' && (
              <div style={{ width: 24, height: 24, borderRadius: 6, background: 'linear-gradient(135deg,#7c6af7,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: '#fff', fontWeight: 700, flexShrink: 0, marginTop: 2 }}>D</div>
            )}
            <div style={{ maxWidth: '76%', background: m.role === 'user' ? 'var(--secondary)' : 'var(--muted)', border: '1px solid var(--border)', borderRadius: m.role === 'user' ? '12px 12px 3px 12px' : '3px 12px 12px 12px', padding: '8px 14px', fontSize: 13, color: 'var(--foreground)', lineHeight: 1.6 }}>
              {m.text}
            </div>
          </div>
        ))}
        {thinking && (
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ width: 24, height: 24, borderRadius: 6, background: 'linear-gradient(135deg,#7c6af7,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: '#fff', fontWeight: 700, flexShrink: 0 }}>D</div>
            <div style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: '3px 12px 12px 12px', padding: '10px 14px', fontSize: 12, color: 'var(--muted-foreground)' }}>
              Reviewing the analysis…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ padding: '8px 14px 12px', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 8, background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10, padding: '8px 12px' }}
          onFocusCapture={e => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)')}
          onBlurCapture={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') sendMsg(input) }}
            placeholder="Ask about this analysis…"
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-body)' }} />
          <button onClick={() => sendMsg(input)}
            style={{ width: 28, height: 28, borderRadius: '50%', background: input.trim() ? 'var(--c-dsp)' : 'var(--muted)', border: 'none', cursor: input.trim() ? 'pointer' : 'default', color: input.trim() ? '#fff' : 'var(--muted-foreground)', fontSize: 13 }}>
            ↑
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function CompanyAnalysis() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const symbol = (searchParams.get('symbol') || '').toUpperCase()

  // Record every symbol load — both global trending and per-user history
  useEffect(() => {
    if (symbol) recordSearch(symbol, user?.email)
  }, [symbol, user?.email])

  const [phase, setPhase] = useState<Phase>('select')
  const [loadStep, setLoadStep] = useState(0)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatCtx, setChatCtx] = useState('')

  const advanceStep = useCallback(() => {
    setLoadStep(s => s + 1)
  }, [])

  useEffect(() => {
    if (phase !== 'buffett-loading') return
    if (loadStep >= LOADING_STEPS.length) { setPhase('buffett-result'); return }
    const t = setTimeout(advanceStep, loadStep === 0 ? 400 : loadStep < 3 ? 700 : 900)
    return () => clearTimeout(t)
  }, [phase, loadStep, advanceStep])

  useEffect(() => {
    if (phase !== 'simple-loading') return
    const t = setTimeout(() => setPhase('simple-result'), 1200)
    return () => clearTimeout(t)
  }, [phase])

  function startBuffett() {
    setLoadStep(0)
    setPhase('buffett-loading')
  }
  function startSimple() {
    setPhase('simple-loading')
  }

  if (!symbol && phase === 'select') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <div style={{ padding: '14px 28px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => navigate('/')}
            style={{ background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer', fontSize: 13, fontFamily: 'var(--font-body)', padding: '4px 0' }}>
            ← Search
          </button>
          <span style={{ color: 'var(--border)' }}>|</span>
          <span style={{ fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)' }}>No company selected</span>
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', flexDirection: 'column', gap: 16 }}>
          <p style={{ fontSize: 15, color: 'var(--muted-foreground)', textAlign: 'center' }}>Search for a company on the home page to begin.</p>
          <button onClick={() => navigate('/')}
            style={{ padding: '9px 20px', background: 'var(--c-dsp)', border: 'none', borderRadius: 8, fontSize: 13, color: '#fff', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
            Go to search
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top bar — only shown in non-buffett phases */}
      {phase !== 'buffett-result' && (
        <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <button onClick={() => { setPhase('select'); setChatOpen(false) }}
            style={{ background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer', fontSize: 13, fontFamily: 'var(--font-body)' }}>
            ←
          </button>
          <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--foreground)', fontFamily: 'var(--font-body)' }}>{symbol || 'Company Analysis'}</span>
          {phase === 'simple-result' && (
            <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>Simple Research</span>
          )}
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
        {phase === 'select' && (
          <SelectionScreen symbol={symbol} onSimple={startSimple} onBuffett={startBuffett} />
        )}
        {phase === 'simple-loading' && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginBottom: 14 }}>
                {[0,1,2].map(d => (
                  <span key={d} style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--c-revenue)', display: 'inline-block', animation: `pulse 1.2s ${d * 0.2}s ease-in-out infinite` }} />
                ))}
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)' }}>Gathering research data…</div>
              <style>{`@keyframes pulse { 0%,100%{opacity:0.3;transform:scale(0.8)} 50%{opacity:1;transform:scale(1)} }`}</style>
            </div>
          </div>
        )}
        {phase === 'simple-result' && (
          <SimpleResult symbol={symbol} onUpgrade={startBuffett} />
        )}
        {phase === 'buffett-loading' && (
          <div style={{ position: 'relative', flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Skeleton visible underneath */}
            <div style={{ position: 'absolute', inset: 0, opacity: 0.35, pointerEvents: 'none' }}>
              <SkeletonReport />
            </div>
            {/* Loader overlay */}
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(8,11,18,0.7)', backdropFilter: 'blur(6px)', zIndex: 10 }}>
              <StagedLoader
                steps={LOADING_STEPS}
                active={loadStep}
                onDone={() => setPhase('buffett-result')}
              />
            </div>
          </div>
        )}
        {phase === 'buffett-result' && (
          <>
            <BuffettReport
              symbol={symbol}
              chatOpen={chatOpen}
              onChatOpen={() => setChatOpen(true)}
              chatCtx={chatCtx}
              onChatCtx={setChatCtx}
            />
            <ChatDrawer
              symbol={symbol}
              open={chatOpen}
              onClose={() => setChatOpen(false)}
              initCtx={chatCtx}
            />
          </>
        )}
      </div>
    </div>
  )
}
