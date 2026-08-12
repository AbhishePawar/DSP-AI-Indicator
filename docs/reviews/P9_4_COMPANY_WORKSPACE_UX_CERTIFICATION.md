# P9.4A — Company Analysis Workspace UX & Visual Certification

| Field | Value |
|---|---|
| Programme | P9.4 / EPIC-005 · P9.4A Institutional UX & Visual Certification |
| Surface | Company Analysis Workspace (`/analysis`) |
| Date | 2026-08-01 |
| Reviewer | Cursor agent (product quality review) |
| Design System | `docs/design/` v1.0.0 |
| Ontology | REP-002 Research Ontology v1.0 |
| Thin client | Frozen `/api/v1/analyse` (+ optional market quote) only |
| Decision | **PASS WITH CONDITIONS** |

---

## 1. Executive Summary

The Company Analysis Workspace is the flagship analytical interface of DSP AI Indicator. This review audited every registered module, primary interactions, loading/empty/error states, design-system conformance, REP-002 terminology, User Trust Standard ladder, accessibility, and performance patterns.

**Verdict: PASS WITH CONDITIONS.**

The workspace is production-quality for Research Mode institutional use: it is thin-client, honest about missing data, sectioned for explainability, keyboard-accessible, theme-aware, and lazy-loaded. Blocking terminology and trust defects found during review were remediated in the frontend (ontology labels, dishonest risk aliasing, epistemic ladder chips, typed analyse errors). Residual conditions are tracked below with owners.

This is **not** a backend redesign. No API contracts or engines were modified.

---

## 2. Visual Review

### 2.1 Module coverage

| Module | Present | Visual notes |
|---|---|---|
| Company Header | ✓ | Name, ticker, exchange, sector, industry, market cap, coverage, research timestamp, confidence, Compare / Watchlist / Share |
| Executive Summary | ✓ | Institutional summary, recommendation, confidence, positives, risks, research notes, Research ladder |
| Valuation | ✓ | IV, price, MoS, DCF, Relative, Residual Income, EPV, overall, confidence |
| Business Quality | ✓ | Overall score + Book 04 concept labels |
| Management | ✓ | Book 05 concept labels (remediated) |
| Economic Moat | ✓ | Book 06 concept labels (remediated) |
| Risk | ✓ | Book 07 labels; honest Unavailable when stage lacks dimensions (remediated) |
| Financial Performance | ✓ | Revenue/profit/cash/margins/debt/ROE/ROCE + honest historical empty |
| AI Committee | ✓ | Decision, rationale, opposing evidence, confidence, review history |
| Explainability | ✓ | Reasoning path, evidence chain, confidence contributors, sources, contradictory evidence |
| Supporting Evidence | ✓ | Research objects, cards, honest document/dataset/statement empties |
| Research Timeline | ✓ | Pipeline stages, recommendation history, material-events empty |
| Downloads | ✓ | PDF/print, share, research report link, JSON/CSV export |

Deep-dive modules (Institutional Ratings, Valuation Transparency, Research Object, Buffett Indicator, Compliance) remain available under a secondary nav group without displacing the flagship reading order.

### 2.2 Design System (`docs/design/`)

| Gate | Result | Notes |
|---|---|---|
| Typography (Fraunces / Sora via DS tokens) | Pass | Section titles use DS `CardTitle` / display font tokens |
| Spacing / grid | Pass | `space-y-4`, responsive `sm/lg` grids; no ad-hoc spacing scale |
| Colors / themes | Pass | CSS variables (`--accent`, `--surface`, `--border`); Light/Dark controls verified in shell |
| Elevation | Pass | Card border + DS shadow tokens; no decorative glow stacks |
| Buttons / cards | Pass | `@/components/ds` Button, Badge, Card, EmptyState, Skeleton, ErrorState |
| Icons | Pass with conditions | Sparse Lucide usage in shell/search; workspace modules are text-first (acceptable for research density) |
| Charts / tables | Pass with conditions | No fabricated charts; historical trends empty. Ratings table uses DS patterns when deep-dive opened |
| Motion | Pass | `motion-reduce:` on blur/scroll; section Suspense skeletons |

**Visual QA captures:** Desktop Light layout confirmed (three-column workspace, DS teal accent, empty-state honesty). Desktop Dark / Tablet / Mobile / Landscape: structure is responsive (`lg` panel collapse, stacked sections); full screenshot matrix incomplete in this environment when screenshot tooling timed out and analyse API was unauthenticated — tracked as Condition C-VQA-01.

