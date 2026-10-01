import { useState } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type Category = 'all' | 'research' | 'premium' | 'analysis' | 'referral'

interface Coupon {
  id: string
  code: string
  title: string
  description: string
  discount: string
  discountType: 'percent' | 'flat' | 'free'
  category: Exclude<Category, 'all'>
  expiry: string
  daysLeft: number
  minSpend?: string
  applicableTo: string[]
  featured?: boolean
  claimed?: boolean
  newBadge?: boolean
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const COUPONS: Coupon[] = [
  {
    id: 'c1',
    code: 'DSP50',
    title: '50% off Premium Plan',
    description: 'Unlock the complete DSP Buffett Indicator suite at half price for your first 3 months.',
    discount: '50%',
    discountType: 'percent',
    category: 'premium',
    expiry: '31 Oct 2026',
    daysLeft: 39,
    applicableTo: ['Premium Monthly', 'Premium Annual'],
    featured: true,
    newBadge: true,
  },
  {
    id: 'c2',
    code: 'RESEARCH30',
    title: '30% off Research Hub',
    description: 'Access institutional-grade research reports and sector intelligence at a discount.',
    discount: '30%',
    discountType: 'percent',
    category: 'research',
    expiry: '15 Nov 2026',
    daysLeft: 54,
    applicableTo: ['Research Hub', 'Institutional Research'],
  },
  {
    id: 'c3',
    code: 'BUFFETT500',
    title: '₹500 flat off on Annual',
    description: 'Save ₹500 on any annual subscription — our best value plan.',
    discount: '₹500',
    discountType: 'flat',
    category: 'premium',
    expiry: '31 Dec 2026',
    daysLeft: 100,
    minSpend: '₹1,999',
    applicableTo: ['Premium Annual', 'Research Annual'],
  },
  {
    id: 'c4',
    code: 'FREEMONTH',
    title: '1 Free Month Added',
    description: 'Renew your plan this month and get an extra month added to your subscription at no charge.',
    discount: 'Free month',
    discountType: 'free',
    category: 'premium',
    expiry: '30 Sep 2026',
    daysLeft: 8,
    applicableTo: ['All plans'],
    newBadge: true,
  },
  {
    id: 'c5',
    code: 'REFER20',
    title: '20% off for You + Friend',
    description: 'Refer a friend and both of you get 20% off your next billing cycle when they sign up.',
    discount: '20%',
    discountType: 'percent',
    category: 'referral',
    expiry: 'Ongoing',
    daysLeft: 999,
    applicableTo: ['All plans'],
  },
  {
    id: 'c6',
    code: 'ANALYSIS15',
    title: '15% off DSP Buffett Analysis',
    description: 'Run the full DSP Buffett Indicator Analysis on any company at a 15% discount.',
    discount: '15%',
    discountType: 'percent',
    category: 'analysis',
    expiry: '20 Oct 2026',
    daysLeft: 28,
    applicableTo: ['DSP Buffett Analysis', 'Single Reports'],
    claimed: true,
  },
  {
    id: 'c7',
    code: 'EARLY2027',
    title: 'Early Bird — 40% off 2027 Annual',
    description: 'Lock in the early bird rate for your 2027 annual subscription before prices increase.',
    discount: '40%',
    discountType: 'percent',
    category: 'premium',
    expiry: '31 Jan 2027',
    daysLeft: 131,
    applicableTo: ['Premium Annual 2027'],
    newBadge: true,
  },
  {
    id: 'c8',
    code: 'ADVISOR25',
    title: '25% off AI Advisor',
    description: 'Access the AI Advisor and portfolio intelligence features at a special rate this quarter.',
    discount: '25%',
    discountType: 'percent',
    category: 'analysis',
    expiry: '31 Oct 2026',
    daysLeft: 39,
    applicableTo: ['AI Advisor', 'Portfolio Intelligence'],
  },
]

const FILTERS: { label: string; value: Category }[] = [
  { label: 'All Offers', value: 'all' },
  { label: 'Premium Plans', value: 'premium' },
  { label: 'Research', value: 'research' },
  { label: 'Analysis', value: 'analysis' },
  { label: 'Referral', value: 'referral' },
]

const CATEGORY_COLORS: Record<Exclude<Category, 'all'>, string> = {
  premium:  'var(--c-dsp)',
  research: 'var(--c-revenue)',
  analysis: 'var(--c-cashflow)',
  referral: 'var(--c-profit)',
}

const CATEGORY_LABELS: Record<Exclude<Category, 'all'>, string> = {
  premium:  'Premium',
  research: 'Research',
  analysis: 'Analysis',
  referral: 'Referral',
}

// ─── Coupon card ──────────────────────────────────────────────────────────────

function CouponCard({ coupon }: { coupon: Coupon }) {
  const [copied, setCopied] = useState(false)

  function copyCode() {
    navigator.clipboard.writeText(coupon.code).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const color = CATEGORY_COLORS[coupon.category]
  const expiringSoon = coupon.daysLeft <= 10 && coupon.daysLeft < 999
  const ongoing = coupon.daysLeft === 999

  return (
    <div style={{
      background: 'var(--card)',
      border: `1px solid ${coupon.featured ? `${color}44` : 'var(--border)'}`,
      borderRadius: 14,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      transition: 'box-shadow 0.2s, border-color 0.2s',
      opacity: coupon.claimed ? 0.6 : 1,
      position: 'relative',
    }}
      onMouseEnter={e => {
        if (!coupon.claimed) {
          e.currentTarget.style.boxShadow = `0 8px 32px rgba(0,0,0,0.3)`
          e.currentTarget.style.borderColor = `${color}66`
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = coupon.featured ? `${color}44` : 'var(--border)'
      }}
    >
      {/* Top accent bar */}
      <div style={{ height: 3, background: coupon.claimed ? 'var(--border)' : `linear-gradient(90deg, ${color}, ${color}88)` }} />

      {/* Header */}
      <div style={{ padding: '18px 20px 14px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 10, padding: '2px 8px',
              background: `${color}18`, border: `1px solid ${color}33`,
              borderRadius: 99, color, fontFamily: 'var(--font-data)', letterSpacing: '0.06em',
            }}>
              {CATEGORY_LABELS[coupon.category].toUpperCase()}
            </span>
            {coupon.newBadge && !coupon.claimed && (
              <span style={{ fontSize: 10, padding: '2px 8px', background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.25)', borderRadius: 99, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em' }}>
                NEW
              </span>
            )}
            {expiringSoon && !coupon.claimed && (
              <span style={{ fontSize: 10, padding: '2px 8px', background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.25)', borderRadius: 99, color: 'var(--c-risk)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em' }}>
                EXPIRING SOON
              </span>
            )}
            {coupon.claimed && (
              <span style={{ fontSize: 10, padding: '2px 8px', background: 'rgba(107,122,153,0.12)', border: '1px solid rgba(107,122,153,0.2)', borderRadius: 99, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.06em' }}>
                CLAIMED
              </span>
            )}
          </div>
          {/* Discount badge */}
          <div style={{
            fontFamily: 'var(--font-heading)', fontSize: 22, fontWeight: 600,
            color: coupon.claimed ? 'var(--muted-foreground)' : color,
            letterSpacing: '-0.02em', flexShrink: 0,
          }}>
            {coupon.discount}
          </div>
        </div>

        <div style={{ fontFamily: 'var(--font-heading)', fontSize: 16, fontWeight: 500, color: 'var(--foreground)', marginBottom: 6, lineHeight: 1.3 }}>
          {coupon.title}
        </div>
        <p style={{ fontSize: 12, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.6 }}>
          {coupon.description}
        </p>
      </div>

      {/* Applies to */}
      <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {coupon.applicableTo.map(a => (
          <span key={a} style={{ fontSize: 10, color: 'var(--muted-foreground)', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 6, padding: '2px 8px', fontFamily: 'var(--font-data)' }}>
            {a}
          </span>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginTop: 'auto' }}>
        {/* Expiry */}
        <div>
          <div style={{ fontSize: 9, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.08em', marginBottom: 3 }}>
            {ongoing ? 'VALID' : 'EXPIRES'}
          </div>
          <div style={{ fontSize: 12, color: expiringSoon ? 'var(--c-risk)' : 'var(--muted-foreground)', fontFamily: 'var(--font-data)', fontWeight: 500 }}>
            {ongoing ? 'Ongoing' : coupon.expiry}
          </div>
          {!ongoing && (
            <div style={{ fontSize: 10, color: expiringSoon ? 'var(--c-risk)' : 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>
              {coupon.daysLeft} days left
            </div>
          )}
        </div>

        {/* Code + copy */}
        {!coupon.claimed ? (
          <button
            onClick={copyCode}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: copied ? 'rgba(52,211,153,0.12)' : 'var(--secondary)',
              border: `1px solid ${copied ? 'rgba(52,211,153,0.35)' : 'var(--border)'}`,
              borderRadius: 8, padding: '8px 14px', cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            <span style={{ fontFamily: 'var(--font-data)', fontSize: 13, fontWeight: 600, color: copied ? 'var(--c-profit)' : 'var(--foreground)', letterSpacing: '0.08em' }}>
              {coupon.code}
            </span>
            {copied ? (
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M2 7l3 3 6-6" stroke="var(--c-profit)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <rect x="1" y="4" width="8" height="8" rx="1.5" stroke="var(--muted-foreground)" strokeWidth="1.2"/>
                <path d="M4 4V2.5A1.5 1.5 0 015.5 1H10.5A1.5 1.5 0 0112 2.5v5A1.5 1.5 0 0110.5 9H9" stroke="var(--muted-foreground)" strokeWidth="1.2"/>
              </svg>
            )}
          </button>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', padding: '8px 14px', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 8 }}>
            {coupon.code}
          </div>
        )}
      </div>

      {coupon.minSpend && (
        <div style={{ padding: '0 20px 12px' }}>
          <span style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>Min. spend {coupon.minSpend}</span>
        </div>
      )}
    </div>
  )
}

// ─── Stats bar ────────────────────────────────────────────────────────────────

function StatsBar() {
  const active = COUPONS.filter(c => !c.claimed).length
  const expiringSoon = COUPONS.filter(c => c.daysLeft <= 10 && c.daysLeft < 999 && !c.claimed).length
  const claimed = COUPONS.filter(c => c.claimed).length
  const maxSaving = '50%'

  return (
    <div style={{ display: 'flex', gap: 0, flexWrap: 'wrap', marginBottom: 28 }}>
      {[
        { l: 'Active Offers', v: String(active), color: 'var(--c-dsp)' },
        { l: 'Expiring Soon', v: String(expiringSoon), color: 'var(--c-risk)' },
        { l: 'Claimed', v: String(claimed), color: 'var(--muted-foreground)' },
        { l: 'Best Discount', v: maxSaving, color: 'var(--c-profit)' },
      ].map((s, i) => (
        <div key={s.l} style={{
          flex: 1, minWidth: 110,
          padding: '18px 22px',
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderLeft: i > 0 ? 'none' : '1px solid var(--border)',
          borderRadius: i === 0 ? '12px 0 0 12px' : i === 3 ? '0 12px 12px 0' : 0,
          textAlign: 'center',
        }}>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 28, fontWeight: 600, color: s.color, lineHeight: 1, marginBottom: 6 }}>{s.v}</div>
          <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em' }}>{s.l.toUpperCase()}</div>
        </div>
      ))}
    </div>
  )
}

// ─── Featured banner ──────────────────────────────────────────────────────────

function FeaturedBanner({ coupon, onCopy }: { coupon: Coupon; onCopy: () => void }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(coupon.code).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopy()
  }

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid rgba(124,106,247,0.35)',
      borderRadius: 16,
      overflow: 'hidden',
      marginBottom: 28,
      position: 'relative',
    }}>
      {/* Gradient backdrop */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse 60% 80% at 100% 50%, rgba(124,106,247,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ padding: '28px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap', position: 'relative' }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em' }}>FEATURED OFFER</span>
            {coupon.newBadge && (
              <span style={{ fontSize: 10, padding: '2px 8px', background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.25)', borderRadius: 99, color: 'var(--c-profit)', fontFamily: 'var(--font-data)' }}>NEW</span>
            )}
          </div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(20px,3vw,28px)', fontWeight: 500, color: 'var(--foreground)', margin: '0 0 8px', letterSpacing: '-0.02em' }}>
            {coupon.title}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: '0 0 16px', lineHeight: 1.65, maxWidth: 440 }}>
            {coupon.description}
          </p>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
            {coupon.applicableTo.map(a => (
              <span key={a} style={{ fontSize: 11, color: 'var(--muted-foreground)', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 6, padding: '3px 10px', fontFamily: 'var(--font-data)' }}>{a}</span>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={copy}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                background: copied ? 'rgba(52,211,153,0.15)' : 'var(--c-dsp)',
                border: `1px solid ${copied ? 'rgba(52,211,153,0.4)' : 'var(--c-dsp)'}`,
                borderRadius: 10, padding: '10px 20px', cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <span style={{ fontFamily: 'var(--font-data)', fontSize: 15, fontWeight: 700, color: copied ? 'var(--c-profit)' : '#fff', letterSpacing: '0.1em' }}>
                {coupon.code}
              </span>
              <span style={{ fontSize: 12, color: copied ? 'var(--c-profit)' : 'rgba(255,255,255,0.8)', fontFamily: 'var(--font-body)' }}>
                {copied ? '✓ Copied' : 'Copy code'}
              </span>
            </button>
            <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>
              Expires {coupon.expiry} · {coupon.daysLeft} days left
            </span>
          </div>
        </div>

        {/* Discount display */}
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(52px,8vw,80px)', fontWeight: 600, color: 'var(--c-dsp)', lineHeight: 1, letterSpacing: '-0.03em' }}>
            {coupon.discount}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginTop: 4 }}>OFF YOUR PLAN</div>
        </div>
      </div>
    </div>
  )
}

// ─── Referral section ─────────────────────────────────────────────────────────

function ReferralSection() {
  const [copied, setCopied] = useState(false)
  const refLink = 'dsp.ai/refer/user-4821'

  function copy() {
    navigator.clipboard.writeText(refLink).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2200)
  }

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid rgba(52,211,153,0.25)',
      borderRadius: 14,
      padding: '24px 28px',
      marginBottom: 28,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap',
    }}>
      <div style={{ flex: 1, minWidth: 220 }}>
        <div style={{ fontSize: 10, color: 'var(--c-profit)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 8 }}>REFERRAL PROGRAMME</div>
        <div style={{ fontFamily: 'var(--font-heading)', fontSize: 18, fontWeight: 500, color: 'var(--foreground)', marginBottom: 6 }}>
          Give 20% off · Get 20% off
        </div>
        <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.6 }}>
          Share your link. When your friend signs up, both of you receive 20% off your next billing cycle automatically.
        </p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 0,
          background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden',
        }}>
          <span style={{ padding: '9px 14px', fontFamily: 'var(--font-data)', fontSize: 12, color: 'var(--muted-foreground)' }}>
            {refLink}
          </span>
          <button
            onClick={copy}
            style={{
              background: copied ? 'var(--c-profit)' : 'var(--c-dsp)',
              border: 'none', padding: '9px 16px', cursor: 'pointer',
              fontSize: 12, color: '#fff', fontFamily: 'var(--font-body)',
              transition: 'background 0.15s',
            }}
          >
            {copied ? '✓ Copied' : 'Copy link'}
          </button>
        </div>
        <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>2 friends referred · ₹400 saved so far</span>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Coupons() {
  const [activeFilter, setActiveFilter] = useState<Category>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const featured = COUPONS.find(c => c.featured)

  const filtered = COUPONS.filter(c => {
    if (c.featured) return false
    const matchesCategory = activeFilter === 'all' || c.category === activeFilter
    const matchesSearch = !searchQuery || c.title.toLowerCase().includes(searchQuery.toLowerCase()) || c.code.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  return (
    <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '28px 32px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.1em', marginBottom: 6 }}>EXCLUSIVE OFFERS</div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(22px,3vw,32px)', fontWeight: 500, color: 'var(--foreground)', margin: 0, letterSpacing: '-0.02em' }}>
              Coupons & Client Offers
            </h1>
            <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: '4px 0 0', lineHeight: 1.5 }}>
              Active discounts and promotions on your DSP subscriptions and services.
            </p>
          </div>
          {/* Search */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 9, padding: '8px 14px', minWidth: 220 }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="6" cy="6" r="4" stroke="var(--muted-foreground)" strokeWidth="1.3"/>
              <line x1="9.5" y1="9.5" x2="12.5" y2="12.5" stroke="var(--muted-foreground)" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search offers or codes…"
              style={{ background: 'none', border: 'none', outline: 'none', fontSize: 13, color: 'var(--foreground)', fontFamily: 'var(--font-body)', flex: 1, minWidth: 0 }}
            />
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <StatsBar />

