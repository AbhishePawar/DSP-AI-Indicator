# Institutional Research Dashboard Architecture (EPIC-W001)

| Field | Value |
|---|---|
| **Status** | Implemented (frontend) |
| **Route** | `/research/institutional` |
| **Package** | `apps/web` |
| **Authority** | [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [CORE_VALUES.md](CORE_VALUES.md) · [REPORT_ARCHITECTURE.md](REPORT_ARCHITECTURE.md) |

---

## Purpose

Canonical **production** thin-client implementation of **RS-001…RS-010**.

Does **not** modify engines, scoring, APIs, models, package boundaries, or
governance law documents.

---

## Composition

```text
InstitutionalDashboardClient
  → POST /api/v1/analyse (frozen contract)
  → mapInstitutionalDashboard (presentation mapper only)
  → InstitutionalResearchDashboard
       ├─ ExecutiveHeader          (RS-001 + mandatory header)
       ├─ MarginOfSafetyPanel      (RS-005, prominent)
       ├─ MarketDataPanel          (RS-002)
       ├─ FinancialStatementsPanel (RS-003)
       ├─ ValuationPanel           (RS-004)
       ├─ BusinessQualityPanel     (RS-006)
       ├─ RiskPanel                (RS-007)
       ├─ ScenarioPanel            (RS-008)
       ├─ ExplainabilityPanel      (RS-009)
       └─ AuditPanel               (RS-010)
```

Each section is independently renderable.

---

## Data rules (CV-001)

| Situation | Display |
|---|---|
| Missing authenticated market quote | **Data unavailable.** |
| Missing calculated output | **Unable to calculate.** |
| User-submitted statement / signal inputs | Shown with **User Input** source chip |
| Never | Dummy / placeholder / estimated exchange quotes |

Authenticated market feed is **not** on the frozen analyse contract today —
RS-002 panel remains honest and empty of invented quotes.

---

## Key paths

| Path | Role |
|---|---|
| `src/app/research/institutional/page.tsx` | Route |
| `src/components/institutional-dashboard/*` | UI modules |
| `src/lib/institutional-dashboard/*` | Types, mapper, RS validation |

---

## Testing

```bash
cd apps/web && npm test -- institutional-dashboard
```

---

## Related

[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [RESEARCH_REPORT_SPECIFICATION.md](RESEARCH_REPORT_SPECIFICATION.md) · [FRONTEND_INTELLIGENCE_WORKSPACE.md](FRONTEND_INTELLIGENCE_WORKSPACE.md)
