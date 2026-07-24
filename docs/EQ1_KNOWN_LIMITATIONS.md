# EQI Known Limitations — Earnings Quality Intelligence Engine

**EQI:** `1.0.0`

## Active limitations

- No Research Engine / live company data coupling — callers supply metric series and evidence
- No persistence, authentication, or multi-user storage
- No chart/gauge **rendering** (dashboard **models** only)
- Earnings Persistence remains an unscored shell and is excluded from Overall Earnings Quality Score
- Advisor Platform / Decision / Research / KG / Portfolio / Risk / Valuation / MIE / EMI / Copilot / Reports / Compliance / API / Launch Dashboard intentionally untouched
- PDF/DOCX, broker, CRM, billing remain out of scope

## What is NOT a limitation anymore

- Overall Earnings Quality Score is **enabled** with published `EARNINGS_CATEGORY_WEIGHTS`
- Earnings Quality Dashboard models integrate scored categories with explainability
- EQI is certified **production-ready** and **feature-complete** for the library surface (EQ1.8)
