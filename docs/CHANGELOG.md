# Changelog

## [2.2.0] — 2026-07-23 — Epic M2.0 Economic Moat Intelligence Engine

### Sprint M2.3 — Network Effects & Switching Costs Intelligence
- Network Effects category scoring (12 metrics · published `NETWORK_EFFECTS_METRIC_WEIGHTS`)
- Switching Costs category scoring (10 metrics · published `SWITCHING_COSTS_METRIC_WEIGHTS`)
- Ecosystem / churn / migration risk flags · evidence-linked explainability
- Overall Moat Score remains disabled

### Sprint M2.2 — Brand Strength Intelligence
- Brand Strength category scoring (15 metrics · published `BRAND_STRENGTH_METRIC_WEIGHTS`)
- Brand risk flags · evidence-linked explainability · merge into MoatAnalysis
- `BrandStrengthEngine` / `BrandStrengthScoringEngine` — Overall Moat Score remains disabled

### Sprint M2.1 — Economic Moat Intelligence Foundation
- New independent `apps/web/src/lib/moat/` foundation (types · evidence · timeline · risk · builders · selectors · validators · utilities · view models · engine)
- 12 category shells prepared — **no scoring**, **no Overall Moat Score**, **no dashboard UI**
- Evidence indexing · timeline lanes · risk framework · ARIA-ready view models
- Does not modify Decision, Research, KG, Portfolio, Risk, Valuation, MIE, Copilot, Reports, Compliance, API contracts, Launch Dashboard, or Advisor Platform

## [2.1.0] — 2026-07-22 — Epic M1.0 Management Intelligence Engine

### Sprint M1.8 — Production Validation & Overall Management Score Enablement
- Overall Management Score enabled via published `MANAGEMENT_CATEGORY_WEIGHTS` (six categories)
- Aggregation: configurable weights · renormalization · confidence propagation · rating bands
- `overallManagementScoreEngine` · dashboard integration · performance helpers
- Production docs: `M1_PRODUCTION_READINESS.md` · architecture · regression · limitations · M1 changelog
- `finalScoringEnabled=true` on MIE facade; Buffett View remains derived-only

### Sprint M1.7 — Management Dashboard, Explainability & Buffett View
- Unified Management Dashboard aggregating all six category engines
- Category cards · evidence explorer · confidence / risk / methodology / limitations panels · timeline · trace viewer
- Derived Buffett View (perspectives + commentary) — no independent Buffett scoring
- Presentation-only visualization models (radar · distributions · heatmap · timeline)
- Overall Management Score remains disabled (`finalScoringEnabled=false`)

### Sprint M1.6 — Strategic Vision & Communication Intelligence
- Strategy category scoring (`strategic_clarity`) — vision · roadmap · innovation · expansion · M&A · execution consistency
- Communication category scoring — letters · calls · disclosure · guidance · forecast · ESG · consistency
- Combined Strategic Vision & Communication score (two-category blend only — not Overall Management Score)
- `StrategyEngine` / `CommunicationEngine` / scoring engines — overall Management Score remains disabled
- StrategyTimeline · CommunicationTimeline · risk flags · evidence-linked explainability

### Sprint M1.5 — Shareholder Alignment & Capital Stewardship Intelligence
- Shareholder Alignment category scoring (ownership · dilution · dividends · buybacks · compensation metrics)
- Capital stewardship event analysis · alignment risk flags · explainability with evidence traceability
- `ShareholderAlignmentEngine` / `ShareholderAlignmentScoringEngine` — overall Management Score remains disabled
- Maps to MIE category `ownership_alignment`; demo fixture for validation (synthetic — not company opinions)

### Sprint M1.4 — Execution & Operational Excellence Intelligence
- Execution category scoring (revenue · margins · cash · working capital · capital efficiency metrics)
- Operational event analysis · execution risk flags · explainability with evidence traceability
- `ExecutionEngine` / `ExecutionScoringEngine` — overall Management Score remains disabled
- Demo fixture for validation (synthetic series — not company opinions)

### Sprint M1.3 — Governance Intelligence
- Governance category scoring (board · committees · auditor · promoter · regulatory metrics)
- Governance event analysis · risk flags · explainability with evidence traceability
- `GovernanceEngine` / `GovernanceScoringEngine` — overall Management Score remains disabled

