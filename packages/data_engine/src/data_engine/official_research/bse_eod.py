"""BSE EOD is a separate venue (MIC=XBOM). Not required for MVP price retrieval.

NSE ClsPric and BSE close are never averaged or merged. A difference is not
a data conflict — they are different markets.
"""

from __future__ import annotations

__all__ = ["BSE_MIC", "BSE_VENUE", "BseEodNotRequired"]

BSE_MIC = "XBOM"
BSE_VENUE = "BSE"


class BseEodNotRequired(LookupError):
    """Raised when a caller requires BSE EOD during the NSE-only MVP."""


class BseEodService:
    """Architectural placeholder. MVP official price path is NSE UDiFF EOD."""

    def fetch_latest(self) -> None:
        raise BseEodNotRequired(
            "BSE EOD is a separate venue and is not required for MVP price retrieval"
        )
