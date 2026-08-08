# Known Limitations — Version 2.0 RC (`2.0.0-rc.1`)

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **2.0.0-rc.1** |
| Authority | [`RC4_RELEASE_CANDIDATE_REPORT.md`](./RC4_RELEASE_CANDIDATE_REPORT.md) |
| Posture | Release Candidate · Research Mode / institutional pilot |
| Commercial GA | **Not approved** |
| Date | 2026-08-02 |

Supersedes messaging for the **2.0 RC channel**. Historical [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) (1.0.0 pilot packet) remains valid as prior art; this file is the RC-era limitations packet.

---

## 1. Accepted RC limitations

| ID | Limitation | Guidance |
|---|---|---|
| RC-01 | **Admin-provisioned access** | Request Access does not create purchasable accounts |
| RC-02 | **No public password reset / email verification theatre** | Honesty messaging; admins recover credentials |
| RC-03 | **Pricing illustrative — not purchasable** | Null billing; **Billing unavailable.** until real provider |
| RC-04 | **In-memory enterprise store** | Process-local; not durable across replicas/restarts |
| RC-05 | **Enterprise actor foundation (`X-User-Id`)** | Production should bind to JWT subject / IdP |
| RC-06 | **Collaboration architecture only** | No realtime transport |
| RC-07 | **Honest Data unavailable.** | CV-001 / CV-005 — never fabricate |
| RC-08 | **Book 07 typed risk dimensions may be empty** | Backend-limited; UI refuses sibling aliases |
| RC-09 | **Trust ladder not universal** | Strongest on Company Analysis + Institutional Reports |
| RC-10 | **AUX / Advisor outside primary IA** | Not palette-searchable for primary journey |
| RC-11 | **Thin client** | All intelligence via `/api/v1` |
| RC-12 | **CSP practical residuals** | `unsafe-inline` / `unsafe-eval` for Next runtime |
| RC-13 | **npm advisories in Next transitive deps** | No safe non-breaking force upgrade at RC time |
| RC-14 | **Field Visual QA / Firefox+Safari / LHCI** | Documented matrices; headed/field proof still open |

---

## 2. Commercial GA blockers (still open)

Inherited from GA-005 / prior GA-C1…GA-C7 — **not closed by EPS-003**:

| # | Condition |
|---|---|
| GA-C1 | Headed Visual QA screenshot archive |
| GA-C2 | Firefox + Safari physical smoke |
| GA-C3 | Universal trust-ladder chrome |
| GA-C4 | Published field LHCI / CWV + broader a11y field evidence |
| GA-C5 | Self-serve entitlements **or** explicit invite-only commercial policy |
| GA-C6 | ~~Stale AAPL onboarding assertion~~ — **addressed in RC test hygiene** |
| GA-C7 | Release board sign-off for broader release |

Plus EPS-002 commercial work: real billing adapter, durable enterprise store, SSO/MFA, HttpOnly sessions.

---

## 3. What is *not* a bug

| Observation | Interpretation |
|---|---|
| **Billing unavailable.** | Null adapter by design |
| Empty enterprise usage counters | Honest zeros until metering wired |
| Empty risk typed rows | Honesty until risk-stage metrics exist |
| Request Access does not log in | Closed-beta / RC design |
| Commercial GA language forbidden | Governance honesty |

---

## 4. How to use

1. Attach to RC audit package and pilot desks.  
2. Reference from ops/support runbooks.  
3. Do not describe `2.0.0-rc.1` as Commercial GA.