      {/* Featured offer */}
      {featured && <FeaturedBanner coupon={featured} onCopy={() => {}} />}

      {/* Referral section */}
      <ReferralSection />

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setActiveFilter(f.value)}
            style={{
              padding: '7px 16px',
              background: activeFilter === f.value ? 'var(--c-dsp)' : 'var(--secondary)',
              border: `1px solid ${activeFilter === f.value ? 'var(--c-dsp)' : 'var(--border)'}`,
              borderRadius: 99,
              fontSize: 12, fontFamily: 'var(--font-body)',
              color: activeFilter === f.value ? '#fff' : 'var(--muted-foreground)',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
            onMouseEnter={e => { if (activeFilter !== f.value) { e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)'; e.currentTarget.style.color = 'var(--foreground)' } }}
            onMouseLeave={e => { if (activeFilter !== f.value) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--muted-foreground)' } }}
          >
            {f.label}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', alignSelf: 'center' }}>
          {filtered.length} offer{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Coupon grid */}
      {filtered.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(290px,1fr))', gap: 16 }}>
          {filtered.map(c => <CouponCard key={c.id} coupon={c} />)}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: 32, marginBottom: 12, opacity: 0.3 }}>◈</div>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 18, color: 'var(--foreground)', marginBottom: 6 }}>No offers found</div>
          <p style={{ fontSize: 13, color: 'var(--muted-foreground)' }}>Try a different filter or check back soon for new promotions.</p>
        </div>
      )}

      {/* Footer notice */}
      <div style={{ marginTop: 36, padding: '16px 20px', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 10 }}>
        <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 4 }}>TERMS & CONDITIONS</div>
        <p style={{ fontSize: 12, color: 'var(--muted-foreground)', margin: 0, lineHeight: 1.7 }}>
          Coupons are valid for the period shown and cannot be combined unless stated. Each coupon may only be applied once per account per billing cycle. DSP reserves the right to withdraw any offer without prior notice. Discounts apply to listed plans only.
        </p>
      </div>

    </div>
  )
}
