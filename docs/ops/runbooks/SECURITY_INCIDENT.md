# Runbook — Security Incident Handling

**Epic:** P6.1 · Contact: `security@dsp-ai-indicator.example`

## Scope

Suspected breach, credential leak, unauthorised admin access, dependency exploit, or data exposure (including research payloads mishandled in tickets).

## Steps

1. **Report** — email security@; do not discuss exploit details in public channels.
2. **Contain** — rotate secrets/tokens; revoke sessions; disable compromised accounts; rate-limit / WAF as needed.
3. **Preserve evidence** — logs, timestamps, request IDs; do not wipe systems before snapshot.
4. **Assess** — confidentiality / integrity / availability impact; PII vs research artefacts.
5. **Eradicate** — patch, revoke keys, rebuild from known-good images.
6. **Notify** — legal/compliance per P4.1 obligations; customers if required.
7. **Recover** — restore service; monitor for recurrence.
8. **Lessons** — postmortem; update hardening backlog (no silent scope expansion into engines).

## Forbidden

Publishing exploit PoCs in customer docs; storing secrets in Feedback; fabricating breach status.
