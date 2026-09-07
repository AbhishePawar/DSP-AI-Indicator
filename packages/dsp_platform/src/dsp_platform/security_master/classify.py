"""Deterministic security-type and DSP type-eligibility classification.

Listed universe and DSP-eligible universe are separate. Financial-statement
availability is not decided here.
"""

from __future__ import annotations

from dsp_platform.security_master.models import (
    EligibilityStatus,
    ListingStatus,
    SecurityType,
)

__all__ = [
    "BSE_SME_GROUPS",
    "NSE_COMMON_EQUITY_SERIES",
    "NSE_SME_SERIES",
    "classify_bse_group",
    "classify_nse_series",
    "eligibility_for",
]

NSE_COMMON_EQUITY_SERIES = frozenset({"EQ", "BE", "BZ"})
NSE_SME_SERIES = frozenset({"SM", "ST", "SZ"})

# BSE List of Scrips GROUP codes observed on the official Active feed.
# M / MT / MS are SME boards. P is preference. R is rights. Other letter
# groups (A, B, T, X, XT, Z, ZP, TS, Y, IP) remain listed equity variants.
BSE_SME_GROUPS = frozenset({"M", "MT", "MS"})
BSE_PREFERENCE_GROUPS = frozenset({"P"})
BSE_RIGHTS_GROUPS = frozenset({"R"})
BSE_EQUITY_GROUPS = frozenset(
    {"A", "B", "T", "X", "XT", "Z", "ZP", "TS", "Y", "IP"}
)


def classify_nse_series(series: str, document_kind: str) -> SecurityType:
    kind = document_kind.strip().lower()
    if kind == "etf":
        return SecurityType.ETF
    if kind == "reit":
        return SecurityType.REIT
    if kind == "invit":
        return SecurityType.INVIT
    if kind == "preference":
        return SecurityType.PREFERENCE
    if kind == "warrant":
        return SecurityType.WARRANT
    if kind == "sme_equity":
        return SecurityType.SME_EQUITY
    code = series.strip().upper()
    if code in NSE_SME_SERIES:
        return SecurityType.SME_EQUITY
    if code in NSE_COMMON_EQUITY_SERIES or kind == "equity":
        if code and code not in NSE_COMMON_EQUITY_SERIES and code not in NSE_SME_SERIES:
            return SecurityType.OTHER
        return SecurityType.COMMON_EQUITY
    return SecurityType.OTHER


def classify_bse_group(group: str, document_kind: str) -> SecurityType:
    code = group.strip().upper()
    if code in BSE_SME_GROUPS:
        return SecurityType.SME_EQUITY
    if code in BSE_PREFERENCE_GROUPS:
        return SecurityType.PREFERENCE
    if code in BSE_RIGHTS_GROUPS:
        return SecurityType.OTHER
    if code in BSE_EQUITY_GROUPS or document_kind.startswith("equity"):
        if code and code not in BSE_EQUITY_GROUPS and code not in BSE_SME_GROUPS:
            return SecurityType.OTHER
        return SecurityType.COMMON_EQUITY
    return SecurityType.OTHER


def eligibility_for(
    *,
    security_type: SecurityType,
    listing_status: ListingStatus,
    identity_ok: bool,
    uniqueness_flags: tuple[str, ...],
) -> tuple[EligibilityStatus, bool, str]:
    if "duplicate_isin_mic" in uniqueness_flags:
        return (
            EligibilityStatus.IDENTITY_AMBIGUOUS,
            False,
            "duplicate ISIN+MIC in source snapshot",
        )
    if not identity_ok:
        return (
            EligibilityStatus.IDENTITY_INCOMPLETE,
            False,
            "ISIN, symbol, or MIC missing or invalid",
        )
    if listing_status is ListingStatus.SUSPENDED:
        return (EligibilityStatus.SUSPENDED, False, "exchange status is suspended")
    if listing_status is ListingStatus.DELISTED:
        return (EligibilityStatus.DELISTED, False, "exchange status is delisted")
    if listing_status is ListingStatus.UNKNOWN:
        return (EligibilityStatus.INACTIVE, False, "listing status unknown")
    if security_type in (SecurityType.COMMON_EQUITY, SecurityType.SME_EQUITY):
        return (EligibilityStatus.ELIGIBLE, True, "")
    if security_type in (
        SecurityType.ETF,
        SecurityType.REIT,
        SecurityType.INVIT,
        SecurityType.PREFERENCE,
        SecurityType.WARRANT,
        SecurityType.OTHER,
        SecurityType.UNKNOWN,
    ):
        return (
            EligibilityStatus.UNSUPPORTED_SECURITY_TYPE,
            False,
            f"security_type={security_type}",
        )
    return (EligibilityStatus.OTHER_EXCLUSION, False, f"security_type={security_type}")
