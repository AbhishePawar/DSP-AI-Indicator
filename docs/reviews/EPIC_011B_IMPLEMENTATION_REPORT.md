# EPIC-011B — Institutional Research Intelligence & Validation Platform

| Field | Value |
|---|---|
| Programme | EPIC-011B · Research Intelligence & Validation (v1.1) |
| Mode | **Implementation** (measurement vertical slice) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Date | 2026-08-02 |
| Decision | **PASS** for research measurement platform foundation (documented gaps remain) |

---

## 1. Executive Summary

EPIC-011B adds an additive **Research Intelligence** subsystem that **measures and validates research quality over time** without changing research engines. Completed analyses can be captured as immutable snapshots; historical windows (3/6/12/24/36 months), outcome measurement, confidence calibration, performance dashboards, and intelligence insights are exposed via new `/api/v1/research/intelligence/*` endpoints and a supporting web workspace under Research.

No valuation, business quality, management, moat, risk, AI committee, explainability, REP-002, trust/governance, or existing recommendation logic was modified. Thin-client rules and CV-001 honesty are preserved.

---

## 2. Research Intelligence Features

| Feature | Status |
|---|---|
| Immutable Research Snapshot Registry | Implemented (InMemory + DatabasePort adapter) |
| Historical tracking (append-only, 3–36m windows) | Implemented |
| Outcome Engine (measure only) | Implemented |
| Confidence Calibration | Implemented |
| Performance Dashboard API + UI | Implemented |
| Research Timeline UI | Implemented |
| Calibration Reports UI | Implemented |
| Research Intelligence insights | Implemented |
| Auto-capture after `/analyse` | Best-effort hook (opt-out via `DSP_RI_AUTO_CAPTURE=0`) |
| Feature flag | `NEXT_PUBLIC_RESEARCH_INTELLIGENCE` / `researchIntelligence` |

---

## 3. Snapshot Registry

**Package:** `packages/dsp_platform/src/dsp_platform/research_intelligence/`

Immutable fields captured: Research ID, Company, Exchange, Sector, Industry, Timestamp, Recommendation, Confidence (+ label), IV, Price, MoS, BQ/Mgmt/Moat/Risk scores, AI Committee Decision, Explainability Summary, Evidence refs, Source Confidence, Research Version, Model Version, content SHA-256.

- Store protocol: `ResearchSnapshotStore`
- Adapters: `InMemoryResearchSnapshotStore` (default/tests), `DatabaseResearchSnapshotStore` (EPIC-011A `DatabasePort`, Postgres when configured + `DSP_RI_USE_DATABASE=1` or Postgres adapter)
- Overwrite forbidden (`SnapshotAlreadyExistsError`)
- Capture seam: post-`compose_intelligence` in composition router + explicit `POST /research/intelligence/snapshots`

---

## 4. Historical Tracking

- Append-only registry — never mutates prior snapshots
- Timeline API projects recommendation/confidence/version evolution
- Window support: **3 / 6 / 12 / 24 / 36** months
- List/filter by symbol or company with offset/limit pagination

---

## 5. Calibration Engine

From measured outcomes only:

- High / Medium / Low bucket accuracy
- Calibration curve (expected vs observed + gap)
- Drift status (`stable` / `watch` / `drifting` / `unavailable`)
- Reliability (overall accuracy, coverage ratio, Brier proxy)

Missing horizon market data → **Data unavailable.** Incomplete calculable inputs → **Unable to calculate.**

---

## 6. Dashboard

**UI route:** `/research/intelligence` (child under Research Workspace; RBAC `read_research`; gated by feature flag)

Sections: Performance · Timeline · Calibration · Intelligence

Metrics surfaced from API only: Overall Accuracy, Rec Accuracy, IV Error, Avg MoS, Calibration summary, Bull/Bear success, FP/FN, Holding Horizon, Coverage, Trends (lazy SVG chart). Empty / loading / error / skeleton states; light/dark via DS tokens; reduced-motion respectful transitions; responsive left/right panels.

---

## 7. Validation Results

| Suite | Result |
|---|---|
| `packages/dsp_platform/tests/test_research_intelligence.py` | Unit: immutability, outcome math fixtures, calibration/dashboard, honest unavailable |
| `packages/api_platform/tests/test_research_intelligence_api.py` | API contract for schema/capture/timeline/outcomes/calibration/performance |
| Frontend `research-intelligence.test.tsx` | Presentation helpers (no fabricated metrics) |
| Analytical engines | Untouched by design |

