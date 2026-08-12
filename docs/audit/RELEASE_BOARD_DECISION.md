# RELEASE BOARD DECISION — EPIC-018

| Field | Value |
|---|---|
| Board | Commercial General Availability Release Board |
| Product | DSP AI Indicator |
| Version | **2.0.0-rc.1** (Version 2.0 RC) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip evaluated | `389d9b1703e3f1202c83447a900bed14ce27a287` (+ EPIC-018 audit docs commit) |
| Date | 2026-08-03 |
| Mode | Evidence-based certification — Architecture Freeze |
| Prior authority | GA-005 **COMMERCIAL GA REJECTED** · RC4 RC APPROVED for audit/deploy planning only |

---

## Question

Is Version 2.0 RC approved for **unrestricted Commercial General Availability**?

---

## Decision (binary — one string only)

# COMMERCIAL GA REJECTED

---

## Rationale (objective)

EPIC-016/017 materially improved identity architecture, HttpOnly/CSRF sessions, DatabasePort enterprise store wiring, deployment packaging, observability, and security packaging checks. Those advances **do not** close the CRITICAL commercial blockers required for unrestricted Commercial GA.

Open CRITICAL blockers with evidence:

1. **No purchasable packaging / live billing** — adapters return unavailable; honesty string retained.  
2. **Live IdP SSO/MFA not integrated** — ports/adapters only.  
3. **Headed Visual QA archive absent.**  
4. **Firefox + Safari physical smoke absent** (Windows host limitation unchanged).  
5. **Universal trust-ladder chrome incomplete.**  
6. **Board/governance unlock for unrestricted GA not earned** while the above remain open.

Additional HIGH residuals reinforce rejection: synthetic-only load, PARTIAL soak (not 8–24h live), no live Docker/K8s deploy on validation host, npm high advisories, CSP residuals, PITR/restore unevidenced.

Closed-beta / institutional pilot under Research Mode remains the authorized posture (unchanged from Release Board / GA-005). This decision does **not** revoke pilot readiness.

---

## Forbidden claims after this decision

- “Generally Available” / “Commercial GA” / unrestricted public sale  
- Self-serve checkout readiness  
- Four-browser physical certification  
- 8–24h soak certification  
- Production cluster load certification on this evidence pack  

## Allowed claims

- Version 2.0 **Release Candidate**  
- Closed-beta / institutional pilot (Research Mode)  
- Production-*deployable packaging improved* (EPIC-017) — not “production-certified at GA bar”  
- Architecture freeze honored through EPIC-018  

## Re-hearing gate

Re-open Commercial GA board **only** when all CRITICAL rows in `OPEN_RISK_REGISTER.md` (R-001…R-006) have evidence of closure on a new tip, plus re-run of load/soak/security field gates.

---

## Sign-off record

| Role | Position |
|---|---|
| CTO / Principal Architect | **REJECTED** |
| Principal SRE | **REJECTED** (live deploy/soak/load gaps) |
| Principal Security | **REJECTED** (IdP/billing/scan residuals) |
| QA Director | **REJECTED** (Visual QA / Firefox / Safari / trust) |
| Release Manager | **REJECTED** |

**Final board string:** `COMMERCIAL GA REJECTED`
