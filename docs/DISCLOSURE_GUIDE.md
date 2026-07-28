# Disclosure Guide (PEP-004)

## Research Mode (default)

Mandatory disclosures include:

1. Research Mode educational posture (not SEBI tip)
2. DPDP privacy notice summary
3. AI explanation boundaries

Templates: `compliance.research_mode_templates()` — versioned (`2026.1`).

## Presentation locale

| Field | Default |
|---|---|
| Timezone | Asia/Kolkata (IST) |
| Currency | INR (`format_inr`) |
| Locale | en-IN |

Helpers: `format_ist()`, `format_inr()`.

## SEBI Mode

Still **gated**. Selecting mode=`sebi` adds an explicit “not activated” disclosure.
Buy/Sell labels remain blocked unless all feature flags unlock (unchanged PR1.0 rules).

## API / UI

Do not hardcode disclosure text in engines. Load via `DisclosurePort` /
`ResearchModeDisclosureEngine`. Thin client may mirror terminology only.
