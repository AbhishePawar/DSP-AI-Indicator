# M1 Known Limitations — Management Intelligence Engine

**MIE:** `1.0.0-mie-production`

## Active limitations

- No Research Engine / live company data coupling — callers supply metric series
- No persistence, authentication, or multi-user storage
- No chart/radar **rendering** (visualization **models** only)
- Buffett View is derived commentary — not an independent score and not an overall-score input
- `buffett_style` remains a shell category in foundation `DEFAULT_CATEGORY_WEIGHTS`; overall aggregation uses `MANAGEMENT_CATEGORY_WEIGHTS` (six categories)
- Advisor Platform / frozen engines are intentionally untouched
- PDF/DOCX, broker, CRM, billing remain out of scope

## What is NOT a limitation anymore

- Overall Management Score is **enabled** with published weights
- Dashboard integrates all six category engines with explainability
