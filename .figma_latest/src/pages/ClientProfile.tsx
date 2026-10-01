import { useState } from 'react'

// ── Semicircular gauge ──────────────────────────────────────────────────────
function HealthGauge({ score }: { score: number }) {
  const max = 1000
  const pct = Math.min(score / max, 1)
  // Arc goes from 180° (left) to 0° (right) — total 180°
  const angle = 180 - pct * 180 // degrees from left; 0 = leftmost, 180 = rightmost
  const toRad = (d: number) => (d * Math.PI) / 180
  const cx = 160, cy = 130, r = 110

  // Build the 5 coloured arc segments
  const zones = [
    { start: 180, end: 144, color: '#ef4444' },   // 0–199 Very Poor
    { start: 144, end: 108, color: '#f97316' },   // 200–399 Poor
    { start: 108, end: 72,  color: '#f59e0b' },   // 400–599 Fair
    { start: 72,  end: 36,  color: '#22c55e' },   // 600–749 Good
    { start: 36,  end: 0,   color: '#10b981' },   // 750–1000 Excellent
  ]

  function arcPath(startDeg: number, endDeg: number, ri = 80, ro = 110) {
    const s = toRad(startDeg), e = toRad(endDeg)
    const x1o = cx + ro * Math.cos(s), y1o = cy - ro * Math.sin(s)
    const x2o = cx + ro * Math.cos(e), y2o = cy - ro * Math.sin(e)
    const x1i = cx + ri * Math.cos(s), y1i = cy - ri * Math.sin(s)
    const x2i = cx + ri * Math.cos(e), y2i = cy - ri * Math.sin(e)
    const large = Math.abs(startDeg - endDeg) > 180 ? 1 : 0
    return `M${x1o},${y1o} A${ro},${ro} 0 ${large},0 ${x2o},${y2o} L${x2i},${y2i} A${ri},${ri} 0 ${large},1 ${x1i},${y1i} Z`
  }

  // Needle
  const needleDeg = angle // angle from left horizontal
  const needleRad = toRad(needleDeg)
  const nx = cx + (r - 10) * Math.cos(needleRad)
  const ny = cy - (r - 10) * Math.sin(needleRad)

  const label = score >= 750 ? 'EXCELLENT' : score >= 600 ? 'GOOD' : score >= 400 ? 'FAIR' : score >= 200 ? 'POOR' : 'VERY POOR'
  const labelColor = score >= 750 ? '#10b981' : score >= 600 ? '#22c55e' : score >= 400 ? '#f59e0b' : '#f97316'

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width="320" height="170" viewBox="0 0 320 170" style={{ overflow: 'visible' }}>
        {/* Track background */}
        <path d={arcPath(180, 0, 80, 112)} fill="var(--secondary)" />
        {/* Colour zones */}
        {zones.map((z, i) => (
          <path key={i} d={arcPath(z.start, z.end, 82, 110)} fill={z.color} opacity={0.85} />
        ))}
        {/* Gap lines between zones */}
        {[144, 108, 72, 36].map(deg => {
          const rad = toRad(deg)
          return (
            <line
              key={deg}
              x1={cx + 80 * Math.cos(rad)} y1={cy - 80 * Math.sin(rad)}
              x2={cx + 112 * Math.cos(rad)} y2={cy - 112 * Math.sin(rad)}
              stroke="var(--card)" strokeWidth="3"
            />
          )
        })}
        {/* Centre circle */}
        <circle cx={cx} cy={cy} r={18} fill="var(--card)" stroke="var(--border)" strokeWidth="1.5" />
        {/* Needle */}
        <line
          x1={cx} y1={cy}
          x2={nx} y2={ny}
          stroke="var(--foreground)" strokeWidth="2.5" strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={5} fill="var(--foreground)" />
        {/* Zone labels */}
        {[
          { deg: 162, label: 'Very Poor' },
          { deg: 126, label: 'Poor' },
          { deg: 90,  label: 'Fair' },
          { deg: 54,  label: 'Good' },
          { deg: 18,  label: 'Excellent' },
        ].map(({ deg, label: zl }) => {
          const r2 = toRad(deg)
          return (
            <text key={deg}
              x={cx + 125 * Math.cos(r2)}
              y={cy - 125 * Math.sin(r2) + 4}
              textAnchor="middle" fontSize="8" fill="var(--muted-foreground)"
              fontFamily="var(--font-data)"
            >{zl}</text>
          )
        })}
        {/* Min/max labels */}
        <text x={cx - 118} y={cy + 18} fontSize="9" fill="var(--muted-foreground)" fontFamily="var(--font-data)">0</text>
        <text x={cx + 106} y={cy + 18} fontSize="9" fill="var(--muted-foreground)" fontFamily="var(--font-data)">1000</text>
      </svg>
      <div style={{ marginTop: -8 }}>
        <div style={{ fontSize: 52, fontWeight: 700, color: 'var(--foreground)', fontFamily: 'var(--font-heading)', lineHeight: 1 }}>
          {score}
        </div>
        <div style={{ fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', marginTop: 2 }}>/ 1000</div>
        <div style={{ fontSize: 18, fontWeight: 600, color: labelColor, fontFamily: 'var(--font-body)', marginTop: 6, letterSpacing: '0.08em' }}>
          {label}
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)', marginTop: 4 }}>
          Your financial health is currently good.
        </div>
      </div>
    </div>
  )
}

