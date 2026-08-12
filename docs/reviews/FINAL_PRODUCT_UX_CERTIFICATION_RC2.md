# FINAL PRODUCT UX CERTIFICATION — RC-2

| Field | Value |
|---|---|
| Programme | Final UX Certification · RC-2 Institutional Product Audit · Pre-Production Review |
| Scope | Complete DSP AI Indicator frontend (user-facing) |
| Date | 2026-08-01 |
| Reviewer | Independent Cursor agent product audit (adversarial) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Assumption | Product ships **tomorrow** to paying institutional clients |
| Prior certifications | **Re-reviewed independently — not trusted as ground truth** |
| Thin client | Frozen `/api/v1` only — no browser valuation / recommendation / AI reasoning |
| Decision | **FAIL** |

---

## 1. Executive Summary

**DSP AI Indicator is not ready for production launch tomorrow.**

The platform has a serious institutional *intent*: Design System tokens, Research Mode language, honest “Data unavailable.” empties on many panels, thin-client discipline, and a credible trust ladder on Institutional Reports. That intent is real.

What a paying desk would experience tomorrow is still an **RC with footnotes**:

1. **Semantic fabrication on the flagship Company Analysis surface** — REP-002 Business Quality dimension labels are filled from Management / Growth / Earnings / Moat stage fields (`QualitySection`).
2. **Commerce and account UX that performs theatre** — signup/forgot/reset/verify collect credentials or imply progress without APIs; Contact publishes `.example` emails while `channelsPublished: false`.
3. **Trust ladder is not universal** — Institutional Reports largely pass; Dashboard / Portfolio / Research Workspace / IRD fail the “every analytical page” bar.
4. **Product fragmentation** — multiple analyse/report surfaces (Company Analysis, Research Workspace, Institutional Reports, IRD, legacy `/analysis` components, AUX palette routes) with inconsistent honesty rules.
5. **Dual UI stacks and unfinished polish** — DS vs `components/ui`, empty executive widgets, fake `lazy()` wrappers, no screenshot matrix, no Firefox/Safari pass.

**Overall Product Score: 4.8 / 10**

| Persona lens | Verdict |
|---|---|
| Institutional investor | Would not rely on BQ dimension rows or portfolio “Health / Compounders” labels |
| Portfolio manager | Portfolio Intelligence is coverage theatre + honest empties — not desk-ready |
| Financial advisor | Auth/commerce broken; cannot onboard a client org |
| Retail investor | Overwhelmed by jargon (REP-002, thin client, frozen API) |
| Accessibility reviewer | Partial — focus traps improved; no axe CI; small touch targets remain |
| Product designer | Marketing looks composed; app feels like multiple specs under one skin |
| UX expert | Navigation dual-model (sidebar vs AUX palette) |
| QA engineer | Critical honesty defects; Visual QA matrix incomplete |
| Design System reviewer | Tokens good; component migration incomplete |
| Trust & Explainability reviewer | **FAIL** until BQ aliasing and universal ladder close |

**Would I pay ₹50,000/year?** **No — not tomorrow.** I would fund a closed beta or paid pilot only with a written remediation schedule for CRITICAL/HIGH items. I would not recommend firm-wide rollout.

Prior P9.7 “PASS WITH CONDITIONS” is **overruled for production ship**. Conditions that were treated as polish are launch blockers under a tomorrow-ship assumption.

---

## 2. Audit Methodology

1. **Independent adversarial review** — prior certification docs consulted only as leads, then re-verified in source.
2. **Static code audit** of marketing, auth, shell, theme, dashboard, company-analysis, portfolio-intelligence, research-workspace, institutional-reports, institutional-dashboard, settings, beta, DS vs UI imports.
3. **Parallel surface audits** (marketing/auth/shell + analytical workspaces) with path-cited evidence.
4. **Ontology cross-check** against REP-002 Books 04–07 labels vs live FieldRow/section titles.
5. **Trust ladder checklist** applied to every analytical surface (not just flagship reports).
6. **Fabrication hunt** — defaults, aliases, “Available/Hold/Confidence” mislabels, evidence recycled from strengths.
7. **Competitive UX benchmark** — Bloomberg, TIKR, Tickertape, Trendlyne, Screener, Simply Wall St, Morningstar (UX/product experience only).
8. **Visual QA** — not re-executed in this pass; prior environment blockage treated as **open FAIL condition** for production (no screenshot proof).
9. **No feature implementation** — documentation-only certification.

