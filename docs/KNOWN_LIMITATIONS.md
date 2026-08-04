# Known Limitations — Web 2.0.0 / Platform 1.7.0

**Living channel:** P7.0 Production Infrastructure. Prior P5.2/P6.1 limitations remain unless closed below.
**P7 condition:** Live ACME/HTTPS and backup/rollback drills require an operator host with real DNS.

## P5.2 — Closed Beta / RC (ops)

- Beta invite/feedback store is **process-local** unless operators export/import snapshots (`/admin/beta/snapshot`). Multi-replica shared state is deferred.
- Screenshot **binary** uploads are not supported — screenshot notes only (trust boundary).
- In-memory API rate limiting is not safe across multiple API replicas without an edge/Redis limiter.
- Web HSTS should be terminated at the edge; API HSTS is enabled via prod compose flags.
- Live multi-tenant soak metrics must be attached by operators; automated certification does not replace customer soak exports.

## Valuation Intelligence Engine (V1.1–V1.2 · **0.2.0-discounted-cash-flow**)

- Foundation + **Discounted Cash Flow (FCFF)** category scoring enabled
- `overallValuationEnabled=false`; `valuationEngine.overallValuation()` returns `null`
- Published `DCF_METRIC_WEIGHTS` (sum = 1.0); FCFE structure only
- Deterministic forecasts, sensitivity cases, evidence-linked explainability
- Metrics/assumptions are caller-supplied (no Research Engine coupling)
- No chart rendering UI / persistence / AI opinions
- Independent of MIE, EMI, and EQI (do not cross-wire)
- See `docs/V1_SPRINT2_DCF.md`

## Earnings Quality Intelligence Engine (EQ1.1–EQ1.8 · **1.0.0 production**)

- Analytical category scoring + Overall Earnings Quality Score + Earnings Quality Dashboard
- Certified production-ready (`ProductionReady=true`, `FeatureComplete=true`, `RegressionPassed=true`)
- Earnings Persistence remains an unscored shell (excluded from overall aggregation)
- Metrics/evidence are caller-supplied (no Research Engine coupling)
- No chart rendering UI / persistence / AI opinions
- Independent of MIE and EMI (do not cross-wire)
- See `docs/EQ1_KNOWN_LIMITATIONS.md` and `docs/EQ1_PRODUCTION_READINESS.md`

## Economic Moat Intelligence Engine (M2.1–M2.8 · **1.0.0 production**)

- Analytical category scoring + Overall Moat Score + Economic Moat Dashboard
- Certified production-ready (`ProductionReady=true`, `FeatureComplete=true`)
- Distribution Advantage remains an unscored shell (excluded from overall aggregation)
- Metrics/evidence are caller-supplied (no Research Engine coupling)
- No chart rendering UI / persistence / AI opinions
- Independent of Management Intelligence Engine (do not cross-wire)
- See `docs/EMI_KNOWN_LIMITATIONS.md` and `docs/EMI_PRODUCTION_READINESS.md`

## Management Intelligence Engine (M1.1–M1.8 · production)

- Six category engines + unified dashboard + derived Buffett View + **Overall Management Score enabled**
- Published `MANAGEMENT_CATEGORY_WEIGHTS` (Buffett excluded from aggregation)
- No Research Engine coupling / persistence / auth / chart rendering UI
- No AI opinions or hidden weights
- See also `docs/M1_KNOWN_LIMITATIONS.md` and `docs/M1_PRODUCTION_READINESS.md`

## Advisor / Client Management (V2.0 Sprint 1–2)

- Advisor + client management are **demo-only** — no persistence, no CRM, no multi-user
- Client aliases are placeholders — no personal information
- Notes / documents / portfolio size bands are illustrative
- Model portfolios are not live investments or advice
- Kanban status changes are not persisted (presentation board)
- Advisor Research uses **demo envelopes** (not live API research) for organization UX
- Collection create/rename/archive is in-session only
- Model Portfolio Builder edits are session-only (not saved)
- Presentation packs are session-only; PDF/DOCX export deferred
- Client review workflow is session-only (no calendar sync)
- Team Collaboration foundation is session-only (no real-time, auth, or chat)
- Shared Research Workspace is session-only (no comments, version control, or live sync)
- Shared Portfolio Workspace is session-only (no portfolio editing, trading, or scenario recalculation)
- Team Review & Assignment is session-only (no email, notifications, or real-time sync)
- Collaboration Dashboard is presentation-only (session recovery watch: refresh clears in-memory state)
- Model portfolios are not tradable and do not sync brokers
- `NEXT_PUBLIC_ADVISOR_DEMO` must be enabled to see Advisor nav
- No authentication, billing, email, or calendar integration

## Carry-forward from 1.0.0

- Lighthouse/Web Vitals CI not yet automated in all agent environments
- PDF/DOCX export remains backend-deferred
- Portfolio Intelligence is session-demo (no broker sync) — by design
- Beta feedback/issues are device-local only
- No broker APIs, trading, tax, or alerts

## EPIC-019A — Commercial engineering (pointers)

- Canonical split: `docs/commercial/ENGINEERING_READY_CHECKLIST.md` vs `EXTERNAL_DEPLOYMENT_PREREQUISITES.md`
- CSP style `'unsafe-inline'` residual: `docs/security/CSP_REVIEW.md`
- Soak 8–24h remains an ops prerequisite: `docs/testing/SOAK_TEST_REPORT.md`
- Doc index: `docs/releases/DOC_INDEX_COMMERCIAL.md`
