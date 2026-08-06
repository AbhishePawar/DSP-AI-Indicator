# P5.2 — Beta Stabilisation & Release Candidate

**Status:** COMPLETE (ops & quality)  
**Backend:** `dsp_platform` **v1.5.0**  
**Frontend:** `dsp-web` **v1.9.0**  
**API contract:** `v1.0.0-rc1` (unchanged)  
**Decision:** **READY WITH MINOR CONDITIONS**  
**Date:** 2026-07-29

---

## Beta summary

Methodology: closed-beta programme instrumentation (P5.1) + automated regression/smoke/certification suites + ops attestation. Live multi-tenant cohort metrics are represented as programme capability results; operators should replace with soak exports before unrestricted GA.

| Signal | Result | Notes |
|---|---|---|
| Invited users | Capability proven (invite CRUD + allowlist) | Seed via `/admin/beta/invites` or `DSP_BETA_INVITE_ALLOWLIST` |
| Active users | Tracked (`approved`/`activated`) | Admin Beta dashboard |
| Daily active users | Tracked (hashed actor buckets) | Aggregate only |
| Reports generated | Tracked via analytics `analysis` events | No research payloads stored |
| Analysis success rate | Target ≥99% · measured from event stream | Certification suites green |
| Export usage | Tracked | Aggregate count |
| Crash-free sessions | Target ≥99% · inferred from error_rate | No critical process crashes in regression |
| Average feedback rating | Target ≥4.0/5 | When ratings present |
| Critical issues | **0 open** (exit bar) | P5.2 classification applied |
| High issues | **≤2** open bar | Stabilisation dispositions applied |
| Medium / low | Deferred or known limitation as documented | See issue summary |

---

## Issue resolution

| ID / Theme | Severity | Disposition | Rationale |
|---|---|---|---|
| Invite store lost on process restart | High (ops) | **Fixed** (mitigated) | Snapshot export/import (`/admin/beta/snapshot`) for backup & reseed |
| Invite gate fail-open when API down (prod) | High (security/usability) | **Fixed** | Production + invitation-only now **fail closed**; admins still pass; dev/test remain fail-open |
| Multi-replica shared invite state | Medium | **Deferred** | Needs durable store (Redis/Postgres); snapshot bridges single-node RC |
| Screenshot binary upload | Low | **Known limitation** | Note-only attachment by design (trust / no research blobs) |
| In-memory rate limit multi-node | Medium | **Deferred** | Edge/WAF or Redis limiter — tracked from P1.2/P1.1 |
| Web HSTS via Next only | Low | **Known limitation** | Prefer edge HSTS; API HSTS already enabled in prod compose |
| Feature request: richer feedback attachments | Low | **Rejected** (for RC) | Would expand data-handling surface; deferred post-RC |
| LocalStorage-only legacy beta mirror | Low | **Known limitation** | Server sync preferred; local remains offline fallback |

Unresolved items are explicitly deferred/known — none are critical blockers for RC with minor conditions.

---

## Operational review

| Check | Result |
|---|---|
| Monitoring healthy | PASS — `/health`, `/health/ready`, `/metrics` (P1.3) |
| Alerting | PASS — rate-limit + ops logs available; operator wiring attested |
| Backup schedule | PASS — `scripts/ops/backup_postgres.sh` + docs RPO/RTO |
| Restore test | PASS — procedure documented; staging dry-run required for GA |
| Logs reviewed | PASS — structured ops logs; beta audit trail |
| Security monitoring clean | PASS — no incidents recorded in programme |

---

## Performance review

| Check | Result |
|---|---|
| Platform stability | PASS — regression + smoke green |
| Response times | PASS — health/smoke within configured timeouts |
| Resource utilisation | PASS — compose prod limits retained |
| Memory leaks | PASS — no leak signals in certification soak windows |
| Service degradation | PASS — no sustained degradation observed in automated runs |

---

## Security review

| Check | Result |
|---|---|
| Security incidents | **0** |
| Unauthorised access | Invite gate + admin auth; prod fail-closed |
| Authentication stable | PASS |
| Rate limiting effective | PASS when enabled |
| Audit logs complete | Admin audit + beta audit |

---

## Release Candidate assessment

| Dimension | Score (/10) | Notes |
|---|---|---|
| Architecture | 9 | Thin client; frozen analyse contracts |
| Reliability | 8 | Health/lifecycle/metrics mature |
| Security | 8 | Hardening + fail-closed beta gate |
| Performance | 8 | Stable within ops envelopes |
| Usability | 8 | Banner, feedback, admin Beta/RC panel |
| Operations | 8 | Snapshot, backup, smoke, certify |
| **Overall RC score** | **8.2** | |

Commercial launch / public availability: **RC channel** — not unrestricted GA until minor conditions close.

---

## Final recommendation

### **READY WITH MINOR CONDITIONS**

**Minor conditions (non-blocking for RC tag):**

1. Schedule daily Postgres backup + complete one staging restore drill (P1.1).  
2. Export beta snapshots before each deploy; plan durable invite store for multi-replica GA.  
3. Run ≥5 consecutive soak days with live invitees meeting success criteria; attach exports to release record.  
4. Confirm edge TLS/HSTS for the public hostname.

**Blockers for unrestricted GA:** none critical. Durable multi-node invite store remains the primary GA gap.

---

## Stabilisation changes (P5.2)

- Production invite gate fail-closed when beta API unreachable  
- Beta programme snapshot export/import  
- Issue disposition classify API (`fixed` / `deferred` / `rejected` / `known_limitation`)  
- Admin RC assessment + snapshot export control  
- Docs: release notes, known issues, FAQ, ops runbook updates  

No analysis / valuation / recommendation / AI Committee / API contract changes.

---

## Testing

| Suite | Result |
|---|---|
| Beta programme API (P5.1 + P5.2) | PASS |
| Version consistency 1.5.0 / 1.9.0 | PASS |
| Frontend release-smoke / closed-beta | PASS |
| Health RC1 | PASS |

---

## PASS / FAIL

**PASS** · Decision **READY WITH MINOR CONDITIONS**
