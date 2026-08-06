# P4.1 — Legal & Compliance Foundation

**Status:** COMPLETE  
**Frontend:** v1.6.0  
**Backend:** unchanged  
**Date:** 2026-07-28

---

## Architecture impact

| Area | Change |
|---|---|
| Analysis pipeline | None |
| Valuation engines | None |
| Recommendation engine | None |
| AI Committee | None |
| API contracts | None |
| Business logic | None |
| Frontend | Legal document pages, footer/header links, first-report disclaimer acknowledgement (localStorage) |

Thin-client rules preserved: no browser scoring, valuation, or AI reasoning. Legal content is presentation/documentation only.

---

## Document summary

| Document | Route | Repo markdown |
|---|---|---|
| Privacy Policy | `/docs/privacy` | `docs/PRIVACY_POLICY_v1.6.0.md` |
| Terms of Service | `/docs/terms` | `docs/TERMS_OF_SERVICE_v1.6.0.md` |
| Investment Research Disclaimer | `/docs/disclaimer` | `docs/INVESTMENT_RESEARCH_DISCLAIMER_v1.6.0.md` |
| Risk Disclosure | `/docs/risk-disclosure` | `docs/RISK_DISCLOSURE_v1.6.0.md` |
| Cookie Policy | `/docs/cookie-policy` | `docs/COOKIE_POLICY_v1.6.0.md` |
| Data Usage Policy | `/docs/data-usage` | `docs/DATA_USAGE_POLICY_v1.6.0.md` |

Shared source of truth for in-app pages: `apps/web/src/lib/legal/content.ts`.

Disclaimer requirements covered: research/education only; not personalised advice; investing involves risk; past performance ≠ future results; due diligence / adviser language.

Data transparency covered: sources, update frequency (where known), Unavailable handling, confidence as backend-mapped, report versioning metadata.

User rights covered: account management, access, deletion, contact, complaint process (Privacy Policy).

---

## UI integration

- **Header** (`Topbar`): Privacy / Terms / Disclaimer links (`LegalNavLinks`, lg+)
- **Footer** (`StatusBar`): same legal links + Docs index link; research-not-advice copy retained
- **Acknowledgement**: `ResearchDisclaimerGate` before first report generation in Company Analysis and Research workspaces; persisted via `dsp.researchDisclaimer.acknowledged.v1`

Components:

- `apps/web/src/components/legal/LegalNavLinks.tsx`
- `apps/web/src/components/legal/ResearchDisclaimerGate.tsx`
- `apps/web/src/components/legal/useResearchDisclaimerGate.tsx`

---

## Compliance checklist

| Check | Result |
|---|---|
| Report metadata displayed (existing workspace transparency) | PASS — unchanged presentation surfaces |
| Missing data labelled Unavailable | PASS — Data Usage Policy + existing UI honesty |
| Scores traceable to evidence | PASS — no new scoring; prior explainability/transparency intact |
| No unsupported claims in legal copy | PASS — research/education framing |
| No hidden calculations introduced | PASS — acknowledgement/storage only |
| Footer/header legal links | PASS |
| First-report disclaimer checkbox | PASS |

---

## Testing

| Area | Coverage |
|---|---|
| Legal content + routes | `apps/web/src/lib/legal/legal.test.tsx` |
| Acknowledgement flow | gate unit test + company-analysis block-until-ack |
| Links | `LegalNavLinks` href assertions |
| Version / regression | foundation, release-smoke, journeys, workspace suites → **1.6.0** |

---

## Feature flags used

None. Acknowledgement is local preference storage, not a product feature flag.

---

## Accessibility validation

- Legal nav uses `nav[aria-label="Legal"]` with clear link names
- Disclaimer dialog: titled, described, checkbox labelled, primary action disabled until checked
- Existing focus/landmarks unchanged

---

## Performance validation

- No new API calls; acknowledgement is O(1) localStorage
- Dialog mounts only when gate opens

---

## Responsive validation

- Footer links wrap with existing status bar flex layout
- Header legal links hidden below `lg` (footer remains available on mobile)

---

## Known limitations

- Contact address uses an example operator mailbox until production legal counsel substitutes a real address
- Documents are product transparency summaries; jurisdictional counsel review remains required before commercial launch in regulated markets
- Clearing browser storage resets acknowledgement (by design)

---

## Future enhancements

- Operator-configurable contact email via env
- Optional signed acknowledgement audit event on backend (out of P4.1 scope)
- Locale-specific legal packs

---

## Regression summary

Frontend foundation **1.5.0 → 1.6.0**. Backend packages unchanged. No `/api/v1` contract changes.

---

## PASS / FAIL

**PASS**