---

## 3. Overall Product Score (/10)

| Dimension | Score | Notes |
|---|---|---|
| Professionalism | 5.5 | Calm institutional voice; engineer leakage (API paths, ontology IDs) |
| Trust | 3.8 | Thin-client honesty undermined by BQ aliasing + auth theatre |
| Visual quality | 6.4 | Tokens + typography coherent; hero lacks product proof |
| Modern design | 6.0 | DS/cmdk current; dual stacks + cream/serif marketing risk |
| Navigation | 5.0 | Clean primary sidebar; AUX palette = second product |
| Consistency (one app) | 4.0 | Four research skins, uneven trust chrome |
| Accessibility | 5.5 | Some strong patterns; no automated gate |
| Performance UX | 5.5 | Real lazy on CA/Reports; fake lazy on Portfolio |
| Error/empty honesty | 6.0 | Strong empties; weak typed errors on some intel paths |
| Commercial readiness | 2.5 | Illustrative pricing, unpublished contacts, fake signup |
| **Weighted overall** | **4.8** | **Below institutional ship bar (≥7.5 required)** |

Ship bar for this audit: **≥7.5 overall** and **zero CRITICAL** open. Neither met.

---

## 4. Screen-by-Screen Review

### 4.1 Marketing Website

| Aspect | Assessment |
|---|---|
| First impression | Premium *tone*; gradient-only hero — no product UI proof |
| Trust | Pricing disclosure good; Contact + JSON-LD + “sketch” copy bad |
| Navigation | Duplicate Sign in / Enter platform; jargon in body |
| Decision | **FAIL for commercial launch** |

Key paths: `apps/web/src/components/marketing/MarketingLanding.tsx`, `(marketing)/pricing`, `(marketing)/contact`, `lib/commercial/editions.ts`.

### 4.2 Authentication

| Screen | Assessment |
|---|---|
| Login | Functional path; exposes `POST /api/v1/auth/rbac/login` in UI — unprofessional |
| Signup | UI-only `setTimeout`; collects password never stored — **trust anti-pattern** |
| Forgot / Reset / Verify | Theatre success states |
| Session expired / 403 / 401 pages | Comparatively clear |
| Decision | **FAIL for self-serve / commercial onboarding** |

### 4.3 Executive Dashboard (`/dashboard`)

| Aspect | Assessment |
|---|---|
| Research Mode | Banner present — good |
| Trust ladder | **Missing** full Facts→…→Recommendation |
| Widgets | Many permanent “Data unavailable.” / empty insight widgets — looks unfinished |
| Decision | **PASS WITH CONDITIONS** as orientation shell only; **FAIL** as analytical product |

### 4.4 Company Analysis (`/analysis`)

| Aspect | Assessment |
|---|---|
| Flagship chrome | Strong three-pane workspace, lazy sections, TrustLadderCard on summary |
| Ontology | **CRITICAL FAIL** — `QualitySection` aliases non-BQ stages into BQ dimension labels |
| Defaults | Silent **AAPL** analyse — implies coverage |
| Decision | **FAIL** until aliasing removed |

Evidence (`WorkspaceSections.tsx`):

- Capital Allocation Quality ← `view.management.label`
- Reinvestment Opportunity ← `view.growth.label` / `.decision`
- Operating Discipline ← `view.earnings.label`
- Industry Structure ← `view.moat.decision`
- Franchise Durability ← `view.moat.label`

Institutional Reports refuses this aliasing. Same product, opposite honesty.

