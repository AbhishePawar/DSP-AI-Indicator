# 15 — UI Certification Checklist

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  

---

## 1. Purpose

Gate every UI change before it is marked complete. A surface may ship only when this checklist is **PASS** (or **PASS WITH CONDITIONS** with named owners and dates).

---

## 2. How to use

1. Identify surface (Website · Dashboard · Research · Portfolio · Report · Mobile · Admin · AI Panel).  
2. Complete every applicable section.  
3. Record decision, date, reviewer.  
4. Link PR / epic.  

**Decision values:** PASS · PASS WITH CONDITIONS · FAIL  

---

## 3. Authority gates

| # | Check | Pass criteria |
|---|---|---|
| A1 | Constitution priority respected | No polish that reduces trust |
| A2 | User Trust Standard | Traceable · Explainable · Consistent · Actionable · Honest · Transparent AI · Research first |
| A3 | Thin client | No client-side valuation/recommendation reasoning; frozen `/api/v1` only |
| A4 | REP-002 alignment | Labels do not invent parallel ontology meanings |
| A5 | Design System conformance | Tokens/components/motion/a11y from `docs/design/` |

---

## 4. Brand & visual

| # | Check | Pass criteria |
|---|---|---|
| B1 | Palette | Teal/slate tokens only; no purple brand accents |
| B2 | Themes | Light + dark verified |
| B3 | Typography | Fraunces titles · Sora body · measure ≤72ch for prose |
| B4 | Elevation | Flat + border default; shadows only modal/dropdown |
| B5 | Marketing hero (if any) | One composition; brand-forward; no card grid hero |

---

## 5. Color & meaning

| # | Check | Pass criteria |
|---|---|---|
| C1 | Semantic colors | Success/warning/info/danger used correctly |
| C2 | Financial risk | Not encoded as red “Sell”; text ratings present |
| C3 | Status | Text + color; disabled clear |
| C4 | Source / epistemic chips | Present on insights |

---

## 6. Layout & components

| # | Check | Pass criteria |
|---|---|---|
| D1 | Grid / gutters | Per Grid + Spacing systems |
| D2 | Navigation | Active state clear; mobile menu works |
| D3 | Cards / tables / forms | Variants per Components doc |
| D4 | Empty / loading / error | All three handled |
| D5 | AI panel (if any) | Header · stream · composer · disclosure |
| D6 | Dashboard / report layout | Matches surface rules |

---

## 7. Data visualization

| # | Check | Pass criteria |
|---|---|---|
| E1 | Caption | Title + interpretation sentence |
| E2 | Tooltip | Value + plain English |
| E3 | Series | ≤3 hues or patterns; dark tokens explicit |
| E4 | Honesty | No silent gap filling; unavailable labeled |

---

## 8. UX & Research Mode

| # | Check | Pass criteria |
|---|---|---|
| F1 | Four Questions | Answered on screen or one reveal away |
| F2 | Next investigation step | Always present |
| F3 | Research Mode vocabulary | No BUY/SELL/HOLD chrome unless flags unlock |
| F4 | Analysis order (research) | Matches Product Design Standard V2 where applicable |

---

## 9. Motion

| # | Check | Pass criteria |
|---|---|---|
| G1 | Purposeful only | No celebratory noise |
| G2 | Duration | Typically 150–300ms |
| G3 | Reduced motion | `prefers-reduced-motion` honored |

---

## 10. Accessibility

| # | Check | Pass criteria |
|---|---|---|
| H1 | Contrast | AA light + dark |
| H2 | Keyboard | Critical path operable |
| H3 | Focus visible | All controls |
| H4 | Names | Icon buttons labeled |
| H5 | Structure | Landmarks + heading order |
| H6 | Touch | ≥44×44px targets |

---

## 11. Responsive

| # | Check | Pass criteria |
|---|---|---|
| I1 | Breakpoints | sm/md/lg/xl verified for surface |
| I2 | Mobile adaptation | Stack/sheet/scroll patterns correct |
| I3 | No page-wide horizontal trap | Tables may scroll locally |

---

## 12. Performance (UI)

| # | Check | Pass criteria |
|---|---|---|
| J1 | Skeletons / progressive render | No long blank main |
| J2 | Heavy lists | Virtualized or paginated when needed |
| J3 | Motion cost | Transform/opacity preferred |

---

## 13. Certification record (template)

```text
Surface:
Epic / PR:
Reviewer:
Date:
Decision: PASS | PASS WITH CONDITIONS | FAIL
Conditions (if any):
Notes:
```

---

## 14. Relationship to platform quality gate

This checklist feeds the broader Implementation Quality Gate (PR1.0–PR1.2 · Governance · Trust · Constitution · Four Questions · Research Mode · Feature flags · A11y · Performance · Responsive · Mobile · Thin client · Regression). UI Certification is necessary but not sufficient alone for full platform release.
