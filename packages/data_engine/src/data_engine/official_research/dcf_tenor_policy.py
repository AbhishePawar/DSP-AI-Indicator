"""Explicit DCF risk-free tenor policy.

Canonical CAPM (`CapmInputs`) and `DcfMethod` do not name a government-security
maturity. SIMPLE-28 recorded that gap. This module is the machine-readable
policy: it does **not** invent a 91-day T-bill, 5-year G-sec, or 10-year G-sec
convention merely so WACC can run.

Until a preferred tenor is established by valuation methodology (not by scrape
convenience), government-yield observations remain VERIFIED OBSERVATIONS and
are not bound as the DCF `risk_free_rate` input.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "DCF_RISK_FREE_ACCEPTABLE_ALTERNATIVES",
    "DCF_RISK_FREE_CONFLICT_TREATMENT",
    "DCF_RISK_FREE_CURRENCY_POLICY",
    "DCF_RISK_FREE_FRESHNESS_DAYS",
    "DCF_RISK_FREE_MATURITY_POLICY",
    "DCF_RISK_FREE_MAX_MISMATCH",
    "DCF_RISK_FREE_MULTIPLE_MATURITIES",
    "DCF_RISK_FREE_OBSERVATION_VS_VALUATION",
    "DCF_RISK_FREE_PREFERRED_MATURITY",
    "DCF_RISK_FREE_REQUIRED_MATURITY",
    "DCF_RISK_FREE_STALE_TREATMENT",
    "DCF_RISK_FREE_TENOR_POLICY_ID",
    "DCF_RISK_FREE_UNLABELED_TREATMENT",
    "GOVERNMENT_YIELD_KINDS",
    "REJECTED_RISK_FREE_KINDS",
    "evaluate_risk_free_binding",
    "tenor_policy_public_dict",
]

DCF_RISK_FREE_TENOR_POLICY_ID = "dsp.dcf.risk_free_tenor.v1"
DCF_RISK_FREE_MATURITY_POLICY = "POLICY_GAP"
DCF_RISK_FREE_PREFERRED_MATURITY: str | None = None
DCF_RISK_FREE_REQUIRED_MATURITY: str | None = None
DCF_RISK_FREE_ACCEPTABLE_ALTERNATIVES: tuple[str, ...] = ()
DCF_RISK_FREE_MAX_MISMATCH: str | None = None
DCF_RISK_FREE_UNLABELED_TREATMENT = "VERIFIED_OBSERVATION_NON_BINDING"
DCF_RISK_FREE_STALE_TREATMENT = "RESEARCH_REQUIRED"
DCF_RISK_FREE_CURRENCY_POLICY = "INR_FOR_INDIAN_EQUITY_NO_FX"
DCF_RISK_FREE_CONFLICT_TREATMENT = "REVIEW_REQUIRED"
DCF_RISK_FREE_MULTIPLE_MATURITIES = "REVIEW_REQUIRED"
DCF_RISK_FREE_OBSERVATION_VS_VALUATION = (
    "as_of must be on or before valuation_date; retrieved_at is not as_of"
)
DCF_RISK_FREE_FRESHNESS_DAYS = 30
DCF_RISK_FREE_KNOWN_MATURITY_REQUIRED_TO_BIND = True

GOVERNMENT_YIELD_KINDS = frozenset(
    {
        "treasury_bill",
        "g_sec",
        "goi_dated_security",
    }
)
REJECTED_RISK_FREE_KINDS = frozenset(
    {
        "bank_rate",
        "mclr",
        "repo_rate",
        "reverse_repo",
        "crr",
        "slr",
        "msf",
        "sdf",
        "policy_rate",
        "inflation",
        "cpi",
        "wpi",
        "corporate_bond",
        "unknown",
    }
)


def evaluate_risk_free_binding(
    *,
    instrument_kind: str,
    maturity: str,
    required_maturity: str | None = DCF_RISK_FREE_REQUIRED_MATURITY,
    maturity_policy: str = DCF_RISK_FREE_MATURITY_POLICY,
) -> str:
    """Bind a government yield as DCF risk_free_rate only when tenor policy matches.

    POLICY_GAP: never BOUND, even for a labeled 10-year G-sec.
    When a required tenor exists: unlabeled → REVIEW_REQUIRED; mismatch → POLICY_MISMATCH.
    """
    kind = str(instrument_kind or "").strip().lower()
    if kind in REJECTED_RISK_FREE_KINDS or kind not in GOVERNMENT_YIELD_KINDS:
        return "REJECTED"
    if maturity_policy == "POLICY_GAP" or required_maturity is None:
        return "POLICY_GAP"
    observed = str(maturity or "").strip().lower()
    required = str(required_maturity).strip().lower()
    if not observed or observed in {"unspecified", "unknown", "not_applicable"}:
        return "REVIEW_REQUIRED"
    if observed != required:
        return "POLICY_MISMATCH"
    return "BOUND"


def tenor_policy_public_dict() -> dict[str, Any]:
    return {
        "policy_id": DCF_RISK_FREE_TENOR_POLICY_ID,
        "maturity_policy": DCF_RISK_FREE_MATURITY_POLICY,
        "preferred_maturity": DCF_RISK_FREE_PREFERRED_MATURITY,
        "required_maturity": DCF_RISK_FREE_REQUIRED_MATURITY,
        "acceptable_alternatives": list(DCF_RISK_FREE_ACCEPTABLE_ALTERNATIVES),
        "maximum_maturity_mismatch": DCF_RISK_FREE_MAX_MISMATCH,
        "unlabeled_treatment": DCF_RISK_FREE_UNLABELED_TREATMENT,
        "known_maturity_required_to_bind": DCF_RISK_FREE_KNOWN_MATURITY_REQUIRED_TO_BIND,
        "observation_vs_valuation": DCF_RISK_FREE_OBSERVATION_VS_VALUATION,
        "stale_treatment": DCF_RISK_FREE_STALE_TREATMENT,
        "freshness_days": DCF_RISK_FREE_FRESHNESS_DAYS,
        "currency_policy": DCF_RISK_FREE_CURRENCY_POLICY,
        "conflict_treatment": DCF_RISK_FREE_CONFLICT_TREATMENT,
        "multiple_eligible_maturities": DCF_RISK_FREE_MULTIPLE_MATURITIES,
        "basis": (
            "CapmInputs and official DcfMethod name no G-sec/T-bill tenor; "
            "RS-004 does not specify one; SIMPLE-28 left POLICY_GAP"
        ),
    }
