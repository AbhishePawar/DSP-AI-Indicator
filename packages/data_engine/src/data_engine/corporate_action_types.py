"""Corporate-action classification (SIMPLE-14G / SIMPLE-14H).

Evidence-driven. Independent of any market-data vendor. Acquisition is
listed but is NOT automatically a share-count-changing event.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AcquisitionConsideration",
    "CorporateActionType",
    "SHARE_COUNT_CHANGING_TYPES",
    "classify_acquisition_consideration",
]


class CorporateActionType(StrEnum):
    BONUS = "bonus"
    SPLIT = "split"
    RIGHTS = "rights"
    QIP = "qip"
    FPO = "fpo"
    PREFERENTIAL_ISSUE = "preferential_issue"
    ESOP = "esop"
    WARRANTS = "warrants"
    CONVERSIONS = "conversions"
    NEW_ISSUANCE = "new_issuance"
    BUYBACK = "buyback"
    CANCELLATION = "cancellation"
    CAPITAL_REDUCTION = "capital_reduction"
    MERGER = "merger"
    DEMERGER = "demerger"
    SCHEME = "scheme"
    ACQUISITION = "acquisition"
    SHARE_SWAP = "share_swap"


class AcquisitionConsideration(StrEnum):
    CASH = "cash"
    SHARE = "share"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# Acquisition is omitted: it must not automatically change share count.
SHARE_COUNT_CHANGING_TYPES = frozenset(
    {
        CorporateActionType.BONUS,
        CorporateActionType.SPLIT,
        CorporateActionType.RIGHTS,
        CorporateActionType.QIP,
        CorporateActionType.FPO,
        CorporateActionType.PREFERENTIAL_ISSUE,
        CorporateActionType.ESOP,
        CorporateActionType.WARRANTS,
        CorporateActionType.CONVERSIONS,
        CorporateActionType.NEW_ISSUANCE,
        CorporateActionType.BUYBACK,
        CorporateActionType.CANCELLATION,
        CorporateActionType.CAPITAL_REDUCTION,
        CorporateActionType.MERGER,
        CorporateActionType.DEMERGER,
        CorporateActionType.SCHEME,
        CorporateActionType.SHARE_SWAP,
    }
)


def classify_acquisition_consideration(raw: str | None) -> AcquisitionConsideration:
    key = str(raw or "").strip().lower()
    if key in {"cash", "all-cash", "all_cash"}:
        return AcquisitionConsideration.CASH
    if key in {"share", "stock", "scrip", "all-stock", "all_stock"}:
        return AcquisitionConsideration.SHARE
    if key in {"mixed", "cash_and_share", "cash+stock"}:
        return AcquisitionConsideration.MIXED
    return AcquisitionConsideration.UNKNOWN
