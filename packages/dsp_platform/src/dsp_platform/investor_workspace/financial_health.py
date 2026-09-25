"""Deterministic Financial Health Score (Figma Client Profile, 0–1000).

Five explainable components, each 0–100, summed and scaled ×2 to 0–1000:

1. Income Strength        — monthly surplus ÷ gross monthly income (30 % ⇒ 100)
2. Savings & Investments  — (savings + investments) ÷ annual income (3× ⇒ 100)
3. Debt Management        — EMI ÷ income (DTI; 50 % ⇒ 0) less card-debt penalty
4. Emergency Protection   — emergency fund months ÷ 6 (⇒ 70) + insurance (15 + 15)
5. Goal Readiness         — monthly surplus ÷ required monthly saving for goal

Figma zones: 0–199 Very Poor · 200–399 Poor · 400–599 Fair · 600–749 Good ·
750–1000 Excellent. CV-002: every mandatory input must be present, otherwise
``status = "incomplete"`` and no score is produced. CV-004: pure function.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

__all__ = [
    "FINANCIAL_HEALTH_VERSION",
    "MANDATORY_INPUTS",
    "compute_financial_health",
    "health_category",
    "profile_completeness",
]

FINANCIAL_HEALTH_VERSION = "fhs-1.0.0"

MANDATORY_INPUTS: tuple[str, ...] = (
    "monthly_income",
    "monthly_expenses",
    "total_savings",
    "total_investments",
    "emergency_fund",
    "primary_goal",
    "target_amount",
    "target_year",
)

# Every Figma form field (used for the "Profile N% complete" indicator).
PROFILE_FIELDS: tuple[str, ...] = (
    "full_name",
    "email",
    "mobile",
    "age",
    "city",
    "occupation",
    "dependents",
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
    "other_monthly_income",
    "total_savings",
    "total_investments",
    "emergency_fund",
    "outstanding_loans",
    "credit_card_outstanding",
    "health_insurance",
    "life_insurance",
    "primary_goal",
    "target_amount",
    "target_year",
)

ZONES: tuple[tuple[int, str], ...] = (
    (750, "Excellent"),
    (600, "Good"),
    (400, "Fair"),
    (200, "Poor"),
)


def health_category(score: int) -> str:
    for threshold, label in ZONES:
        if score >= threshold:
            return label
    return "Very Poor"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _num(profile: dict[str, Any], key: str, default: float | None = None) -> float | None:
    raw = profile.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def profile_completeness(profile: dict[str, Any] | None) -> dict[str, Any]:
    if not profile:
        return {"percent": 0, "filled": 0, "total": len(PROFILE_FIELDS), "missing": list(PROFILE_FIELDS)}
    filled = [k for k in PROFILE_FIELDS if profile.get(k) not in (None, "")]
    missing = [k for k in PROFILE_FIELDS if k not in filled]
    return {
        "percent": round(100 * len(filled) / len(PROFILE_FIELDS)),
        "filled": len(filled),
        "total": len(PROFILE_FIELDS),
        "missing": missing,
    }


def _component(
    key: str,
    label: str,
    score: float | None,
    *,
    formula: str,
    inputs: dict[str, Any],
    note: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "score": None if score is None else int(round(_clamp(score, 0, 100))),
        "max": 100,
        "formula": formula,
        "inputs": inputs,
        "note": note,
    }


def compute_financial_health(
    profile: dict[str, Any] | None, *, now: datetime | None = None
) -> dict[str, Any]:
    """Pure, deterministic score. Returns ``status`` incomplete/complete."""
    profile = dict(profile or {})
    missing = [k for k in MANDATORY_INPUTS if profile.get(k) in (None, "")]
    completeness = profile_completeness(profile)
    if missing:
        return {
            "version": FINANCIAL_HEALTH_VERSION,
            "status": "incomplete",
            "score": None,
            "max": 1000,
            "category": None,
            "components": [],
            "insight": "Unable to calculate. Complete the highlighted fields to receive a Financial Health Score.",
            "missing_inputs": missing,
            "completeness": completeness,
        }

    income = _num(profile, "monthly_income", 0.0) or 0.0
    other_income = _num(profile, "other_monthly_income", 0.0) or 0.0
    expenses = _num(profile, "monthly_expenses", 0.0) or 0.0
    no_debt = bool(profile.get("no_outstanding_debt"))
    emi = 0.0 if no_debt else (_num(profile, "monthly_emi", 0.0) or 0.0)
    loans = 0.0 if no_debt else (_num(profile, "outstanding_loans", 0.0) or 0.0)
    card = 0.0 if no_debt else (_num(profile, "credit_card_outstanding", 0.0) or 0.0)
    savings = _num(profile, "total_savings", 0.0) or 0.0
    investments = _num(profile, "total_investments", 0.0) or 0.0
    emergency = _num(profile, "emergency_fund", 0.0) or 0.0
    # Figma captures ₹ cover amounts; a positive cover counts as insured.
    health_cover = _num(profile, "health_insurance", 0.0) or 0.0
    life_cover = _num(profile, "life_insurance", 0.0) or 0.0
    health_ins = health_cover > 0
    life_ins = life_cover > 0
    target_amount = _num(profile, "target_amount", 0.0) or 0.0
    target_year = int(_num(profile, "target_year", 0.0) or 0)

    gross = income + other_income
    if gross <= 0:
        return {
            "version": FINANCIAL_HEALTH_VERSION,
            "status": "incomplete",
            "score": None,
            "max": 1000,
            "category": None,
            "components": [],
            "insight": "Unable to calculate. Monthly income must be greater than zero.",
            "missing_inputs": ["monthly_income"],
            "completeness": completeness,
        }

    surplus = gross - expenses - emi
    savings_rate = surplus / gross
    income_strength = _clamp(savings_rate / 0.30) * 100

    annual_income = gross * 12
    wealth_ratio = (savings + investments) / annual_income
    savings_score = _clamp(wealth_ratio / 3.0) * 100

    dti = emi / gross
    card_penalty = min(30.0, (card / gross) * 10.0) if gross else 0.0
    debt_score = 100.0 if no_debt else _clamp(1 - dti / 0.5) * 100 - card_penalty
    if loans > 0 and not no_debt:
        # Secured debt above 5× annual income caps the component at 60.
        debt_score = min(debt_score, 60.0) if loans > 5 * annual_income else debt_score

    monthly_outflow = expenses + emi
    months_covered = emergency / monthly_outflow if monthly_outflow > 0 else 6.0
    emergency_score = _clamp(months_covered / 6.0) * 70 + (15 if health_ins else 0) + (15 if life_ins else 0)

    current = (now or datetime.now(tz=UTC)).astimezone(UTC)
    months_left = max(1, (target_year - current.year) * 12 + (12 - current.month))
    gap = target_amount - (savings + investments)
    if gap <= 0:
        goal_score = 100.0
        required_monthly = 0.0
    else:
        required_monthly = gap / months_left
        goal_score = _clamp(surplus / required_monthly) * 100 if required_monthly > 0 else 100.0

    components = [
        _component(
            "income_strength",
            "Income Strength",
            income_strength,
            formula="(gross income − expenses − EMI) ÷ gross income ÷ 30%",
            inputs={"gross_monthly_income": gross, "monthly_expenses": expenses, "monthly_emi": emi, "savings_rate": round(savings_rate, 4)},
            note="A 30% monthly savings rate scores full marks.",
        ),
        _component(
            "savings_investments",
            "Savings & Investments",
            savings_score,
            formula="(savings + investments) ÷ annual income ÷ 3",
            inputs={"total_savings": savings, "total_investments": investments, "annual_income": annual_income, "wealth_ratio": round(wealth_ratio, 4)},
            note="Three years of income in savings and investments scores full marks.",
        ),
        _component(
            "debt_management",
            "Debt Management",
            debt_score,
            formula="(1 − EMI ÷ income ÷ 50%) × 100 − min(30, card debt ÷ income × 10)",
            inputs={"debt_to_income": round(dti, 4), "credit_card_outstanding": card, "outstanding_loans": loans, "no_outstanding_debt": no_debt},
            note="No outstanding debt scores full marks; EMI at 50% of income scores zero.",
        ),
        _component(
            "emergency_protection",
            "Emergency Protection",
            emergency_score,
            formula="months covered ÷ 6 × 70 + health insurance 15 + life insurance 15",
            inputs={"emergency_fund": emergency, "monthly_outflow": monthly_outflow, "months_covered": round(months_covered, 2), "health_insurance_cover": health_cover, "life_insurance_cover": life_cover, "health_insured": health_ins, "life_insured": life_ins},
            note="Six months of outflow plus both covers scores full marks.",
        ),
        _component(
            "goal_readiness",
            "Goal Readiness",
            goal_score,
            formula="monthly surplus ÷ required monthly saving to reach target by target year",
            inputs={"primary_goal": profile.get("primary_goal"), "target_amount": target_amount, "target_year": target_year, "months_left": months_left, "required_monthly": round(required_monthly, 2), "monthly_surplus": round(surplus, 2)},
            note="Surplus covering the required monthly saving scores full marks.",
        ),
    ]
    total = int(round(sum(c["score"] for c in components) * 2))
    total = max(0, min(1000, total))
    weakest = min(components, key=lambda c: c["score"])
    strongest = max(components, key=lambda c: c["score"])
    insight = (
        f"{health_category(total)} financial health ({total}/1000). "
        f"Strongest area: {strongest['label']} ({strongest['score']}/100). "
        f"Priority: {weakest['label']} ({weakest['score']}/100) — {weakest['note']}"
    )
    return {
        "version": FINANCIAL_HEALTH_VERSION,
        "status": "complete",
        "score": total,
        "max": 1000,
        "category": health_category(total),
        "components": components,
        "insight": insight,
        "missing_inputs": [],
        "completeness": completeness,
        "calculated_at": current.isoformat(),
    }