### 4.5 Portfolio Intelligence (`/portfolio`)

| Aspect | Assessment |
|---|---|
| Empties | Many honest “Data unavailable.” panels |
| Labels | “Portfolio Health”, “Research Confidence”, “Quality Compounders” overclaim session flags |
| Trust ladder | Not full ladder |
| Performance | Cosmetic `lazy()` over already-imported modules |
| Decision | **FAIL** as institutional portfolio product |

### 4.6 Research Reports (`/research/institutional`)

| Aspect | Assessment |
|---|---|
| Trust ladder | Present and largely correct |
| Ontology | Better metric sourcing than Company Analysis |
| Residual | “Unavailable” string leaks; local cache vs server archive clarity |
| Decision | **PASS WITH CONDITIONS** (best analytical surface) |

### 4.7 Research Workspace (`/research`)

| Aspect | Assessment |
|---|---|
| Purpose | Library / session history — useful |
| Trust | No full ladder; Research Mode banner weak/missing |
| Decision | **FAIL** against “every analytical page” bar; OK as library if scoped |

### 4.8 Institutional Dashboard / IRD (`/research/institutional/dashboard`)

| Aspect | Assessment |
|---|---|
| Field badges | Stronger provenance than flagship FieldRow |
| Ladder | Deferred to Reports — fails on-surface requirement |
| DS | Still imports `components/ui` |
| Decision | **FAIL on-surface**; demote or fold into Reports |

### 4.9 Navigation / Global / Theme

| Aspect | Assessment |
|---|---|
| Sidebar | RBAC-filtered primary IA — good |
| Command palette | `searchableRoutes()` **not** RBAC-filtered — exposes Admin/AUX |
| Breadcrumbs | Present |
| Theme | Light/Dark via settings; marketing theme control incomplete for System |
| Decision | **PASS WITH CONDITIONS** (C-NAV / a11y) |

---

## 5. Design System Review

| Gate | Result |
|---|---|
| Typography (display/body tokens) | Pass on flagship / marketing |
| Color / themes | Pass — teal/slate variables |
| Spacing / radius / elevation | Pass with residual one-off utilities |
| DS adoption | **Fail completeness** — IRD + many legacy/advisor/analysis paths still on `components/ui` |
| Charts / tables | Sparse; honest empties > fabricated series |
| Motion / reduced-motion | Pass patterns present |
| Visual drift | Medium — marketing hand-rolled vs app DS vs IRD legacy |

**Design score: 6.2 / 10** — foundation yes; institutional unity no.

---

## 6. Trust Review

| Requirement | Dashboard | Company Analysis | Portfolio | Research WS | Inst. Reports | IRD |
|---|---|---|---|---|---|---|
| Facts → Analysis → Inference → Recommendation | Fail | Partial (summary) | Fail | Fail | Pass | Deferred / Fail |
| Confidence | Weak | Partial | Mislabeled | Sparse | Pass | Pass |
| Evidence | Fail | Partial | Sparse | Strengths-as-proxy risk | Pass | Partial |
| Contradictory evidence | Fail | Committee section | Weak | Fail | Pass | Deferred |
| Research timestamp | Weak | Partial | Session | When loaded | Pass | Partial |
| Data freshness | Weak | Partial | Fail | Weak | Pass | Partial |
| Research Mode messaging | Banner | Badge/footer | Footnotes | Missing/weak | Badges | Banner |
| **Surface verdict** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **PASS*** | **FAIL** |

\*Reports: best-in-platform; still needs epistemic chips per field and string normalization.

**Trust score: 3.8 / 10**

---

## 7. REP-002 / Ontology Review

| Issue | Severity |
|---|---|
| Company Analysis BQ dimensions aliased from wrong stages | **CRITICAL** |
| Management vs Management Quality label drift | HIGH |
| Moat vs Economic Moat; Network Effect(s); Brand vs Brand Strength | MEDIUM |
| Risk rows sourced from financial_strength metrics (wrong book) | HIGH |
| AI Committee vs investment_committee / Committee naming | LOW–MEDIUM |
| “Recommendation” chrome vs Research Mode “no buy/sell” | HIGH (messaging conflict) |
| Product name collision: Executive / Institutional / IRD / Reports / Research Workspace | HIGH (IA) |

