# 06 — Known Limitations (Honest Packet)

This guide summarizes limitations for Version **1.0.0**. Authoritative detail lives in:

- `docs/releases/KNOWN_LIMITATIONS.md` (pilot vs GA-condition split — **primary for 1.0.0**)
- `docs/KNOWN_LIMITATIONS.md` (living channel / engine & advisor residuals)
- `docs/releases/GA_CERTIFICATION_REPORT.md`

Auditors must **not** treat honest empties as defects to fill with invented numbers (CV-001).

---

## 1. Closed-beta limitations (accepted for pilot)

| ID | Limitation |
|---|---|
| CB-01 | Admin-provisioned access only — Request Access does not create accounts |
| CB-02 | No public password reset / email verification (honesty messaging) |
| CB-03 | Support contact channels may be unpublished |
| CB-04 | Pricing illustrative — not purchasable |
| CB-05 | Honest **Data unavailable.** — never fabricate |
| CB-06 | Book 07 typed risk dimensions empty until risk-stage metrics exist |
| CB-07 | Partial BQ / Management / Moat sub-metrics — no sibling-stage aliases |
| CB-08 | Trust ladder not universal (CA + Institutional Reports strongest) |
| CB-09 | AUX / Advisor outside primary IA |
| CB-10 | Research Mode messaging tension with recommendation chrome (HIGH residual) |
| CB-11 | Thin client — no browser valuation/recommendation/AI reasoning |
| CB-12 | OneDrive / local `.next` build quirks on some hosts |

---

## 2. Commercial GA blockers (outstanding)

See [`05_RELEASE_STATUS.md`](./05_RELEASE_STATUS.md) GA-C1…GA-C7. Until closed with evidence, unrestricted Commercial GA remains **REJECTED**.

---

## 3. Engine / advisor residuals (living docs)

From `docs/KNOWN_LIMITATIONS.md` (non-exhaustive):

- Valuation overall may be disabled depending on engine flags; DCF category work is caller-supplied metrics
- Some category shells remain unscored (e.g. Earnings Persistence, Distribution Advantage) and are excluded from aggregations
- Advisor / shared collaboration surfaces are largely **session/demo** — no CRM, broker sync, or durable multi-user collaboration
- PDF/DOCX export deferred; beta invite store may be process-local without snapshot ops
- In-memory API rate limiting is not multi-replica safe without edge/Redis

---

## 4. What is *not* a bug

| Observation | Interpretation |
|---|---|
| Empty risk typed rows | Honesty until metrics exist |
| “Data unavailable.” | CV-001 preferred over fabrication |
| Request Access does not log in | Closed-beta design |
| Pricing not-for-purchase | Closed-beta design |
| Trust ladder missing on some shells | Known residual — GA condition, accepted for pilot |

---

## 5. How auditors should use this

1. Attach limitations when evaluating pilot desks.
2. Escalate only true trust regressions (fabrication, theatre), not expected empties.
3. Before any external “Commercial GA” language, require Release Board re-decision.
