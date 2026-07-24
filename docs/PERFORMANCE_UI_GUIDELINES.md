# Performance UI Guidelines

**Epic:** PR1.2 · VLIS  
**Goal:** Research UI feels instant; heavy visuals never block reading the conclusion.

---

## 1. Principles

1. **Paint shell first** — nav + skeleton, then data.  
2. **Lazy everything below the fold** — charts, KG, Copilot mount on demand.  
3. **Skeletons over spinners** for layout-stable waits.  
4. **No business logic in the client** — perf work is rendering/fetch UX only.  
5. **Measure** — LCP/CLS/INP budgets below.

---

## 2. Lazy loading

| Asset | Strategy |
|---|---|
| Analysis sections | Fetch/render when near viewport or accordion open |
| Charts | Dynamic import chart lib per section |
| Knowledge Graph | Load engine when section opened |
| Copilot panel | Code-split route + lazy panel chunk |
| Images / logos | `next/image` or lazy `loading`; sized explicitly |
| Fonts | `next/font` already; avoid extra families |

---

## 3. Code splitting

| Split | Why |
|---|---|
| `/analysis` heavy widgets | Keep dashboard light |
| Chart vendor | Large dependency |
| KG visualization | Large dependency |
| Settings / rarely used modals | Defer |

Prefer route-level and `next/dynamic` with skeleton `loading`.

---

## 4. Skeletons

- Match final card geometry (reduce CLS).  
- One skeleton theme (surface-2 pulse) — disable pulse if reduced motion.  
- Never skeleton the entire viewport for a single failing widget.

---

## 5. Images

- Explicit width/height or aspect-ratio.  
- Compressed modern formats.  
- No full-bleed decorative photos on Analysis (keeps LCP clean).  

---

## 6. Tables & lists

| Threshold | Technique |
|---|---|
| > 100 rows | Window virtualization |
| Wide tables | Virtualize columns only if necessary; else horizontal scroll |
| Recent reports | Keep short (local max already ≤ 8) |

---

## 7. Data fetching UX

- TanStack Query: stale-while-revalidate; show prior data where safe.  
- Deduplicate `health` / `platform` queries.  
- Cancel in-flight Copilot on close.  
- Empty/error states must be cheap (no retry storms).  

---

## 8. Budgets (targets)

| Metric | Target |
|---|---|
| LCP (Dashboard) | < 2.5s on mid cable |
| CLS | < 0.1 |
| INP | < 200ms |
| Analysis initial JS | Keep chart/KG out of first load |

---

## 9. Rendering hygiene

- Avoid huge JSON `<pre>` dumps in default view — collapse behind “Raw envelope”.  
- Memoize only when profiling shows need (follow React Compiler guidance if enabled).  
- IntersectionObserver for TOC — disconnect on unmount.  

---

## 10. Performance checklist

- [ ] Shell interactive without waiting all widgets  
- [ ] Charts/KG not in initial bundle  
- [ ] Skeletons prevent CLS  
- [ ] Large tables virtualized  
- [ ] Images sized  
- [ ] Reduced motion doesn’t leave infinite spinners  
- [ ] Network errors don’t infinite retry  
