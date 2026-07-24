# Knowledge Graph UX

**Epic:** PR1.1 · PXB  
**Section:** Knowledge Graph (Analysis) · optional full-page later  
**Data:** Cite KG reports via API — no graph math in browser beyond layout.

---

## 1. Goals

- Make relationships explorable: company ↔ peers ↔ risks ↔ evidence ↔ reports.  
- Support “why is this connected?” for trust.  
- Feed Copilot with selected subgraph context.

---

## 2. Node types

| Type | Visual | Examples |
|---|---|---|
| Company | Primary node | Subject symbol |
| Peer | Secondary | Comparable firms |
| Metric / Factor | Diamond | ROIC, leverage |
| Risk | Warning tone | Cyclicality, concentration |
| Evidence | Doc icon | Filing excerpt ref |
| Report | Envelope | Research / Risk report refs |
| Thesis / Conclusion | Star | Research Conclusion node |
| Street (optional) | Dashed | Consensus node when available |

---

## 3. Edge semantics (display labels)

| Edge | Meaning |
|---|---|
| `supports` | Evidence supports claim |
| `contradicts` | Tension / conflict |
| `peer_of` | Comparison eligibility |
| `derived_from` | Metric derived from inputs |
| `cites` | Report citation |
| `impacts` | Risk impacts thesis |

---

## 4. Interactions

| Action | Behaviour |
|---|---|
| Click node | Detail drawer: type, summary, links, Ask AI |
| Double-click / “Focus” | Recenter ego network |
| Hover edge | Label + short rationale |
| Multi-select | Compare selected · send to Copilot |
| Filter | Toggle node types / edge types |
| Search | Find node by name |
| Reset | Return to company-centric layout |

---

## 5. Filters (default on)

- Company · Evidence · Risk · Peer  
Optional: Street · Report · Metric  

Density control: Low (ego + 1 hop) · Medium · High (power users).

---

## 6. Use cases

1. **Trace conclusion** — Conclusion → supporting evidence path.  
2. **Peer contrast** — Company ↔ peers on shared factors.  
3. **Risk walk** — Risk node → impacted scores → takeaways.  
4. **Conflict hunt** — Highlight `contradicts` edges for Challenge Mode.  
5. **Report lineage** — Report → cited artifacts.

---

## 7. Layout & empty states

| State | UX |
|---|---|
| Loading | Skeleton canvas + “Building relationship view…” |
| Empty | Empty State — KG not available for symbol |
| Sparse | Show what exists + “limited relationships” Alert |
| Error | Error State + retry |

Desktop: canvas + right detail.  
Mobile: list-first relationships; “Open graph” full-screen secondary.

---

## 8. Accessibility

- Provide **list/table alternative** of nodes and edges.  
- Keyboard: tab nodes, Enter open, Esc close drawer.  
- Do not convey meaning by color alone.  