**Ontology score: 3.5 / 10**

---

## 8. Accessibility Review

| Check | Result |
|---|---|
| Keyboard / Ctrl+K | Pass patterns |
| Focus visible | Improved post-P9.7; residual gaps |
| Focus trap | Feedback dialog / mobile drawer better; marketing mobile nav weaker |
| ARIA / landmarks | Partial pass |
| Contrast | Token intent AA; **no axe CI** |
| Reduced motion | Present |
| Touch targets | Marketing header / DS checkbox (~16px) fail 44px |
| Forms | Auth forms structured; signup is dishonest UX |

**A11y score: 5.5 / 10**

---

## 9. Performance Review

| Area | Result |
|---|---|
| Company Analysis / Institutional Reports | Real `React.lazy` + dynamic imports — Pass |
| Dashboard widgets | Real lazy — Pass |
| Portfolio | Fake lazy over static imports — Fail |
| Research Workspace / IRD | Eager / weak split — Fail |
| Skeletons | Present on flagship workspaces |
| Bundle / Lighthouse budgets | Not published — Fail for prod |
| Layout shift | Mitigated by skeletons; unverified in field |

**Performance UX score: 5.5 / 10**

---

## 10. Competitive Benchmark (UX only)

| Competitor | What they do better | DSP relative gap |
|---|---|---|
| Bloomberg | One terminal grammar, dense live facts | Fragmented routes; many unwired panels |
| TIKR | Statements & history first | Financial history often empty by design |
| Screener | Fast company page clarity | Auto-AAPL; overloaded section nav |
| Tickertape / Trendlyne | Retail clarity + India workflows | DSP jargon + incomplete commerce |
| Simply Wall St | Visual narrative with caveats | Pretty scores without field provenance on flagship |
| Morningstar | Mature research packaging | DSP packaging still “illustrative / sketch” |

**Differentiation opportunity:** Trust ladder + explainability — only half-built on surfaces users open first.

---

## 11. Client Experience (₹50,000/year test)

| Question | Answer |
|---|---|
| Would I trust this platform? | **Not yet** — BQ aliasing + auth theatre |
| Would I recommend it? | Only as closed-beta research tooling with caveats |
| Would I pay for it? | Pilot maybe; annual desk license **no** |
| What feels unfinished? | Pricing sketch, `.example` contact, empty dashboards, four research UIs, AAPL default, fake signup |

---

## 12. Top 100 Findings

Severity key: **C** CRITICAL · **H** HIGH · **M** MEDIUM · **L** LOW · **X** COSMETIC

### CRITICAL (1–12)

| # | Sev | Finding | Evidence |
|---|---|---|---|
| 1 | C | BQ dimension labels aliased from wrong ontology stages | `company-analysis/WorkspaceSections.tsx` `QualitySection` |
| 2 | C | Trust ladder not on every analytical page | Dashboard, Portfolio, Research WS, IRD |
| 3 | C | Signup collects password with no registration API | `(auth)/signup/page.tsx` |
| 4 | C | Contact page publishes `.example` emails ignoring `channelsPublished` | `(marketing)/contact/page.tsx` vs `SUPPORT_CONTACT` |
| 5 | C | Semantic fabrication risk worse than blank cells for institutional trust | Same as #1 |
| 6 | C | Multiple research products with contradictory honesty rules | CA vs Reports vs IRD |
| 7 | C | Production Visual QA matrix not evidenced | No screenshots for ship decision |
| 8 | C | Command palette navigates routes without sidebar RBAC | `ShellCommandPalette` + `searchableRoutes()` |
| 9 | C | Reset/forgot/verify success theatre | Auth pages |
| 10 | C | “Quality Compounders” = `researchAvailable` holdings | `FlagshipSections.tsx` |
| 11 | C | Portfolio “Health / Research Confidence” from session/API status strings | Portfolio flagship summary |
| 12 | C | Commercial packaging still “Illustrative · … sketch” for ship-tomorrow claim | `MarketingLanding` / pricing |

