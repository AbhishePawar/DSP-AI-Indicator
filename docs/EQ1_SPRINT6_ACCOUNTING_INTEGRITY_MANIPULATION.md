# Epic EQ1.0 Sprint EQ1.6 — Accounting Quality · Financial Statement Integrity · Earnings Manipulation Risk

**Web:** `2.3.0` · **EQI:** `0.6.0-accounting-integrity-manipulation`

## Mission

Evaluate accounting conservatism, statement integrity/transparency, and manipulation-risk signals as evidence-based category scores. **Category scores only** — Overall Earnings Quality Score remains disabled until EQ1.7. Earnings Persistence remains an unscored foundation shell.

## Foundation category ids

| Module | Foundation id |
|--------|---------------|
| Accounting Quality | `accounting_conservatism` |
| Financial Statement Integrity | `earnings_transparency` |
| Earnings Manipulation Risk | `earnings_manipulation_risk` |

## Modules

### Accounting Quality (`accounting_conservatism`)

| File | Role |
|------|------|
| `accountingQualityModels.ts` | Domain types |
| `accountingQualityEvidence.ts` | Mapping / indexing |
| `accountingQualityScoring.ts` | `ACCOUNTING_QUALITY_METRIC_WEIGHTS` · risks (`accqrisk-`) |
| `accountingQualityBuilders.ts` | Analysis + demo |
| `accountingQualitySelectors.ts` | Selectors |
| `accountingQualityValidators.ts` | Validation |
| `accountingQualityEngine.ts` | Facade |

### Financial Statement Integrity (`earnings_transparency`)

| File | Role |
|------|------|
| `financialStatementIntegrityModels.ts` | Domain types |
| `financialStatementIntegrityEvidence.ts` | Mapping / indexing |
| `financialStatementIntegrityScoring.ts` | `FINANCIAL_STATEMENT_INTEGRITY_METRIC_WEIGHTS` · risks (`fsirisk-`) |
| `financialStatementIntegrityBuilders.ts` | Analysis + demo |
| `financialStatementIntegritySelectors.ts` | Selectors |
| `financialStatementIntegrityValidators.ts` | Validation |
| `financialStatementIntegrityEngine.ts` | Facade |

### Earnings Manipulation Risk (`earnings_manipulation_risk`)

| File | Role |
|------|------|
| `earningsManipulationModels.ts` | Domain types |
| `earningsManipulationEvidence.ts` | Mapping / indexing |
| `earningsManipulationScoring.ts` | `EARNINGS_MANIPULATION_METRIC_WEIGHTS` · risks (`emrisk-`) |
| `earningsManipulationBuilders.ts` | Analysis + demo |
| `earningsManipulationSelectors.ts` | Selectors |
| `earningsManipulationValidators.ts` | Validation |
| `earningsManipulationEngine.ts` | Facade |

## Usage

```ts
import { earningsEngine } from "@/lib/earnings";

const eq = earningsEngine.demoWithScoredCategories();
earningsEngine.overallEarningsQuality(); // null
```

## Trust

- Published metric weights (each category sum = 1)
- Evidence-linked conclusions
- Persistence shell remains unscored
- No Overall Earnings Quality Score · no AI opinions