### Sprint M1.2 — Capital Allocation Intelligence
- Capital Allocation category scoring (metrics · evidence · confidence · category score)
- Deployment classification · risk flags · explainability summaries with evidence traceability
- `CapitalAllocationEngine` / `CapitalAllocationScoringEngine` — overall Management Score remains disabled
- Demo fixture for validation (synthetic series — not company opinions)

### Sprint M1.1 — MIE Foundation
- New `apps/web/src/lib/management/` architecture (types, evidence, scoring shells, timeline, risk, view models)
- `ManagementScoringEngine` supports weights / incomplete / missing data — **no final scores**
- Immutable builders, selectors, validators, formatters; ARIA-ready view-model metadata
- Does not modify Decision, Research, KG, Portfolio, Risk, Valuation, Copilot, Reports, Compliance, API contracts, Launch Dashboard, or Advisor Platform

## [2.0.0] — 2026-07-22 — Epic V2.0 Advisor Platform

### Pre-implementation gate (Web 2.1.0 / M1.0)
- Advisor Platform readiness · architecture · cross-module validation reports (`docs/WEB_2_0_*.md`)
- Assignments nav aligned to Assignment Board; regression remains GREEN

### Sprint 7.5 — Collaboration Dashboard & Production Validation
- Unified Collaboration Dashboard (workspace health · team metrics · activity overview)
- Cross-workspace navigation preserving in-memory session state
- Production / Performance / Accessibility / Advisor Platform readiness panels
- Lazy `/advisor/team/dashboard` + `/advisor/team/validation` routes
- **Team Collaboration EPIC (7.1–7.5) complete**

### Sprint 7.4 — Team Review & Assignment
- Shared Review Workspace lanes (Pending · Assigned · In Progress · Ready · Completed · Archived)
- Assignment Board with drag-and-drop + keyboard column move · owner/priority badges
- Session discussion panel · activity timeline · progress & readiness metrics
- Filters (owner · priority · client · status · meeting · portfolio · research/presentation)
- Lazy `/advisor/team/shared-reviews/*` routes

### Sprint 7.3 — Shared Portfolio Collaboration
- Shared Portfolio Library with filters (risk · strategy · sector · market cap · allocation · flags)
- Compare 2–5 model portfolios reusing existing allocation / sector / risk / notes fields
- Scenario review cards (Conservative · Base · Bull · Bear · Stress) — presentation framings only
- Session discussion panel · activity feed · overview dashboard
- Lazy `/advisor/team/shared-portfolios/*` routes

### Sprint 7.2 — Shared Research Workspace
- Shared Research Library with filters (sector · industry · market cap · rating · risk · valuation · flags)
- Session collections (create / rename / delete / move / favorite)
- Compare 2–5 companies reusing existing envelope fields (never regenerated)
- Bookmarks · pins · favorites · activity feed · overview dashboard
- Lazy `/advisor/team/shared-research/*` routes

### Sprint 7.1 — Team Collaboration Foundation
- Collaboration shell: TeamWorkspace · CollaborationLayout · TeamHeader · TeamSidebar · WorkspaceContainer
- Navigation: My Work · Shared Research/Reviews/Portfolios · Discussions · Assignments · Activity
- Overview cards + session state (pins, filters, recent nav, panel width) — in-memory only
- Lazy `/advisor/team/*` routes · memoized workspace cards · responsive / collapsible sidebar

### Sprint 6 — Client Review Workflow
- Review workspace lanes + active review (checklist, timeline, prep, summary, actions)
- Workflow dashboard · review templates
- Session-only guided process over existing research / portfolios / presentations

### Sprint 5 — Advisor Reporting & Client Presentation
- Presentation workspace (create / duplicate / rename / archive — session)
- Builder with section reorder + visibility · multi-mode preview
- Research & portfolio sections reuse demo DSP envelopes / models
- Export prep: Markdown/HTML via existing download helper · PDF/DOCX placeholders

### Sprint 4 — Model Portfolio Manager
- Model Portfolio Library + session Portfolio Builder (allocation % · 100% warn)
- Holding details from demo DSP envelopes · Portfolio review card
- Scenario comparison · Templates · Portfolio notes

