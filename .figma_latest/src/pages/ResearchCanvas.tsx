import { useState } from 'react'
import { TopBar } from '../components/Nav'

const INITIAL_BLOCKS = [
  { id: 1, type: 'heading', content: 'TCS — Investment Thesis' },
  { id: 2, type: 'text', content: 'TCS is the market leader in Indian IT services with consistent revenue growth, a fortress balance sheet, and industry-leading return ratios. The company generates strong free cash flow and maintains a negligible debt position.' },
  { id: 3, type: 'metric', content: 'Revenue: ₹2,703 Bn | ROCE: 47.8% | FCF: ₹518 Cr | Rating: A+' },
  { id: 4, type: 'heading', content: 'Key Risks' },
  { id: 5, type: 'text', content: '• High client concentration in BFSI\n• USD/INR sensitivity on margins\n• Technology disruption from AI/automation\n• Talent attrition in senior roles' },
  { id: 6, type: 'heading', content: 'Valuation View' },
  { id: 7, type: 'text', content: 'At current P/E of 27.4×, TCS trades at a premium to sector. Justified by quality of business and cash generation. Target: ₹4,200–4,400 over 12–18 months.' },
]

const BLOCK_TYPES = ['heading', 'text', 'metric', 'table', 'chart-ref', 'divider']

export default function ResearchCanvas() {
  const [blocks, setBlocks] = useState(INITIAL_BLOCKS)
  const [activeBlock, setActiveBlock] = useState<number | null>(null)
  const [saved, setSaved] = useState(false)

  function updateBlock(id: number, content: string) {
    setBlocks(prev => prev.map(b => b.id === id ? { ...b, content } : b))
    setSaved(false)
  }

  function addBlock(type: string) {
    const newBlock = { id: Date.now(), type, content: type === 'heading' ? 'New section' : type === 'metric' ? 'Metric: value' : '' }
    setBlocks(prev => [...prev, newBlock])
  }

  function removeBlock(id: number) {
    setBlocks(prev => prev.filter(b => b.id !== id))
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopBar title="Research Canvas" subtitle="Notebook-style research environment" />
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 200px', overflow: 'hidden' }}>
        {/* Canvas */}
        <div className="scroll-container" style={{ overflow: 'auto', padding: '32px 48px' }}>
          <div style={{ maxWidth: 700, margin: '0 auto' }}>
            {/* Canvas toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
              <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)' }}>
                {saved ? '✓ Saved' : 'Unsaved changes'}
              </div>
              <button onClick={() => setSaved(true)}
                style={{ fontSize: 12, color: 'var(--foreground)', background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 14px', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
                Save canvas
              </button>
            </div>

            {/* Blocks */}
            {blocks.map(block => (
              <div key={block.id}
                style={{ position: 'relative', marginBottom: 16, group: 'block' } as React.CSSProperties}
                onMouseEnter={e => {
                  const del = (e.currentTarget as HTMLDivElement).querySelector('.del-btn') as HTMLButtonElement
                  if (del) del.style.opacity = '1'
                }}
                onMouseLeave={e => {
                  const del = (e.currentTarget as HTMLDivElement).querySelector('.del-btn') as HTMLButtonElement
                  if (del) del.style.opacity = '0'
                }}>
                <button className="del-btn" onClick={() => removeBlock(block.id)}
                  style={{ position: 'absolute', left: -28, top: 8, background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer', fontSize: 14, opacity: 0, transition: 'opacity 0.15s', padding: '2px 6px' }}>
                  ×
                </button>
                {block.type === 'heading' && (
                  <input value={block.content} onChange={e => updateBlock(block.id, e.target.value)}
                    style={{ width: '100%', background: 'none', border: 'none', outline: 'none', fontSize: 22, fontFamily: 'var(--font-heading)', color: 'var(--foreground)', fontWeight: 500, padding: 0, marginBottom: 4 }} />
                )}
                {block.type === 'text' && (
                  <textarea value={block.content} onChange={e => updateBlock(block.id, e.target.value)} rows={3}
                    style={{ width: '100%', background: 'none', border: 'none', outline: 'none', fontSize: 14, fontFamily: 'var(--font-body)', color: 'var(--foreground)', lineHeight: 1.7, padding: 0, resize: 'vertical' }} />
                )}
                {block.type === 'metric' && (
                  <div style={{ background: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px', borderLeft: '3px solid var(--c-dsp)' }}>
                    <input value={block.content} onChange={e => updateBlock(block.id, e.target.value)}
                      style={{ width: '100%', background: 'none', border: 'none', outline: 'none', fontSize: 13, fontFamily: 'var(--font-data)', color: 'var(--c-dsp)' }} />
                  </div>
                )}
                {block.type === 'divider' && (
                  <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '8px 0' }} />
                )}
                {block.type === 'chart-ref' && (
                  <div style={{ background: 'var(--muted)', border: '1px dashed var(--border)', borderRadius: 10, padding: '20px', textAlign: 'center', color: 'var(--muted-foreground)', fontSize: 12, fontFamily: 'var(--font-data)' }}>
                    [Chart placeholder — ask DSP to generate]
                  </div>
                )}
              </div>
            ))}

            {/* Add block */}
            <div style={{ marginTop: 24, paddingTop: 24, borderTop: '1px solid var(--border)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {BLOCK_TYPES.map(t => (
                <button key={t} onClick={() => addBlock(t)}
                  style={{ fontSize: 12, color: 'var(--muted-foreground)', background: 'none', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontFamily: 'var(--font-data)', transition: 'all 0.15s' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--c-dsp)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--c-dsp)' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--muted-foreground)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)' }}>
                  + {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Outline panel */}
        <div style={{ background: 'var(--card)', borderLeft: '1px solid var(--border)', padding: '20px 16px', overflow: 'auto' }}>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>Outline</div>
          {blocks.filter(b => b.type === 'heading').map(b => (
            <div key={b.id} style={{ fontSize: 12, color: 'var(--muted-foreground)', padding: '4px 0', cursor: 'pointer', lineHeight: 1.4 }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--foreground)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted-foreground)')}>
              {b.content}
            </div>
          ))}
          <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'var(--font-data)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>Info</div>
            <div style={{ fontSize: 12, color: 'var(--muted-foreground)', lineHeight: 1.7 }}>
              <div>{blocks.length} blocks</div>
              <div>{blocks.filter(b => b.type === 'text').length} text sections</div>
              <div>~{blocks.filter(b => b.type === 'text').reduce((a, b) => a + b.content.split(' ').length, 0)} words</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
