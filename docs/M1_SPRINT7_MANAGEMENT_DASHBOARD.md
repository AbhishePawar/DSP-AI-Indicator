# Epic M1.0 Sprint M1.7 — Management Dashboard, Explainability & Buffett View

**Web:** `2.1.0` · **MIE:** `0.7.0-dashboard-buffett`

## Mission

Unified Management Intelligence Dashboard integrating all completed category engines, with a **derived Buffett View** (no independent scoring). **Overall Management Score remains disabled.**

## Modules

| File | Role |
|------|------|
| `managementDashboardModels.ts` | Dashboard · cards · panels · viz models |
| `managementDashboardBuilders.ts` | Aggregate builders · evidence dedupe · memoized snapshots |
| `managementDashboardSelectors.ts` | Pure selectors |
| `managementDashboardValidators.ts` | Overall-score / Buffett / evidence guards |
| `managementDashboardEngine.ts` | Facade · full demo |
| `buffettViewModels.ts` | Derived Buffett perspectives + commentary |

## Integrated categories

Capital Allocation · Governance · Execution · Shareholder Alignment · Strategy · Communication

Each card: category score · evidence count · confidence · risk summary · evidence links · timeline ids

## Buffett View

Perspectives (derived only):

- Capital Allocation
- Management Integrity (governance + communication)
- Operational Excellence (execution)
- Shareholder Stewardship
- Strategic Vision (strategy + communication)
- Overall Buffett Commentary (narrative only — `independentScore: null`)

## Usage

```ts
import { managementEngine, managementDashboardEngine } from "@/lib/management";

const dash = managementEngine.demoDashboard();
managementDashboardEngine.validate(dash); // ok
dash.overallManagementScore; // null
dash.buffettView.independentScore; // null
```

## Visualization models (no rendering)

Radar · Score distribution · Timeline · Evidence heatmap · Confidence distribution · Risk distribution

## Non-goals

Overall Management Score · Research/Report/Portfolio/Decision integration · Persistence · Auth · Chart rendering