// ── Score breakdown row ──────────────────────────────────────────────────────
function ScoreRow({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = (value / max) * 100
  const color = pct >= 75 ? '#22c55e' : pct >= 55 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ flex: 1, fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)' }}>{label}</div>
      <div style={{ width: 120, height: 5, background: 'var(--secondary)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99 }} />
      </div>
      <div style={{ fontSize: 12, fontFamily: 'var(--font-data)', color: 'var(--foreground)', width: 46, textAlign: 'right' }}>
        {value} / {max}
      </div>
    </div>
  )
}

// ── Goal card ────────────────────────────────────────────────────────────────
const GOALS = [
  { id: 'wealth', label: 'Wealth Creation', icon: '📈' },
  { id: 'retirement', label: 'Retirement', icon: '🏖️' },
  { id: 'income', label: 'Regular Income', icon: '💰' },
  { id: 'education', label: "Children's Education", icon: '🎓' },
  { id: 'home', label: 'Home Purchase', icon: '🏠' },
  { id: 'marriage', label: 'Marriage', icon: '💍' },
  { id: 'emergency', label: 'Emergency Fund', icon: '🛡️' },
  { id: 'other', label: 'Other', icon: '✦' },
]

// ── Input helpers ────────────────────────────────────────────────────────────
function Field({
  label, type = 'text', value, onChange, placeholder, prefix, hint, locked, optional,
}: {
  label: string; type?: string; value: string; onChange: (v: string) => void
  placeholder?: string; prefix?: string; hint?: string; locked?: boolean; optional?: boolean
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <label style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
          {optional && <span style={{ fontSize: 10, marginLeft: 6, opacity: 0.6 }}>(optional)</span>}
        </label>
        {locked && (
          <span style={{ fontSize: 10, color: 'var(--c-cashflow)', fontFamily: 'var(--font-data)', letterSpacing: '0.04em' }}>
            From your account
          </span>
        )}
      </div>
      <div style={{ position: 'relative' }}>
        {prefix && (
          <span style={{
            position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
            fontSize: 14, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)',
          }}>{prefix}</span>
        )}
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={locked}
          style={{
            width: '100%', background: locked ? 'color-mix(in srgb, var(--secondary) 60%, transparent)' : 'var(--secondary)',
            border: `1px solid ${locked ? 'color-mix(in srgb, var(--border) 50%, transparent)' : 'var(--border)'}`,
            borderRadius: 8, padding: prefix ? '10px 12px 10px 28px' : '10px 12px',
            fontSize: 13, color: locked ? 'var(--muted-foreground)' : 'var(--foreground)',
            fontFamily: 'var(--font-body)', outline: 'none', boxSizing: 'border-box',
            opacity: locked ? 0.7 : 1, cursor: locked ? 'default' : 'text',
          }}
        />
      </div>
      {hint && <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)', marginTop: 4 }}>{hint}</div>}
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--card-radius)',
      padding: 'var(--card-padding)', marginBottom: 'var(--sp-4)',
    }}>
      <h3 style={{ margin: `0 0 var(--sp-4)`, fontSize: 'var(--text-md)', fontFamily: 'var(--font-body)', fontWeight: 600, color: 'var(--foreground)' }}>{title}</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>{children}</div>
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function ClientProfile() {
  const [calculated, setCalculated] = useState(true)
  const [goal, setGoal] = useState('wealth')

  // Pre-filled from "account"
  const [name] = useState('Abhishek Pawar')
  const [email] = useState('abhishek@example.com')
  const [mobile] = useState('+91 98765 43210')

  // Form state
  const [age, setAge] = useState('28')
  const [city, setCity] = useState('Mumbai')
  const [occupation, setOccupation] = useState('Salaried')
  const [dependents, setDependents] = useState('2')
  const [income, setIncome] = useState('75,000')
  const [expenses, setExpenses] = useState('32,000')
  const [emi, setEmi] = useState('12,000')
  const [otherIncome, setOtherIncome] = useState('')
  const [savings, setSavings] = useState('4,50,000')
  const [investments, setInvestments] = useState('25,00,000')
  const [emergency, setEmergency] = useState('2,00,000')
  const [loans, setLoans] = useState('8,50,000')
  const [cc, setCc] = useState('0')
  const [health, setHealth] = useState('10,00,000')
  const [life, setLife] = useState('50,00,000')
  const [targetAmount, setTargetAmount] = useState('2,00,00,000')
  const [targetYear, setTargetYear] = useState('2036')

  const score = 742

  return (
    <div style={{ height: '100%', overflowY: 'auto', background: 'var(--background)' }}>
      {/* Top bar */}
      <div className="profile-topbar">
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', paddingBottom: 16 }}>
          <div>
            <h1 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontSize: 24, color: 'var(--foreground)', fontWeight: 500, letterSpacing: '-0.01em' }}>
              Your Financial Profile
            </h1>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)' }}>
              Help us understand your current financial health.
            </p>
          </div>
          {/* Completion indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 4 }}>
            <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.04em' }}>
              Profile 65% complete
            </div>
            <div style={{ width: 100, height: 5, background: 'var(--secondary)', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{ width: '65%', height: '100%', background: 'var(--c-cashflow)', borderRadius: 99 }} />
            </div>
          </div>
        </div>
      </div>

      {/* Two-column body */}
      <div className="profile-grid">

        {/* ── LEFT: Form ── */}
        <div>

          {/* 1. Personal Info */}
          <SectionCard title="Personal Information">
            <div className="personal-info-grid">
              <Field label="Full Name"      value={name}   onChange={() => {}} locked />
              <Field label="Email Address"  value={email}  onChange={() => {}} locked />
              <Field label="Mobile Number"  value={mobile} onChange={() => {}} locked />
              <Field label="Age" type="number" value={age} onChange={setAge} placeholder="28" />
              <Field label="City"           value={city}         onChange={setCity}       placeholder="Mumbai" />
              <Field label="Occupation"     value={occupation}   onChange={setOccupation} placeholder="Salaried" />
              <Field label="No. of Dependents" type="number" value={dependents} onChange={setDependents} placeholder="2" />
            </div>
          </SectionCard>

          {/* 2. Monthly Cash Flow */}
          <SectionCard title="Monthly Cash Flow">
            <div className="personal-info-grid">
              <Field label="Monthly Income"    value={income}    onChange={setIncome}    prefix="₹" placeholder="75,000" hint="Your primary take-home income" />
              <Field label="Monthly Expenses"  value={expenses}  onChange={setExpenses}  prefix="₹" placeholder="32,000" hint="Household & living costs" />
              <Field label="Monthly EMI / Debt" value={emi}      onChange={setEmi}       prefix="₹" placeholder="12,000" />
              <Field label="Other Monthly Income" value={otherIncome} onChange={setOtherIncome} prefix="₹" placeholder="0" optional />
            </div>
          </SectionCard>

          {/* 3. Savings & Investments */}
          <SectionCard title="Savings & Investments">
            <div className="personal-info-grid">
              <Field label="Total Savings / Cash"  value={savings}      onChange={setSavings}      prefix="₹" placeholder="4,50,000" />
              <Field label="Total Investments"     value={investments}  onChange={setInvestments}  prefix="₹" placeholder="25,00,000" hint="Stocks, MF, FD combined" />
              <Field label="Emergency Fund"        value={emergency}    onChange={setEmergency}    prefix="₹" placeholder="2,00,000" />
            </div>
            <button style={{ background: 'none', border: 'none', color: 'var(--c-dsp)', fontSize: 12, cursor: 'pointer', padding: 0, fontFamily: 'var(--font-body)', textAlign: 'left' }}>
              + Add investment details
            </button>
          </SectionCard>

          {/* 4. Debt & Protection */}
          <SectionCard title="Debt & Protection">
            <div className="personal-info-grid">
              <Field label="Outstanding Loans"     value={loans}   onChange={setLoans}  prefix="₹" placeholder="8,50,000" />
              <Field label="Credit Card Outstanding" value={cc}    onChange={setCc}     prefix="₹" placeholder="0" />
              <Field label="Health Insurance"      value={health}  onChange={setHealth} prefix="₹" placeholder="10,00,000" />
              <Field label="Life / Term Insurance" value={life}    onChange={setLife}   prefix="₹" placeholder="50,00,000" />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--muted-foreground)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
              <input type="checkbox" style={{ accentColor: 'var(--c-dsp)' }} />
              No outstanding debt
            </label>
          </SectionCard>

          {/* 5. Financial Goal */}
          <SectionCard title="Primary Financial Goal">
            <div className="goal-grid">
              {GOALS.map(g => (
                <button
                  key={g.id}
                  onClick={() => setGoal(g.id)}
                  style={{
                    background: goal === g.id ? 'color-mix(in srgb, var(--c-dsp) 15%, transparent)' : 'var(--secondary)',
                    border: `1px solid ${goal === g.id ? 'var(--c-dsp)' : 'var(--border)'}`,
                    borderRadius: 10, padding: '10px 8px', cursor: 'pointer', textAlign: 'center',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ fontSize: 18, marginBottom: 4 }}>{g.icon}</div>
                  <div style={{ fontSize: 10, color: goal === g.id ? 'var(--foreground)' : 'var(--muted-foreground)', fontFamily: 'var(--font-body)', lineHeight: 1.3 }}>
                    {g.label}
                  </div>
                </button>
              ))}
            </div>
            <div className="personal-info-grid" style={{ marginTop: 4 }}>
              <Field label="Target Amount" optional value={targetAmount} onChange={setTargetAmount} prefix="₹" placeholder="2,00,00,000" />
              <Field label="Target Year"   optional value={targetYear}   onChange={setTargetYear}   placeholder="2036" />
            </div>
          </SectionCard>

          {/* CTAs */}
          <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
            <button
              onClick={() => setCalculated(true)}
              style={{
                flex: 1, background: 'var(--c-dsp)', color: '#fff', border: 'none',
                borderRadius: 10, padding: '14px', fontSize: 14, cursor: 'pointer',
                fontFamily: 'var(--font-body)', fontWeight: 600,
              }}
            >
              {calculated ? 'Update Financial Profile' : 'Calculate My Financial Health Score'}
            </button>
            <button style={{
              background: 'none', border: '1px solid var(--border)', borderRadius: 10,
              padding: '14px 20px', fontSize: 13, cursor: 'pointer', color: 'var(--muted-foreground)',
              fontFamily: 'var(--font-body)',
            }}>
              Save &amp; Continue Later
            </button>
          </div>
        </div>

        {/* ── RIGHT: Score card ── */}
        <div className="score-sticky">
          {/* Main score card */}
          <div style={{
            background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--card-radius)',
            padding: 'var(--card-padding)', marginBottom: 'var(--sp-4)',
          }}>
            <div style={{ textAlign: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', letterSpacing: '0.07em', marginBottom: 2 }}>
                FINANCIAL HEALTH SCORE
              </div>
              <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)' }}>
                An overall view of your current financial position.
              </div>
            </div>
            <HealthGauge score={score} />
          </div>

          {/* Score breakdown */}
          <div style={{
            background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--card-radius)',
            padding: 'var(--card-padding)', marginBottom: 'var(--sp-4)',
          }}>
            <h4 style={{ margin: '0 0 14px', fontSize: 13, fontFamily: 'var(--font-body)', fontWeight: 600, color: 'var(--foreground)' }}>
              What influences your score?
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <ScoreRow label="Income Strength"       value={82} />
              <ScoreRow label="Savings & Investments" value={76} />
              <ScoreRow label="Debt Management"       value={71} />
              <ScoreRow label="Emergency Protection"  value={68} />
              <ScoreRow label="Goal Readiness"        value={74} />
            </div>
          </div>

          {/* Insight card */}
          <div style={{
            background: 'color-mix(in srgb, var(--c-cashflow) 8%, var(--card))',
            border: '1px solid color-mix(in srgb, var(--c-cashflow) 25%, transparent)',
            borderRadius: 'var(--card-radius)', padding: 'var(--card-padding)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--foreground)', fontFamily: 'var(--font-body)', marginBottom: 8 }}>
              Your financial position is healthy.
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-body)', lineHeight: 1.6 }}>
              Building a stronger emergency fund and improving debt management could further improve your Financial Health Score.
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
