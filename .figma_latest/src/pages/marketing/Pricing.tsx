import { useState } from 'react'
import { Link } from 'react-router-dom'

const PLANS = [
  {
    name: 'Free',
    monthly: 0,
    annual: 0,
    period: 'forever',
    desc: 'For casual investors getting started.',
    features: ['10 research sessions/month', 'Company Analysis (basic)', 'DSP Rating access', 'Company Directory'],
    cta: 'Get started free',
    href: '/signup',
  },
  {
    name: 'Pro',
    monthly: 999,
    annual: 799,
    period: '/month',
    desc: 'For serious individual investors.',
    features: ['Unlimited research sessions', 'Full Company Analysis', 'Portfolio tracking', 'Security Compare', 'AI Copilot access', 'Research Canvas', 'Priority support'],
    cta: 'Start Pro trial',
    href: '/signup',
  },
  {
    name: 'Institutional',
    monthly: null,
    annual: null,
    period: 'contact us',
    desc: 'For advisors, funds, and teams.',
    features: ['Everything in Pro', 'Multi-user seats', 'Advisor dashboard', 'Bulk research API', 'Institutional screener', 'Dedicated support', 'Custom integrations'],
    cta: 'Contact sales',
    href: '/contact',
  },
]

export default function Pricing() {
  const [billing, setBilling] = useState<'monthly' | 'annual'>('monthly')
  const [selected, setSelected] = useState<string>('Pro')
  const [hovered, setHovered] = useState<string | null>(null)

  function getPrice(plan: typeof PLANS[0]) {
    if (plan.monthly === null) return 'Custom'
    if (plan.monthly === 0) return '₹0'
    const amount = billing === 'annual' ? plan.annual! : plan.monthly
    return `₹${amount.toLocaleString('en-IN')}`
  }

  function getPeriod(plan: typeof PLANS[0]) {
    if (plan.monthly === null || plan.monthly === 0) return plan.period
    return billing === 'annual' ? '/month, billed annually' : '/month'
  }

  function cardBorder(plan: typeof PLANS[0]) {
    if (selected === plan.name) return '2px solid #7c6af7'
    if (hovered === plan.name) return '2px solid rgba(124,106,247,0.45)'
    return '2px solid var(--border)'
  }

  function cardBackground(plan: typeof PLANS[0]) {
    if (selected === plan.name)
      return 'linear-gradient(160deg, rgba(124,106,247,0.13) 0%, rgba(45,212,191,0.07) 100%)'
    if (hovered === plan.name)
      return 'linear-gradient(160deg, rgba(124,106,247,0.06) 0%, rgba(45,212,191,0.03) 100%)'
    return 'var(--card)'
  }

  return (
    <div>
      <section style={{ padding: '80px 48px 48px', textAlign: 'center' }}>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(32px, 5vw, 52px)', color: 'var(--foreground)', fontWeight: 500, margin: '0 0 16px', letterSpacing: '-0.02em' }}>
          Simple, transparent pricing.
        </h1>
        <p style={{ fontSize: 16, color: 'var(--muted-foreground)', maxWidth: 480, margin: '0 auto 36px' }}>
          Start for free. Upgrade when you need more depth.
        </p>

        {/* Billing toggle */}
        <div style={{ display: 'inline-flex', alignItems: 'center', background: 'var(--muted)', borderRadius: 12, padding: 4, gap: 2 }}>
          {(['monthly', 'annual'] as const).map(opt => (
            <button
              key={opt}
              onClick={() => setBilling(opt)}
              style={{
                padding: '7px 20px', borderRadius: 9, border: 'none', cursor: 'pointer',
                fontSize: 13, fontFamily: 'var(--font-body)', fontWeight: 500,
                background: billing === opt ? 'var(--card)' : 'transparent',
                color: billing === opt ? 'var(--foreground)' : 'var(--muted-foreground)',
                boxShadow: billing === opt ? '0 1px 4px rgba(0,0,0,0.18)' : 'none',
                transition: 'all 0.18s',
                display: 'flex', alignItems: 'center', gap: 6,
              }}
            >
              {opt === 'monthly' ? 'Monthly' : 'Annual'}
              {opt === 'annual' && (
                <span style={{
                  fontSize: 10, fontFamily: 'var(--font-data)', fontWeight: 700,
                  background: 'var(--c-profit)', color: '#fff',
                  borderRadius: 99, padding: '2px 7px', letterSpacing: '0.03em',
                }}>
                  –20%
                </span>
              )}
            </button>
          ))}
        </div>
      </section>

      <section style={{ padding: '0 48px 80px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20, maxWidth: 960, margin: '0 auto' }}>
          {PLANS.map(plan => {
            const isSelected = selected === plan.name
            const isHovered = hovered === plan.name

            return (
              <div
                key={plan.name}
                onClick={() => setSelected(plan.name)}
                onMouseEnter={() => setHovered(plan.name)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  background: cardBackground(plan),
                  border: cardBorder(plan),
                  borderRadius: 16, padding: '28px 28px',
                  position: 'relative', cursor: 'pointer',
                  transition: 'border-color 0.22s, background 0.22s, box-shadow 0.22s',
                  boxShadow: isSelected
                    ? '0 0 0 4px rgba(124,106,247,0.12)'
                    : isHovered
                    ? '0 0 0 2px rgba(124,106,247,0.07)'
                    : 'none',
                  outline: 'none',
                }}
                role="radio"
                aria-checked={isSelected}
                tabIndex={0}
                onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && setSelected(plan.name)}
              >
                {/* Selected badge */}
                {isSelected && (
                  <div style={{
                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                    background: 'var(--c-dsp)', color: '#fff', fontSize: 11,
                    fontFamily: 'var(--font-data)', borderRadius: 99, padding: '4px 14px',
                    letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap',
                    transition: 'opacity 0.2s',
                  }}>
                    {plan.name === 'Pro' ? 'Most popular' : 'Selected'}
                  </div>
                )}
                {/* Non-selected Pro badge */}
                {!isSelected && plan.name === 'Pro' && (
                  <div style={{
                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                    background: 'var(--muted)', color: 'var(--muted-foreground)', fontSize: 11,
                    fontFamily: 'var(--font-data)', borderRadius: 99, padding: '4px 14px',
                    letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap',
                    border: '1px solid var(--border)',
                  }}>
                    Most popular
                  </div>
                )}

                <div style={{ fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
                  {plan.name}
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginBottom: 4 }}>
                  <span style={{ fontSize: 36, fontFamily: 'var(--font-heading)', color: 'var(--foreground)', fontWeight: 500, lineHeight: 1 }}>
                    {getPrice(plan)}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginBottom: 8 }}>
                  {getPeriod(plan)}
                </div>
                {billing === 'annual' && plan.monthly && plan.monthly > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', marginBottom: 8 }}>
                    Save ₹{((plan.monthly - plan.annual!) * 12).toLocaleString('en-IN')}/year
                  </div>
                )}
                <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: '0 0 20px', lineHeight: 1.5 }}>
                  {plan.desc}
                </p>
                <Link
                  to={plan.href}
                  onClick={e => e.stopPropagation()}
                  style={{
                    display: 'block', textAlign: 'center', padding: '11px 20px',
                    background: isSelected ? 'var(--c-dsp)' : 'var(--muted)',
                    color: isSelected ? '#fff' : 'var(--foreground)',
                    border: isSelected ? 'none' : '1px solid var(--border)',
                    borderRadius: 10, fontSize: 14, textDecoration: 'none',
                    fontFamily: 'var(--font-body)', marginBottom: 24,
                    transition: 'background 0.22s, color 0.22s',
                  }}
                >
                  {plan.cta}
                </Link>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {plan.features.map(f => (
                    <div key={f} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                      <span style={{ color: isSelected ? 'var(--c-dsp)' : 'var(--c-profit)', fontSize: 14, flexShrink: 0, marginTop: 1, transition: 'color 0.22s' }}>✓</span>
                      <span style={{ fontSize: 13, color: 'var(--muted-foreground)', lineHeight: 1.4 }}>{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
