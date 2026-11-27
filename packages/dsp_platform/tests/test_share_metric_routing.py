import pytest

from dsp_platform.research_retrieval.service import (
    _is_share_count_metric,
)


@pytest.mark.parametrize(
    "metric",
    [
        "shares",
        "SHARE_COUNT",
        "OUTSTANDING_SHARES",
        "shares outstanding",
        "period-end shares",
        "issued_equity_shares",
        "outstanding equity shares",
    ],
)
def test_share_count_routing(metric):
    assert _is_share_count_metric(metric)


@pytest.mark.parametrize(
    "metric",
    [
        None,
        "",
        "revenue",
        "net_profit",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_per_share",
        "share_price",
    ],
)
def test_other_metrics_not_misclassified(metric):
    assert not _is_share_count_metric(metric)