### HIGH (13–40)

| # | Sev | Finding | Evidence |
|---|---|---|---|
| 13 | H | Strengths recycled as evidence/citations proxies | Reports/CA explainability paths |
| 14 | H | Management Governance fallbacks to stage decision | CA Flagship Management |
| 15 | H | Risk Book fields tied to financial_strength metrics | CA Risk section |
| 16 | H | Login UI leaks internal API path | `LoginForm.tsx` |
| 17 | H | Marketing FAQ claims trials summarised — FAQ has no trial items | marketing `content.ts` |
| 18 | H | JSON-LD price `"0"` vs paid illustrative tiers | marketing `page.tsx` |
| 19 | H | Feature matrix “Yes” next to demo portfolio wording | commercial editions |
| 20 | H | Silent default symbol AAPL on analysis | `CompanyAnalysisWorkspace.tsx` |
| 21 | H | AUX routes (Advisor, Screening, Copilot, Launch…) in palette but not primary IA | `AUX_ROUTES` |
| 22 | H | Flagship FieldRow lacks SourceBadge / ValueCategoryBadge | CA/Reports vs IRD |
| 23 | H | `"Unavailable"` vs mandated `Data unavailable.` | Multiple mappers |
| 24 | H | Recommendation chrome conflicts with Research Mode disclaimer | Summary cards vs `RESEARCH_DISCLAIMER` |
| 25 | H | IRD trust ladder deferred off-surface | IRD client alerts |
| 26 | H | Portfolio API errors not fully mapped to 401/403/404/timeout copy | Portfolio workspace |
| 27 | H | Empty executive insight widgets look broken, not honest | Dashboard widgets |
| 28 | H | Fake `lazy()` in Portfolio | PortfolioIntelligenceWorkspace |
| 29 | H | Research Workspace missing Research Mode banner | research-workspace |
| 30 | H | Marketing hero has no product screenshot / UI proof | MarketingLanding |
| 31 | H | “Go to dashboard” CTA for unauthenticated users | MarketingLanding |
| 32 | H | Duplicate Sign in / Enter platform CTAs | MarketingHeader |
| 33 | H | Ontology jargon on marketing (REP-002, thin client) | marketing content |
| 34 | H | Nav label “Institutional” ambiguous (Reports vs IRD) | `SHELL_NAV` |
| 35 | H | expectedLongTermQuality mirrors businessQualityLabel | ratings mapping |
| 36 | H | Earnings Quality uses growth proxies | mapInstitutionalRatings |
| 37 | H | No axe/contrast CI gate | platform |
| 38 | H | No LCP/INP production budgets published | platform |
| 39 | H | Firefox / Safari not certified | platform |
| 40 | H | Advisor / legacy analysis surfaces still in tree & searchable | AUX + pages |

### MEDIUM (41–75)

