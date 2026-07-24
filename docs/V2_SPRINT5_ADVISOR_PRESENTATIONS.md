# Epic V2.0 Sprint 5 — Advisor Reporting & Client Presentation

**Web:** `2.0.0`

## Mission

Assemble professional client presentation packs from existing DSP research, model portfolios, and advisor notes. Presentation only — no PDF backend, no persistence, no Research Engine changes.

## Surfaces

- `/advisor/presentations` — Create · Duplicate · Rename · Archive (session)
- `/advisor/presentations/builder` — Section reorder + visibility
- `/advisor/presentations/preview` — Desktop · Tablet · Print · Present
- `/advisor/presentations/templates` — Initial Consultation → Custom
- `/advisor/presentations/export` — Markdown/HTML download · PDF/DOCX placeholders

## Trust

Displays DSP demo envelope fields exactly (thesis, quality, valuation, confidence, evidence, methodology, limitations). Never rewrites conclusions.

## Enable

`NEXT_PUBLIC_ADVISOR_DEMO=true`
