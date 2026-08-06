# Administrator Guide — DSP AI Indicator Version 1.0.0 (Closed Beta)

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Posture | Closed-beta / institutional pilot · Research Mode |
| Companion | [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) · [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) · [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md) |
| Date | 2026-08-02 |

---

## 1. Purpose

This guide covers **user provisioning**, **role management**, **operational responsibilities**, and **support expectations** for administrators running Version 1.0.0 closed beta. It does not redesign auth APIs or RBAC; it documents how to operate the certified posture.

Deep platform ops remain under `docs/OPERATIONS_RUNBOOK.md` and `docs/ops/runbooks/`. This document is the **release-facing admin packet** for pilot desks.

---

## 2. Access model (closed beta)

| Principle | Detail |
|---|---|
| Provisioning | **Admin-only.** `/signup` is Request Access honesty — it does **not** create accounts. |
| Password recovery | No public reset / verify APIs. Admins handle credential reset offline / via admin tooling. |
| Commerce | Pricing illustrative — not purchasable. Do not enable checkout. |
| Contact | Keep `SUPPORT_CONTACT.channelsPublished` **false** until real mailboxes exist. |
| Thin client | Users consume `/api/v1` only; no browser-side scoring. |

**Pre-flight:** provision all pilot users **before** go-live. Do not rely on Request Access form submission as an account pipeline.

---

## 3. User provisioning

### 3.1 Recommended pilot roles

Builtin roles (auth package) used for shell access patterns:

| Role | Typical pilot use | Key permissions (summary) |
|---|---|---|
| `research_analyst` | Primary desk user | `read_research`, `create_research`, `edit_drafts`, `submit_workflow` |
| `senior_analyst` | Lead analyst | Analyst + `approve_workflow`, `view_audit` |
| `portfolio_manager` | Portfolio desk | Research read + portfolio shell access via role |
| `reviewer` | Peer review | `read_research`, approve/reject workflow, `view_audit` |
| `compliance_officer` | Oversight | Research read, workflow approve/reject, `view_audit`, `manage_roles` |
| `investment_committee` | Committee read | Research-oriented committee access |
| `read_only` | Observer | Minimal read posture |
| `administrator` | Platform admin | Full permission set including `manage_users`, `manage_roles`, `configure_platform`, `view_audit` |

Shell Administration (`/admin`) requires one of: `manage_users`, `manage_roles`, `configure_platform`, `view_audit`, or role `administrator`.

Primary research surfaces (Company Analysis, Research Workspace, Reports, IRD) require `read_research` (or equivalent via role evaluation).

### 3.2 Provisioning checklist

- [ ] Collect desk list: name, email, org, intended role, start date.  
- [ ] Create accounts via approved admin / identity path (not `/signup`).  
- [ ] Assign least-privilege role for pilot duties.  
- [ ] Confirm login works: `/login` → `/dashboard`.  
- [ ] Confirm command palette does **not** expose AUX Advisor/Launch/Screening for analyst roles.  
- [ ] Deliver credentials + [`PILOT_USER_GUIDE.md`](./PILOT_USER_GUIDE.md) + [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md).  
- [ ] Record provisioned users in the pilot register (internal).  
- [ ] Revoke access promptly when a desk leaves the pilot.

### 3.3 Deprovisioning

1. Disable or delete the user in the identity / admin store.  
2. Invalidate active sessions if tooling supports it.  
3. Confirm login returns unauthorized / forbidden.  
4. Note reason and timestamp in the pilot register.

---

## 4. Role management

| Responsibility | Guidance |
|---|---|
| Least privilege | Default new pilot users to `research_analyst` or `read_only` unless portfolio / admin duties require more. |
| Admin accounts | Limit `administrator` to named ops owners. Prefer separate admin and research accounts. |
| Role changes | Document who approved the change; prefer change during business hours. |
| Palette / nav | UI filters via `searchableRoutes(permissions, roles)` — do not grant `manage_*` to ordinary analysts. |
| AUX routes | Do not expand AUX into primary IA during closed beta without Release Board approval. |

If a user reports “missing menu items,” verify permissions before filing a product defect.

---

## 5. Operational responsibilities

### 5.1 Release posture ownership

Administrators (with Release Board) must ensure external messaging stays **closed-beta Research Mode**, not Commercial GA, until GA conditions close.

### 5.2 Environment hygiene

| Item | Expectation |
|---|---|
| Feature flags / env | Closed-beta posture; no public registration endpoints |
| Contact channels | Unpublished until real mailboxes |
| Pricing | Illustrative only |
| `VERSION` | `v1.0.0` on deployed artefact |
| API | Frozen `/api/v1` health green before desk use |

### 5.3 Day-2 operations

- Watch auth failure rates (401/403 expected for unprovisioned attempts).  
- Watch analyse / portfolio error rates.  
- Escalate trust regressions (fabricated numbers, restored theatre) as **S1/S2** per [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md).  
- Prefer rollback of certified build over hot-fixing analytical honesty under pressure ([`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md)).

### 5.4 Admin UI (`/admin`)

Enterprise administration surface for users with admin permissions. Treat workflow/queue widgets that show **Data unavailable.** as honest empty states until admin workflow APIs are fully consumed — do not invent queue metrics.

---

## 6. Support expectations (admin side)

| Expectation | Detail |
|---|---|
| First response (pilot) | Acknowledge desk issues within the pilot SLA (see Support Runbook) |
| Credential issues | Admin-handled; do not send users to forgot-password theatre |
| Data unavailable reports | Educate using Known Limitations; escalate only if a **filled** fabricated value appears |
| Trust defects | Immediate escalation — CV-001 violations are release-critical |
| Commercial purchase requests | Decline politely; product is not for purchase in 1.0.0 closed beta |
| After-hours | Follow incident severity; S1 trust/availability may require on-call ops |

Admins should keep [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md) and this guide together in the pilot ops folder.

---

## 7. Smoke tests after provisioning or deploy

Mirror of go-live smokes (admin-owned):

1. Provisioned user: `/login` → `/dashboard` with Research Mode visible.  
2. `/analysis` requires explicit ticker — no silent AAPL/ACM default.  
3. `/research/institutional` loads for a selected symbol (API-backed).  
4. `/portfolio` shows coverage language (not Health/Compounders marketing).  
5. Palette: AUX not listed for analyst.  
6. `/signup` remains Request Access honesty.  
7. Empty cells show **Data unavailable.** / coverage copy — not invented scores.

---

## 8. Related documents

| Document | Path |
|---|---|
| Pilot user guide | [`PILOT_USER_GUIDE.md`](./PILOT_USER_GUIDE.md) |
| Known limitations | [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) |
| Support runbook | [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md) |
| Operations runbook (release) | [`OPERATIONS_RUNBOOK.md`](./OPERATIONS_RUNBOOK.md) |
| Platform ops index | `docs/OPERATIONS_RUNBOOK.md` |
| Go-live checklist | [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) |