---

## 3. Accessibility Review

| Check | Result |
|---|---|
| Keyboard navigation | Pass — Ctrl+Enter analyse; 1–9 / E T R V O B C sections; `[` / `]` panels |
| Focus rings | Pass — DS `focus-visible:ring-[var(--accent)]` |
| Semantic regions | Pass — `aria-label` on nav, main analysis, context panel; skip link present in shell |
| ARIA | Pass — `aria-pressed`, `aria-current`, `aria-busy` skeleton, disclaimer dialog |
| Reduced motion | Pass — `motion-reduce:backdrop-blur-none`, `motion-reduce:scroll-auto` |
| Contrast | Pass with conditions — DS tokens intended for AA; no automated axe scan in this review (C-A11Y-01) |
| Screen readers | Pass with conditions — Field rows are `dl/dt/dd`; accordion explainability uses DS Accordion |

Research disclaimer gate blocks analyse until acknowledged — correct Research Mode behaviour.

---

## 4. Performance Review

| Check | Result |
|---|---|
| Lazy loading heavy sections | Pass — `React.lazy` + `Suspense` for valuation, quality, management, moat, risk, financial, AI, explainability, evidence, timeline, ratings, transparency, Buffett, compliance |
| Code splitting | Pass — section modules split from eager Summary / Downloads |
| Skeleton loading | Pass — `WorkspaceSkeleton` + section fallback |
| Layout shifts | Pass with conditions — panel prefs persist; no reserved height for async section content beyond skeleton (acceptable) |
| Initial render | Pass with conditions — shell + empty/skeleton first paint; live `<2s` with authenticated API not measured here (C-PERF-01) |
| Interaction latency | Pass — section switches are local state; no client scoring |
| Virtualized tables | N/A — no long financial line-item tables in this surface yet |

---

## 5. Trust Review

| Trust Standard pillar | Result |
|---|---|
| Traceable | Pass — correlation ID, pipeline/platform versions, stage status |
| Explainable | Pass — Research ladder + Explainability accordion |
| Consistent | Pass after remediation — REP-002 labels restored |
| Transparent AI | Pass — committee opposing evidence + confidence contributors |
| Research first | Pass — Research Mode copy; disclaimer gate |
| Honest | Pass after remediation — Risk no longer aliases financial_strength label as Business Risk |
| Actionable | Pass — Compare, Watchlist, Share, institutional dashboard, Copilot links, Retry |

**Ladder verified on Executive Summary:**

Observed Facts → Analysis → Inference → Recommendation, with confidence on inference and recommendation layers, and epistemic badges.

**Contradictory evidence:** AI Committee + Explainability surfaces opposing reasons / weaknesses / risks when present; empty when absent (honest).

---

## 6. Consistency Review (REP-002 v1.0)

| Domain | Book | UI alignment after remediation |
|---|---|---|
| Business Quality | Book 04 | Capital Allocation Quality, Reinvestment Opportunity, Operating Discipline, Industry Structure, Franchise Durability |
| Management | Book 05 | Management Quality, Corporate Governance, Integrity, Execution Capability, Shareholder Orientation, Leadership Quality |
| Economic Moat | Book 06 | Economic Moat, Brand Strength, Network Effects, Switching Costs, Distribution Advantage, Cost-Based Moat, Moat Durability |
| Risk | Book 07 | Business / Financial / Operational / Regulatory Risk, Permanent Capital Loss, Margin of Safety — values only when stage exposes them |

**Removed inconsistencies:** “Shareholder Alignment”, bare “Network”, “Governance” (without Corporate), “Cost Advantage” as moat primary label, “Downloads/Exports” naming drift (nav + panel now **Downloads**).

No duplicate parallel ontology invented. Missing sub-metrics remain **Data unavailable.**

---

## 7. Empty & Error States

| State | Result |
|---|---|
| Empty (no analysis yet) | Pass — “Run analysis to load…” |
| Unavailable field | Pass — FieldRow → “Data unavailable.” |
| Documents / datasets / statements / historical trends / material events | Pass — explicit why-unavailable copy |
| API unavailable / 5xx | Pass — typed error copy + Retry |
| Network timeout | Pass — typed message |
| Permission denied (401/403) | Pass — typed message (remediated) |
| No coverage (404) | Pass — typed message (remediated) |
| Partial coverage | Pass — header Coverage shows failed stage when present |
| Unknown company | Pass — catalogue miss still allows Analyse against API; search notes honesty |
| Fabricated research | Pass — none observed |

