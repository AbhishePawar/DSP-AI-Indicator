
from datetime import date
from types import SimpleNamespace

import pytest

from dsp_platform.research_retrieval.amfi_nav import (
    AMFI_URL,
    AmfiNavError,
    AmfiNavService,
    parse_amfi_nav,
)

from data_engine.source_access_policy import (
    evaluate_source_access,
)


AS_OF = date(2026, 11, 27)

DIRECT = (
    "135762;INF846K01WO1;-;Axis Children's Fund;"
    "Direct Plan;Growth Option;31.4008;27-Nov-2026"
)

REGULAR = (
    "135759;INF846K01WJ1;-;Axis Children's Fund;"
    "Regular Plan;Growth Option;27.2964;27-Nov-2026"
)

LEGACY = (
    "123456;INF846K01WO1;-;Example Fund;"
    "25.5;27-Nov-2026"
)


def parse(text):

    return parse_amfi_nav(text, as_of=AS_OF)


def test_eight_column_format():

    result = parse(DIRECT)

    item = result["records"]["135762"]

    assert item["nav"] == "31.4008"
    assert item["plan"] == "Direct Plan"
    assert item["option"] == "Growth Option"
    assert item["currency"] == "INR"


def test_legacy_format():

    item = parse(LEGACY)["records"]["123456"]

    assert item["nav"] == "25.5"
    assert item["plan"] is None
    assert item["option"] is None


def test_direct_regular_not_combined():

    result = parse(DIRECT + "\n" + REGULAR)

    assert result["record_count"] == 2

    assert (
        result["records"]["135762"]["nav"]
        != result["records"]["135759"]["nav"]
    )


def test_duplicate_record_deduplicated():

    result = parse(DIRECT + "\n" + DIRECT)

    assert result["record_count"] == 1


def test_conflicting_records_quarantined():

    conflict = DIRECT.replace(
        "31.4008", "99.9999"
    )

    result = parse(
        DIRECT + "\n" + conflict + "\n" + REGULAR
    )

    assert "135762" not in result["records"]

    assert result["conflicting_scheme_codes"] == [
        "135762"
    ]


def test_conflict_cannot_be_reintroduced():

    conflict = DIRECT.replace(
        "31.4008", "99.9999"
    )

    result = parse(
        "\n".join([
            DIRECT, conflict, DIRECT, REGULAR
        ])
    )

    assert "135762" not in result["records"]


@pytest.mark.parametrize(
    "value",
    [
        "0", "-1", "N.A.", "",
        "Infinity", "NaN",
    ],
)
def test_invalid_nav_rejected(value):

    with pytest.raises(AmfiNavError):

        parse(DIRECT.replace("31.4008", value))


def test_future_nav_rejected():

    with pytest.raises(AmfiNavError):

        parse(DIRECT.replace(
            "27-Nov-2026", "28-Nov-2026"
        ))


def test_invalid_date_rejected():

    with pytest.raises(AmfiNavError):

        parse(DIRECT.replace(
            "27-Nov-2026", "invalid"
        ))


def test_historical_nav_preserved():

    result = parse(DIRECT.replace(
        "27-Nov-2026", "01-Nov-2026"
    ))

    assert result["recent_count"] == 0

    assert (
        result["records"]["135762"]["freshness"]
        == "historical"
    )


def test_header_and_group_rows_ignored():

    result = parse(
        "Scheme Code;Scheme Name\n"
        "Open Ended Schemes\n"
        "Axis Mutual Fund\n"
        + DIRECT
    )

    assert result["record_count"] == 1


def test_malformed_dataset_rejected():

    with pytest.raises(AmfiNavError):

        parse("<html>Not a NAV dataset</html>")


def test_exact_amfi_endpoint_permitted():

    assert evaluate_source_access(
        "AMFI", "fund_nav", AMFI_URL
    ).permitted


@pytest.mark.parametrize(
    "url",
    [
        AMFI_URL + "?redirect=example",
        AMFI_URL + "#fragment",
        "https://portal.amfiindia.com/other.txt",
        "https://amfiindia.com.attacker.example/",
        "https://www.amfiindia.com/spages/NAVAll.txt",
    ],
)
def test_other_amfi_endpoints_rejected(url):

    assert not evaluate_source_access(
        "AMFI", "fund_nav", url
    ).permitted


class FakeFetcher:

    def __init__(self, redirected=False):

        self.redirected = redirected

    def fetch(self, url):

        today = date.today().strftime(
            "%d-%b-%Y"
        )

        return SimpleNamespace(
            status_code=200,
            url=url,
            final_url=(
                "https://example.com/"
                if self.redirected else url
            ),
            redirect_chain=(
                (url,) if self.redirected else ()
            ),
            text_content=DIRECT.replace(
                "27-Nov-2026", today
            ),
            content_hash="a" * 64,
            fetched_at="2026-11-27T00:00:00Z",
        )


def test_connector_preserves_provenance():

    result = AmfiNavService(
        FakeFetcher()
    ).acquire()

    assert result["source"] == "AMFI"
    assert result["source_url"] == AMFI_URL
    assert result["content_hash"] == "a" * 64
    assert not result["authorized_for_valuation"]
    assert not result["scheme_identity_reconciled"]


def test_connector_rejects_redirect():

    with pytest.raises(AmfiNavError):

        AmfiNavService(
            FakeFetcher(redirected=True)
        ).acquire()