| # | Sev | Finding |
|---|---|---|
| 41 | M | Marketing theme control hides System mode |
| 42 | M | Marketing mobile nav lacks focus trap / Esc |
| 43 | M | Header controls likely &lt;44px touch targets |
| 44 | M | DS checkbox ~16×16 |
| 45 | M | Collapsed sidebar uses text chevrons not icons |
| 46 | M | Topbar search affordances overlapping (3 patterns) |
| 47 | M | Breadcrumb depth inconsistent on ticker deep links |
| 48 | M | Settings vs Profile split unclear |
| 49 | M | Beta banner / disclaimer stacking density |
| 50 | M | StatusBar density low-value for PM personas |
| 51 | M | Print/PDF modes of Reports under-tested visually |
| 52 | M | Local report cache age vs server archive weak |
| 53 | M | Dashboard customize panel cognitive load |
| 54 | M | Tasks widget = hardcoded links |
| 55 | M | Demo “add AAPL to watchlist” patterns |
| 56 | M | 10px disclaimer footers as primary compliance |
| 57 | M | Star glyphs for unavailable ratings |
| 58 | M | Shortcut help strings differ across workspaces |
| 59 | M | Panel collapse below `lg` can hide section nav |
| 60 | M | Landscape tablet not screenshot-verified |
| 61 | M | Dark mode residual border/contrast drift on IRD |
| 62 | M | Marketing long-scroll manifesto length |
| 63 | M | About/FAQ thin reuse |
| 64 | M | Pricing seats “sketch” language |
| 65 | M | Support unpublished note inconsistently applied |
| 66 | M | Session-expired → dashboard path assumptions |
| 67 | M | ProtectedRoute coverage uneven across AUX |
| 68 | M | Intelligence/Companies/Screening visual orphan risk |
| 69 | M | Copilot UX not in primary nav but searchable |
| 70 | M | Reports `/reports` vs `/research/institutional` naming clash |
| 71 | M | Research Mode badge vs alert vs footer inconsistency |
| 72 | M | TrustLadder static chrome not per-value categories |
| 73 | M | Minority opinions / contradictory lists empty often without guidance |
| 74 | M | Export bar promises vs thin-client limits |
| 75 | M | Skeleton quality uneven (IRD spinner-only) |

### LOW (76–90)

| # | Sev | Finding |
|---|---|---|
| 76 | L | Monospace API crumbs in footers |
| 77 | L | “Research ladder” vs “Trust Ladder” naming |
| 78 | L | Mixed icon density (Lucide sparse vs text-first) |
| 79 | L | Scrollbar styling inconsistent across panes |
| 80 | L | Hover transition durations differ |
| 81 | L | Card padding rhythm drifts between workspaces |
| 82 | L | Table density not standardized |
| 83 | L | Chart container empty states uneven |
| 84 | L | Focus ring color vs accent soft collision |
| 85 | L | Loading copy verbosity |
| 86 | L | Orphaned AnalysisClient still in tree |
| 87 | L | Docs routes vs Documentation vs /docs split |
| 88 | L | Health/Diagnostics in palette for end users |
| 89 | L | Preference persistence edge cases undocumented in UI |
| 90 | L | Keyboard shortcut collisions undocumented |

### COSMETIC (91–100)

| # | Sev | Finding |
|---|---|---|
| 91 | X | Gradient hero wash without imagery |
| 92 | X | Cream/serif marketing adjacency to common AI templates |
| 93 | X | Badge overuse on Research Mode |
| 94 | X | Section eyebrow casing inconsistency |
| 95 | X | Link underline styles differ marketing vs app |
| 96 | X | Empty state illustration absence (text-only) |
| 97 | X | Favicon / brand mark weight in shell |
| 98 | X | Footer link order polish |
| 99 | X | Tooltip delay inconsistency |
| 100 | X | Print stylesheet residual margins |

---

## 13. Improvement Opportunities

### Quick Wins (days)

1. Stop BQ stage aliasing — show `Data unavailable.` unless true BQ metrics exist (match Reports).
2. Gate Contact emails on `channelsPublished`; remove `.example` mailto when false.
3. Remove password fields from signup theatre OR clearly make it “email-only access request” with no password.
4. Strip API path from login footer; remove “sketch” from customer-facing pricing strings (keep Illustrative).
5. Fix JSON-LD price honesty.
6. Remove silent AAPL default — require explicit symbol.
7. Rename Portfolio Health / Quality Compounders / Research Confidence to coverage facts.
8. RBAC-filter command palette routes.
9. Add Research Mode banner to Research Workspace + compact ladder to Dashboard/Portfolio summaries.

### Medium Improvements (1–2 sprints)