---

## 8. Issues Found

### Remediated in this certification (frontend only)

| ID | Severity | Issue | Fix |
|---|---|---|---|
| F-ONT-01 | High | Management labels diverged from Book 05 (Alignment, Governance, Execution, Leadership) | Aligned to Corporate Governance, Execution Capability, Shareholder Orientation, Leadership Quality |
| F-ONT-02 | High | Moat labels used Brand / Network / Distribution / Cost Advantage | Aligned to Brand Strength, Network Effects, Distribution Advantage, Cost-Based Moat |
| F-ONT-03 | Medium | BQ used short Capital Allocation / Reinvestment | Aligned to Capital Allocation Quality / Reinvestment Opportunity |
| F-TRUST-01 | High | Risk mapped `financial_strength` label/decision as Business/Financial Risk | Removed aliasing; Book 07 fields Unavailable unless present |
| F-TRUST-02 | Medium | Epistemic categories not visible on Research ladder | Added category badges + layer annotations |
| F-UX-01 | Low | Downloads vs Exports label drift | Unified to Downloads |
| F-ERR-01 | Medium | Analyse errors were generic | Typed 401/403/404/408/504/5xx / network copy |

### Open conditions

| ID | Severity | Condition | Owner | Target |
|---|---|---|---|---|
| C-VQA-01 | Medium | Complete screenshot matrix (Desktop Dark, Tablet, Mobile, Landscape) with authenticated analyse payload | Frontend UX | Next polish sprint |
| C-A11Y-01 | Low | Automated axe/contrast CI gate on `/analysis` | Frontend QA | P9 a11y CI |
| C-PERF-01 | Low | Measure LCP/INP with production API under typical broadband; publish numbers | Frontend Perf | Perf budget review |
| C-TRUST-01 | Low | Optional per-`FieldRow` SourceBadge (DS) — currently section/ladder level | Frontend Trust | Follow-up |
| C-DS-01 | Low | Align legacy `SourceBadge` to `@/components/ds` (still on `ui/Badge`) before workspace-wide adoption | Design System | DS cleanup |

---

## 9. Recommendations

1. Run authenticated Visual QA matrix and attach screenshots under `docs/reviews/assets/p9-4/` when API is available.  
2. Add axe check to web CI for `/analysis` route.  
3. Prefer DS `SourceBadge` on deep-dive rating modules first, then FieldRow opt-in.  
4. Keep historical charts out until filings/series APIs are frozen for the thin client — do not fabricate series.  
5. Treat this workspace as the reference layout for future analytical modules (section registry + lazy Suspense + Trust ladder).

---

## 10. Certification Decision

### **PASS WITH CONDITIONS**

**Rationale**

- Flagship modules present and navigable.  
- Design System components/tokens used; no parallel visual language.  
- Thin client preserved; no engine/API changes.  
- REP-002 terminology remediated for Management, Moat, Business Quality, and Risk honesty.  
- Trust ladder, confidence, evidence, and contradictory evidence paths present.  
- Accessibility and performance patterns meet institutional baseline.  
- Remaining items are non-blocking conditions with named follow-ups.

**Ship guidance:** Workspace may remain the production flagship Research Mode surface. Conditions C-VQA-01 / C-A11Y-01 / C-PERF-01 / C-TRUST-01 / C-DS-01 must not regress honesty or ontology labels when addressed.

---

## 11. Authority checklist (docs/design/15)

| Gate | Result |
|---|---|
| A1 Constitution | Pass |
| A2 User Trust Standard | Pass (after F-TRUST-*) |
| A3 Thin client | Pass |
| A4 REP-002 alignment | Pass (after F-ONT-*) |
| A5 Design System | Pass with C-DS-01 |

---

## 12. References

- `apps/web/src/components/company-analysis/`
- `apps/web/src/lib/company-analysis/sections.ts`
- `docs/design/` (01–15)
- `docs/research/REP-002_Research_Ontology/` Books 04–07
- `docs/USER_TRUST_STANDARD.md`
- `docs/PRODUCT_CONSTITUTION.md`
