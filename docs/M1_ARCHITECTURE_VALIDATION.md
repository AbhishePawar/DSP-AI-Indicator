# M1 Architecture Validation — Management Intelligence Engine

**Web:** `2.1.0` · **MIE:** `1.0.0-mie-production`

## Architecture

```
managementEngine (facade)
├── Category engines (M1.2–M1.6)
│   capitalAllocation · governance · execution
│   shareholderAlignment · strategy · communication
├── managementDashboardEngine (M1.7)
│   category cards · evidence · risks · timeline
│   methodology · limitations · viz models
│   buffettView (derived)
└── overallManagementScoreEngine (M1.8)
    MANAGEMENT_CATEGORY_WEIGHTS → Overall Score
```

## Invariants

1. Category engines never collect Research Engine data directly.
2. Overall score consumes **category outputs only** (no recompute of metric series).
3. Buffett View is **derived commentary** — `independentScore = null`, excluded from aggregation.
4. Frozen platforms remain unmodified: Decision · Research · KG · Portfolio · Risk · Valuation · Copilot · Reports · Compliance · API · Launch · Advisor.
5. All conclusions maintain `conclusionEvidenceMap` evidence links.
6. Weights are published and normalizable; no hidden overrides.

## Weight publication

| Category | Weight |
|----------|--------|
| Capital Allocation | 0.22 |
| Governance | 0.18 |
| Execution | 0.18 |
| Shareholder Alignment | 0.16 |
| Strategy | 0.14 |
| Communication | 0.12 |
| **Sum** | **1.00** |

Missing categories → renormalize effective weights over present scored categories.

## Validation result

**PASS** — architecture consistent with M1.0 mission and production enablement rules.