---

## 8. Remaining Gaps

1. **Full multi-year market history feeds** — not wired; callers must supply `horizon_prices` for measurable outcomes. Without prices, outcomes remain **Data unavailable.**
2. **Postgres durability** — adapter exists behind `DatabasePort`; default process registry remains InMemory unless Postgres + opt-in env. Schema is additive JSON payload table — production migration/ops runbook still needed.
3. **Auto-capture payload richness** — depends on public composition DTO field coverage; sparse pipelines yield partial snapshots with honest nulls.
4. **Virtualized timeline** — incremental list with limit/offset; full virtualization library not introduced.
5. Additive research routers from prior epics remain unregistered in `create_app` (pre-existing); only EPIC-011B router was added to the live factory list.

---

## 9. Architecture Impact

| Area | Impact |
|---|---|
| Analytical engines | **None** |
| Recommendation logic | **None** |
| Frozen `/api/v1` analyse contracts | **Preserved** (capture is best-effort side effect; failures swallowed) |
| New APIs | Additive `/api/v1/research/intelligence/*` |
| Thin client | Consumes measurement APIs only |
| CV-001 | Enforced — no fabricated outcomes |

---

## 10. Components Added

### Backend
- `dsp_platform/research_intelligence/*` (models, store, capture, outcomes, calibration, dashboard, insights, service, registry)
- `dsp_platform/research_intelligence_facade.py`
- `DSPPlatform` research intelligence methods
- `api_platform/api/routers/research_intelligence.py`
- Composition post-complete capture hook

### Frontend
- `apps/web/src/app/research/intelligence/page.tsx`
- `apps/web/src/components/research-intelligence/*`
- `apps/web/src/lib/research-intelligence/*`
- API client methods + nav child + feature flag

### Docs / Tests
- This report
- Unit + API + light frontend tests

---

## 11. Pages Updated

- Navigation registry: Research → Research Intelligence child
- `.env.example`: `NEXT_PUBLIC_RESEARCH_INTELLIGENCE`

---

## 12. Feature Flags Used

| Flag | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_RESEARCH_INTELLIGENCE` | `true` | Presentation/nav/workspace gate |
| `DSP_RI_AUTO_CAPTURE` | `1` | Server auto-capture after `/analyse` |
| `DSP_RI_USE_DATABASE` | `0` | Force DatabasePort store when non-Postgres |
| `DSP_RI_FORCE_MEMORY` | unset | Keep InMemory even if DB present |

---

## 13. Accessibility / Performance / Responsive

- Section nav with `aria-current`, region labels, keyboard-reachable controls
- Skeletons with `aria-busy`; error/empty honest copy
- `motion-reduce:transition-none` on interactive transitions
- Lazy/code-split sections + chart; route-level `next/dynamic`
- Desktop / tablet / mobile panel collapse via existing a11y helper

---

## 14. Known Limitations

See §8 Remaining Gaps. Outcome measurement is intentionally honest when market horizons are absent.

---

## 15. Future Enhancements

- Production Postgres migration + ops runbook for `research_intelligence_snapshots`
- Authenticated historical price provider adapter for automatic horizon fills (still no fabrication)
- Virtualized timeline for large registries
- Exportable calibration PDF aligned with institutional report export (R003) — citations only

---

## 16. Regression Summary

- Analytical behaviour: **unchanged**
- Existing recommendation / valuation paths: **unchanged**
- New surface is pure consumer / measurement

---

## 17. Key Paths

| Kind | Path |
|---|---|
| Schema | `GET /api/v1/research/intelligence/schema` |
| Capture | `POST /api/v1/research/intelligence/snapshots` |
| List | `GET /api/v1/research/intelligence/snapshots` |
| Timeline | `GET /api/v1/research/intelligence/timeline` |
| Outcomes | `POST /api/v1/research/intelligence/outcomes` |
| Calibration | `POST /api/v1/research/intelligence/calibration` |
| Performance | `GET|POST /api/v1/research/intelligence/performance` |
| Insights | `GET|POST /api/v1/research/intelligence/insights` |
| UI | `/research/intelligence` |
| Report | `docs/reviews/EPIC_011B_IMPLEMENTATION_REPORT.md` |