1. Collapse IA: one company research surface; demote IRD; hide AUX from palette or RBAC-lock.
2. Shared trust chrome kit (banner + ladder + contradictory + freshness) mandatory.
3. Epistemic chips on FieldRow across CA + Reports.
4. Real code-splitting for Portfolio / Research WS; kill fake lazy.
5. Typed error maps everywhere (401/403/404/500/timeout/network/coverage).
6. axe CI + Lighthouse budgets.
7. Complete Visual QA screenshot matrix Light/Dark × Desktop/Tablet/Mobile.
8. Finish DS migration off `components/ui` for IRD.

### Future Enhancements

1. Live product hero (authenticated demo or scrubbed UI capture).
2. Real self-serve auth when API exists — delete theatre pages.
3. Portfolio market-value weights when feeds exist (no client math).
4. India-native clarity pass (Screener-level company page speed).

### Version 2 Ideas

1. Bloomberg-dense quote strip without tip-app chrome.
2. Single “Research Object” timeline across Analysis → Reports → Archive.
3. Advisor collaboration product properly productized or removed from palette.
4. Competitive statement browser (TIKR-class) as separate epic — not fake panels.

---

## 14. Recommended Fix Order

1. **CRITICAL ontology honesty** — Company Analysis `QualitySection` + Risk/Management fallbacks.
2. **CRITICAL commerce/auth honesty** — Contact gate, signup/reset theatre, pricing/JSON-LD.
3. **CRITICAL trust universality** — shared ladder kit on Dashboard, Portfolio, Research WS, IRD.
4. **CRITICAL security UX** — RBAC command palette.
5. **HIGH IA collapse** — one flagship research path; hide orphans.
6. **HIGH portfolio language** — Health/Compounders/Confidence rename.
7. **HIGH defaults** — no silent AAPL.
8. **MEDIUM performance / DS / a11y CI**.
9. **Visual QA matrix** before any public launch claim.
10. **Browser matrix** (Firefox/Safari).

---

## 15. Certification Decision

### **FAIL**

**Rationale (brutal):**

- A tomorrow ship to institutional clients would expose semantic fabrication on Business Quality, account/commerce theatre, unpublished contact channels, incomplete trust ladder coverage, and fragmented research IA.
- Institutional Reports shows the product *can* be honest and structured — that raises the bar; it does not excuse flagship Analysis aliasing.
- Prior PASS WITH CONDITIONS certifications are **insufficient** under a production-tomorrow assumption. Conditions became blockers.

**What would change the decision to PASS WITH CONDITIONS:**

- All CRITICAL (1–12) closed with regression tests.
- Visual QA matrix attached.
- Palette RBAC + Contact gate + BQ honesty verified in review.
- Remaining HIGH items scheduled with owners before public GA.

**What would change the decision to PASS:**

- Above, plus HIGH (13–40) closed or explicitly accepted with client-facing limitations documentation, axe/Lighthouse green, and dual-stack DS migration for primary paths.

**Allowed interim use (not a PASS):** closed-beta Research Mode with invited users, written limitations, and no commercial “live pricing / self-serve signup” claims.

---

## 16. References

- `docs/design/` (01–15)
- `docs/research/REP-002_Research_Ontology/`
- `docs/USER_TRUST_STANDARD.md`
- `docs/PRODUCT_CONSTITUTION.md`
- `docs/reviews/P9_PLATFORM_UX_CERTIFICATION.md` (prior — **overruled for production ship**)
- `docs/reviews/P9_4_COMPANY_WORKSPACE_UX_CERTIFICATION.md`
- Primary code: `apps/web/src/components/{marketing,layout,dashboard,company-analysis,portfolio-intelligence,research-workspace,institutional-reports,institutional-dashboard,ds,auth,beta}/`
- Shell: `apps/web/src/lib/shell/navigationRegistry.ts`

---

## 17. Audit Integrity Statement

This review was performed as an independent adversarial certification. Findings cite concrete paths. No screenshots were fabricated. No backend/engine changes were made. This document is the sole deliverable of the RC-2 audit task.