### Sprint 3 — Advisor Research Workspace
- Research Library with unified search
- Collections (Growth → Custom) with create / rename / archive (session)
- Compare workspace (2–5 demo envelopes)
- Research notes, timeline, bookmarks, Quick Review cards
- Client Directory with search, filters, and sort
- Expanded client profile + dashboard cards
- Meeting timeline (upcoming / completed / cancelled)
- Kanban task board (todo / in progress / waiting / done)
- Notes + research history timelines (demo)

### Sprint 1 — Advisor Platform Foundation
- Optional Advisor workspace (`/advisor/*`) — demo-only domain foundation
- `lib/advisor/` types, models, view-models, workspace facade
- Clients, Meetings, Tasks, Research collections, Model portfolios (demo)
- Nav entry gated by `NEXT_PUBLIC_ADVISOR_DEMO` (default off)

### Notes
- Does not modify Decision Engine, Research, KG, Copilot, Portfolio Engine, Reports, Valuation, Compliance, Research Mode, API contracts, Feature Flags, or Launch Dashboard
- Single-user experience unchanged when demo mode is disabled
- No persistence / no PII

## [1.0.0] — 2026-07-22 — Phase C Public Launch

### Added
- Launch Dashboard (`/launch`) — deployment status, build ID, quality gates, release health
- Post-launch report (`/launch/report`)
- Documentation hub (`/docs`) with User/Admin/Architecture/Methodology/Legal summaries
- `VERSION_MANIFEST.json` + version freeze docs

### Changed
- Web version stamp to **1.0.0** (promoted from RC 0.9.5)
- CSP **enforced** (was Report-Only through 0.9.5)
- `productionBrowserSourceMaps=false`; compress explicit

### Notes
- No Decision Engine / Research / KG / Copilot / Portfolio / Reports / Valuation / Compliance / API / Research Mode / Feature Flag changes
- Quality gates: Critical 0 · Regression PASS · A11y PASS · Perf PASS · Security PASS

## [0.9.5] — 2026-07-22 — Phase B2 Sprint 11 RC Stabilization

### Added
- ReleaseCandidateDashboard with RC score + recommendation
- IssueResolutionCard (Before → After → Verification)
- QualityTrendCard · VersionManifestCard · ReleaseSummaryCard
- Accessibility & cross-browser validation matrices
- SuccessState · WindowedList · dsp-interactive / page-enter polish

### Changed
- Web version stamp to 0.9.5
- ContentArea spacing rhythm; Button min-height touch targets
- `/beta/rc` expanded into full RC stabilization workspace

### Notes
- No Decision Engine / Research / KG / Portfolio / Copilot / Compliance / API / Feature Flag changes
- Ready for Web 1.0.0 soak pending CSP enforcement & empty critical queue

## [0.9.0] — 2026-07-22 — Phase B1 Sprint 10 Private Beta & Feedback

### Added
- `/beta` dashboard, feedback workspace, `/beta/issues`, `/beta/rc`
- Floating feedback + onboarding walkthrough
- Local analytics placeholders
- Issue tracker with status workflow
- Release candidate Go / No-Go card

### Security / Trust
- Feedback redacts tokens/JWTs; stores path only — never research or portfolio payloads

### Notes
- No Decision Engine / Portfolio / Copilot / KG / Compliance / API contract changes

## [0.8.0] — 2026-07-22 — P1.0 Sprint 9 Production Readiness

### Added
- Launch Readiness dashboard (`/launch`) with overall score and quality gates
- Performance Workspace with client Web Vitals sampling + audit notes
- Health/Build observability workspace and QA checklists
- Global/Section error boundaries, Offline banner, Session recovery, 404/500/maintenance pages
- CSP Report-Only headers and security hardening helpers
- Reduced motion + high contrast CSS

### Changed
- Web version stamp to 0.8.0
- Root layout reliability shell

### Security
- Download filename sanitization for exports
- `safeText` helpers for HTML escape / plain text / href checks

### Notes
- No Decision Engine, Research, KG, Copilot, Portfolio, Valuation, Compliance, or Feature Flag logic changes

## [0.7.0] — L1.2 Sprint 8 Portfolio Intelligence
## [0.6.0] — L1.2 Sprint 7 Reports & Export
## [0.5.0] — L1.2 Sprint 6 AI Research Copilot
## Prior — L1.2 Sprints 1–5 Research Platform foundation
