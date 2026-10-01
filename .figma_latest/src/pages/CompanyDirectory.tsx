import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/Nav'

const COMPANIES = [
  { symbol: 'TCS', name: 'Tata Consultancy Services', sector: 'IT', mcap: '₹13.9L Cr', rating: 'A+', price: '₹3,842', change: '+1.2%', up: true },
  { symbol: 'INFY', name: 'Infosys', sector: 'IT', mcap: '₹7.5L Cr', rating: 'A', price: '₹1,792', change: '+0.8%', up: true },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', sector: 'Banking', mcap: '₹12.7L Cr', rating: 'A+', price: '₹1,680', change: '-0.3%', up: false },
  { symbol: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy', mcap: '₹19.9L Cr', rating: 'B+', price: '₹2,945', change: '+2.1%', up: true },
  { symbol: 'WIPRO', name: 'Wipro', sector: 'IT', mcap: '₹2.5L Cr', rating: 'B', price: '₹476', change: '-0.6%', up: false },
  { symbol: 'BAJFIN', name: 'Bajaj Finance', sector: 'NBFC', mcap: '₹4.5L Cr', rating: 'B+', price: '₹7,340', change: '+0.4%', up: true },
  { symbol: 'ASIANPAINT', name: 'Asian Paints', sector: 'FMCG', mcap: '₹2.8L Cr', rating: 'A', price: '₹2,760', change: '-1.1%', up: false },
  { symbol: 'HCLTECH', name: 'HCL Technologies', sector: 'IT', mcap: '₹4.1L Cr', rating: 'A', price: '₹1,514', change: '+0.9%', up: true },
  { symbol: 'TITAN', name: 'Titan Company', sector: 'Cons. Disc.', mcap: '₹2.4L Cr', rating: 'A', price: '₹3,286', change: '+1.8%', up: true },
  { symbol: 'DMART', name: 'Avenue Supermarts', sector: 'Retail', mcap: '₹3.2L Cr', rating: 'B+', price: '₹4,921', change: '+0.2%', up: true },
  { symbol: 'SUNPHARMA', name: 'Sun Pharma', sector: 'Pharma', mcap: '₹3.8L Cr', rating: 'A', price: '₹1,586', change: '+0.6%', up: true },
  { symbol: 'LTIM', name: 'LTIMindtree', sector: 'IT', mcap: '₹1.4L Cr', rating: 'B+', price: '₹4,620', change: '-0.4%', up: false },
]

const SECTORS = ['All Sectors', 'IT', 'Banking', 'Energy', 'NBFC', 'FMCG', 'Pharma', 'Cons. Disc.', 'Retail']
const RATINGS = ['All Ratings', 'A+', 'A', 'B+', 'B', 'C']

export default function CompanyDirectory() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [sector, setSector] = useState('All Sectors')
  const [rating, setRating] = useState('All Ratings')

  const filtered = COMPANIES.filter(c => {
    const matchSearch = !search || c.symbol.toLowerCase().includes(search.toLowerCase()) || c.name.toLowerCase().includes(search.toLowerCase())
    const matchSector = sector === 'All Sectors' || c.sector === sector
    const matchRating = rating === 'All Ratings' || c.rating === rating
    return matchSearch && matchSector && matchRating
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Company Directory" subtitle="Discover and search listed securities" />
      <div className="scroll-container" style={{ flex: 1, overflow: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Search & filters */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or ticker..."
            style={{ flex: 1, minWidth: 240, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 14px', fontSize: 14, color: 'var(--foreground)', fontFamily: 'var(--font-body)', outline: 'none' }} />
          <select value={sector} onChange={e => setSector(e.target.value)}
            style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', color: 'var(--foreground)', fontSize: 13, fontFamily: 'var(--font-data)', cursor: 'pointer', outline: 'none' }}>
            {SECTORS.map(s => <option key={s} value={s} style={{ background: 'var(--card)' }}>{s}</option>)}
          </select>
          <select value={rating} onChange={e => setRating(e.target.value)}
            style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', color: 'var(--foreground)', fontSize: 13, fontFamily: 'var(--font-data)', cursor: 'pointer', outline: 'none' }}>
            {RATINGS.map(r => <option key={r} value={r} style={{ background: 'var(--card)' }}>{r}</option>)}
          </select>
          <span style={{ fontSize: 12, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{filtered.length} results</span>
        </div>

        {/* Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {filtered.map(c => (
            <div key={c.symbol}
              style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 18px', cursor: 'pointer', transition: 'border-color 0.15s, transform 0.1s' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(124,106,247,0.4)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)' }}
              onClick={() => navigate(`/analysis?symbol=${c.symbol}`)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--foreground)', fontFamily: 'var(--font-data)', marginBottom: 3 }}>{c.symbol}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted-foreground)', lineHeight: 1.3 }}>{c.name}</div>
                </div>
                <span style={{ fontSize: 11, color: 'var(--c-dsp)', fontFamily: 'var(--font-data)', background: 'rgba(124,106,247,0.12)', borderRadius: 6, padding: '3px 8px', fontWeight: 600, flexShrink: 0, marginLeft: 8 }}>{c.rating}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 16, color: 'var(--foreground)', fontFamily: 'var(--font-data)', fontWeight: 500 }}>{c.price}</div>
                  <div style={{ fontSize: 12, color: c.up ? 'var(--c-profit)' : 'var(--c-risk)', fontFamily: 'var(--font-data)' }}>{c.change}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 10, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{c.sector}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>{c.mcap}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
