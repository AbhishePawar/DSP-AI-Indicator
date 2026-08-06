"""Static reference data — public taxonomies and disclosed heuristic thresholds.

Nothing here is fabricated company/market data. ``GICS_SECTORS`` is the
published 11-sector Global Industry Classification Standard taxonomy, used
only as a comparison baseline to detect zero-exposure ("missing") sectors.
The threshold constants are disclosed, documented heuristics (see
``docs/PORTFOLIO_GUIDE.md``) — callers may override every one of them.
"""

from __future__ import annotations

__all__ = [
    "CAP_BUCKETS",
    "CONCENTRATION_COUNTRY_FLAG_PCT",
    "CONCENTRATION_INDUSTRY_FLAG_PCT",
    "CONCENTRATION_SECTOR_FLAG_PCT",
    "CONCENTRATION_SINGLE_POSITION_FLAG_PCT",
    "CONCENTRATION_STYLE_FLAG_PCT",
    "DRIFT_BAND_PCT",
    "GICS_SECTORS",
    "STYLE_BUCKETS",
    "VALUATION_OVERVALUED_THRESHOLD",
    "VALUATION_UNDERVALUED_THRESHOLD",
]

#: The 11 GICS sectors (published, public taxonomy) — used only to flag
#: sectors with zero portfolio exposure ("missing sectors").
GICS_SECTORS: tuple[str, ...] = (
    "Energy",
    "Materials",
    "Industrials",
    "Consumer Discretionary",
    "Consumer Staples",
    "Health Care",
    "Financials",
    "Information Technology",
    "Communication Services",
    "Utilities",
    "Real Estate",
)

STYLE_BUCKETS: tuple[str, ...] = ("growth", "value", "blend")
CAP_BUCKETS: tuple[str, ...] = ("large", "mid", "small")

#: Any single position above this weight is flagged as concentrated.
CONCENTRATION_SINGLE_POSITION_FLAG_PCT = 0.10
#: Any sector above this weight is flagged as concentrated.
CONCENTRATION_SECTOR_FLAG_PCT = 0.30
#: Any industry above this weight is flagged as concentrated.
CONCENTRATION_INDUSTRY_FLAG_PCT = 0.25
#: Any style bucket above this weight is flagged as concentrated.
CONCENTRATION_STYLE_FLAG_PCT = 0.70
#: Any single country above this weight is flagged as concentrated.
CONCENTRATION_COUNTRY_FLAG_PCT = 0.60

#: Margin-of-safety threshold above which a holding is classified Undervalued.
VALUATION_UNDERVALUED_THRESHOLD = 0.15
#: Margin-of-safety threshold below which a holding is classified Overvalued.
VALUATION_OVERVALUED_THRESHOLD = -0.15

#: Relative deviation from an even baseline weight before a bucket is
#: flagged over/underweight (e.g. 0.5 = 50% above/below the even-split baseline).
DRIFT_BAND_PCT = 0.5
