# Phase B3 — Decision Pack Validation

**Status:** Complete · Architecture frozen · Additive only  
**Baseline:** 879 tests before B3 · green suite after

## 1. B2 implementation audit

| Check | Result |
|-------|--------|
| Recommendation preserved exactly (echo, not rewrite) | PASS |
| Brief explains; does not re-analyze | PASS |
| Assurance grades robustness; does not change action | PASS |
| MoS never recalculated (propagated only) | PASS |
| No engine logic duplicated | PASS |
| `analyze()` backward compatible | PASS |
| `analyze_decision_pack()` single pipeline (`analyze` once) | PASS |

### Deviations found (before B3 fixes)

1. **SELL + `ACCUMULATE_GRADUALLY`** — guidance stance/rationale implied accumulation on sells.
2. **Valuation-supported BUY without usable MoS → `HIGH` + accumulate** — overstated robustness.
3. **Evidence consistency used `EngineSource` tags** — almost always `ai_committee`, so multi-domain support looked MIXED/THIN incorrectly.
4. **Minority directional win with only soft HOLD dissent labeled `CONFLICT`** — overstated conflict vs narrow support.
5. **HOLD + HIGH used LOW-assurance rationale text** — coherent stance, misleading words.
6. **Intrinsic mid not surfaced in Brief** when `valuation_summary` was present — product gap for “what does valuation say?”

No architecture redesign required. Fixes are deterministic policy-table corrections inside Assurance (+ minor Brief surfacing).

## 2. Scenario matrix

Covered in `tests/test_scenario_matrix.py` (15 named cases + echo checks):

Strong BUY/SELL/HOLD · tech vs fund conflict · fund strong / val expensive · fund weak / val cheap · macro dissent · high MoS weak evidence · low MoS strong fund · missing valuation · missing economic · partial members · strong disagreement · single-domain dependence · high vote agreement without MoS-backed immediacy.

## 3. Contradictions discovered

Documented above; coherence suite locks the invariants:

- No BUY+LOW+`INVEST_IMMEDIATELY`
- No SELL+`ACCUMULATE_GRADUALLY`
- HOLD never implies buy/accumulate language
- No HIGH with thin evidence or conflict agreement
- Valuation BUY without MoS → wait, not HIGH immediacy

## 4. Fixes made (justified)

| Fix | Why |
|-----|-----|
| Guidance never uses accumulate for SELL | Stance name implies long exposure |
| Downgrade when valuation supports directional call without MoS | B1.1 assumption fragility |
| Evidence breadth from agreeing member domains | Correct analytical breadth |
| Soft-only minority → NARROW not CONFLICT | Accurate agreement label |
| HOLD rationale branches by assurance | Honest wording |
| Brief surfaces intrinsic mid when present | Answers valuation question without recalc |

## 5. Golden Decision Packs

`tests/test_golden_packs.py`: robust BUY · fragile valuation BUY · conflict HOLD · SELL without MoS.

## 6. Presentation / read-model

`present_decision_pack(pack) -> DecisionPackView` — read-only section projection:

DECISION · ROBUSTNESS · VALUATION · COMMITTEE · WHY · CAUTION · ACTION · WATCH

No UI, no dashboard, no recalculation.

## 7. Remaining limitations

- No portfolio / risk / sector overlay (by design).
- Guidance stances remain coarse (no explicit `REDUCE_GRADUALLY` enum).
- Synthetic scenarios force committee decisions; live plurality edge cases still belong to committee tests.
- Presentation is a serializer, not a research narrative product.
- Trust for multi-stock / portfolio work still needs live-market calibration beyond structural coherence.

## Verdict question

See final B3 report in the delivery response.
