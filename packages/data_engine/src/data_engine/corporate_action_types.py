"""Corporate-action classification (SIMPLE-14G).

Evidence-driven. Independent of any market-data vendor. Acquisition is
listed but is NOT automatically a share-count-changing event.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["CorporateActionType", "SHARE_COUNT_CHANGING_TYPES"]


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
