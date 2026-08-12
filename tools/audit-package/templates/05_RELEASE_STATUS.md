# 05 — Release Status

| Field | Value |
|---|---|
| Product version | **1.0.0** (`VERSION` → `v1.0.0`) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Board date | 2026-08-02 |
| Authority docs | `docs/releases/GA_CERTIFICATION_REPORT.md`, `RELEASE_BOARD.md`, `RC3_FINAL_CERTIFICATION_REPORT.md` |

---

## Decision snapshot (authoritative)

| Question | Answer |
|---|---|
| Closed-beta / institutional pilot UI freeze? | **APPROVED / GO** — PASS WITH CONDITIONS |
| Unrestricted Commercial public GA? | **NOT APPROVED** |
| Final commercial enum | **`COMMERCIAL GA REJECTED`** |
| Self-serve commerce / checkout? | **NOT AUTHORIZED** |
| Messaging language | **Closed-beta Research Mode** only |
| `GO_LIVE_APPROVAL.md` (full Commercial GA) | **Not generated** — approval not granted |

Production recommendation (GA Certification Report): proceed only with **closed-beta / institutional pilot** under Research Mode; do **not** tag, market, or sell Version 1.0.0 as Commercial GA.

---

## Certification stack

| Artefact | Decision |
|---|---|
| RC3 Final | PASS WITH CONDITIONS (pilot); commercial-tomorrow posture would FAIL |
| Visual QA / Screenshot | PASS WITH CONDITIONS — headed archive unavailable |
| Browser | Chrome/Edge PASS; Firefox/Safari physical smoke pending |
| Accessibility automation | PASS WITH CONDITIONS |
| Performance automation | PASS WITH CONDITIONS; field LHCI/CWV unpublished |
| GA-004 ops package | Complete for pilot; Commercial GA **NO-GO** |
| GA Certification (final) | **COMMERCIAL GA REJECTED** |

---

## Outstanding Commercial GA conditions (GA-C1…GA-C7)

Summarized from `docs/releases/KNOWN_LIMITATIONS.md` / Release Board:

1. **GA-C1** — Headed Visual QA screenshot matrix (or CI Percy/Playwright artefacts)
2. **GA-C2** — Firefox + Safari physical smoke on primary paths
3. **GA-C3** — Compact trust-ladder / Research Mode chrome on Dashboard, Portfolio, Research Workspace, IRD
4. **GA-C4** — Published LHCI / field CWV + stronger axe contrast/route coverage
5. **GA-C5** — Self-serve commercial entitlements **or** explicit invite-only commercial policy (still not “unrestricted GA” without clarity)
6. **GA-C6** — Fix stale `commercial.test.tsx` AAPL onboarding assertion
7. **GA-C7** — Client-facing limitations packet + governance sign-off for broader release

Non-negotiable: no reintroduction of auth/commerce theatre or silent demo tickers.

---

## Tag guidance

| Item | Value |
|---|---|
| Proposed tag meaning | Closed-beta institutional UI freeze |
| Do not tag / market as | Commercial GA / Public self-serve |

---

## Auditor instruction

Do **not** soften “COMMERCIAL GA REJECTED” into “almost GA.” Pilot readiness and Commercial GA are different release questions. Cite the GA Certification Report and Release Board verbatim when summarizing for stakeholders.
