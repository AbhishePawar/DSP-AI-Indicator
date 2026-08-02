# Support Runbook — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Posture | Closed-beta / institutional pilot |
| Related | [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) · [`ADMINISTRATOR_GUIDE.md`](./ADMINISTRATOR_GUIDE.md) · `docs/ops/runbooks/INCIDENT_RESPONSE.md` |
| Date | 2026-08-02 |

---

## 1. Purpose

Operational triage for pilot support: **issue classification**, **incident severity**, **escalation**, and **support expectations**. Prefer restoring the certified build over hot-patching analytical honesty under pressure.

---

## 2. Support expectations (closed beta)

| Item | Expectation |
|---|---|
| Scope | Provisioned pilot desks only — not public self-serve customers |
| Purchase / billing | Out of scope — product not purchasable |
| Account creation | Admin-handled; Request Access is not a ticket-to-account SLA |
| Password reset | Admin-handled; no public reset API |
| First response (pilot SLA) | **1 business day** for Medium/Low; **4 hours** for High; **1 hour** for Critical during business hours (adjust per firm contract) |
| After-hours | Critical (S1) availability / trust → on-call ops per firm rota |
| Communication | Research Mode / closed-beta language only — never claim Commercial GA |

---

## 3. Issue triage

### 3.1 Intake checklist

1. Reporter identity (provisioned pilot?).  
2. Route / ticker / time (UTC) / browser / screenshot.  
3. Correlation / request ID if present.  
4. Reproduce on Chrome or Edge when possible.  
5. Classify: **Expected limitation** vs **Defect** vs **Incident**.

### 3.2 Fast filters (do not escalate as product bugs)

| Report | Likely classification |
|---|---|
| “Risk scores blank” / typed risk **Data unavailable.** | Expected — CB-06 |
| “Sub-metric Data unavailable.” | Expected unless a sibling stage was incorrectly aliased |
| “Signup didn’t create my account” | Expected — CB-01 |
| “Forgot password didn’t email me” | Expected — CB-02 |
| “Can’t buy / checkout fails” | Expected — CB-04 |
| “Trust ladder missing on Portfolio” | Known residual — document; track for GA-C3; not CRITICAL for pilot |
| AUX Advisor not in palette | Expected — primary IA |

### 3.3 Always escalate (trust / security)

| Signal | Action |
|---|---|
| Fabricated number where API had no data | **S1 Trust** — CV-001 |
| Auth “success” without provisioning / password theatre restored | **S1 Trust** |
| Purchase / free Offer / fake contact mailto restored | **S1 Trust / Compliance** |
| Silent demo ticker analyse (AAPL/ACM) | **S1 Trust** |
| Palette shows AUX to analysts / RBAC bypass | **S1 Security** |
| Credential leak / session fixation | **S1 Security** — follow `docs/ops/runbooks/SECURITY_INCIDENT.md` |

---

## 4. Incident classification

Align with platform incident response; closed-beta labels:

| Severity | Name | Definition | Examples | Initial response |
|---|---|---|---|---|
| **S1** | Critical | Trust breach, security breach, or total pilot outage | Fabrication; auth theatre; web+API down | Immediate; page on-call; consider rollback |
| **S2** | High | Primary research path broken for many desks | Analyse 5xx sustained; login broken for provisioned users | Same day; hotfix or rollback |
| **S3** | Medium | Degraded feature; workaround exists | Single module skeleton stuck; portfolio widget error | Next business day |
| **S4** | Low | Cosmetic / docs / known residual | Density, dual h1 legal, ladder incomplete | Backlog / GA conditions |

**Rule:** Only **CRITICAL** trust defects block closed-beta production posture. Known HIGH residuals (universal ladder, headed VQA) are tracked — do not reinvent as new S1 unless behaviour **regressed** from certified honesty.

---

## 5. Escalation path

```text
Desk reporter
  → Pilot Administrator (access / role)
    → Support triage (this runbook)
      → Engineering on-call (S1/S2 functional)
        → Trust / Governance owner (CV/RS issues)
          → Release Board (posture / rollback / communicate)
```

| Layer | Owns |
|---|---|
| Pilot Administrator | Credentials, roles, “can’t see nav” |
| Support triage | Classification, known-limitation education, ticket hygiene |
| Engineering | Reproduce, deploy fix or execute rollback |
| Trust / Governance | CV-001…CV-010 / RS violations; certify messaging |
| Release Board | Pilot pause, GA claims, external comms |

For platform outage steps also use `docs/ops/runbooks/SERVICE_OUTAGE.md` and `docs/ops/runbooks/INCIDENT_RESPONSE.md`.

---

## 6. Working the ticket

1. **Acknowledge** within SLA.  
2. **Classify** (limitation / defect / incident).  
3. **Contain** — disable bad flag, revoke bad role, or prepare rollback ([`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md)).  
4. **Mitigate** — prefer certified artefact restore over analytical hot-patch.  
5. **Communicate** — Research Mode status to affected desks.  
6. **Resolve** — fix on branch; re-smoke go-live checks.  
7. **Postmortem** for S1/S2 — include commit SHAs and trust impact.

### Evidence to collect

- Deployed web commit SHA / image tag  
- API version / health  
- Request IDs (`X-Request-Id` if present)  
- Whether empty vs fabricated  
- Browser / viewport  

**Do not** store full research payloads in public ticketing.

---

## 7. Common playbooks

### 7.1 “Numbers look wrong”

1. Confirm API response vs UI (thin client).  
2. If UI shows a value with no source → **S1 Trust**.  
3. If UI shows **Data unavailable.** correctly → educate + close as limitation.  
4. If API incomplete → backend ticket; UI must remain honest.

### 7.2 Login failures

1. Confirm user is provisioned.  
2. Check 401/403 rates (expected for strangers).  
3. Admin reset credentials.  
4. If all provisioned users fail → **S2** API/auth incident.

### 7.3 Performance complaints

1. Note route and holdings size.  
2. Confirm skeletons/lazy still present (not a stuck spinner with silent empty).  
3. Check API latency.  
4. Field CWV not yet GA-certified — do not promise Lighthouse scores.

### 7.4 Accessibility complaints

1. Reproduce keyboard / focus.  
2. Log against a11y cert residuals.  
3. Escalate blockers on primary path (cannot reach Analysis) as **S2**.

---

## 8. Closure criteria

| Type | Close when |
|---|---|
| Limitation | User acknowledges Known Limitations reference |
| Defect | Fix deployed + smoke green + reporter confirmed |
| S1/S2 incident | Service restored or rolled back; postmortem filed; desks notified |

---

## 9. Related documents

| Document | Path |
|---|---|
| Rollback | [`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md) |
| Operations | [`OPERATIONS_RUNBOOK.md`](./OPERATIONS_RUNBOOK.md) |
| Pilot guide | [`PILOT_USER_GUIDE.md`](./PILOT_USER_GUIDE.md) |
| Platform incident | `docs/ops/runbooks/INCIDENT_RESPONSE.md` |
| Security incident | `docs/ops/runbooks/SECURITY_INCIDENT.md` |
