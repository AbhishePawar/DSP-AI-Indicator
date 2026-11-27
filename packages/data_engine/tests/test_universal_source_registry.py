
import pytest

from data_engine.universal_source_registry import (
    SOURCE_REGISTRY,
    get_source,
    source_matches_url,
    sources_for_capability,
)


def test_source_inventory():

    assert len(SOURCE_REGISTRY) == 70

    assert all(
        source.capabilities
        for source in SOURCE_REGISTRY.values()
    )


def test_sources_not_automatically_activated():

    assert not any(
        source.enabled
        for source in SOURCE_REGISTRY.values()
    )


def test_case_insensitive_source_lookup():

    assert get_source(" sec_edgar ").source_id == "SEC_EDGAR"


@pytest.mark.parametrize(
    "source,url",
    [
        ("SEC_EDGAR", "https://www.sec.gov/Archives/test"),
        ("NSE", "https://nsearchives.nseindia.com/report.pdf"),
        ("WORLD_BANK", "https://api.worldbank.org/v2/test"),
        ("AMFI", "https://www.amfiindia.com/test"),
        ("SCREENER", "https://www.screener.in/company/INFY/"),
        ("RBI", "https://data.rbi.org.in/"),
    ],
)
def test_known_source_domains(source, url):

    assert source_matches_url(source, url)


@pytest.mark.parametrize(
    "url",
    [
        "https://sec.gov.attacker.example/",
        "https://fake-sec.gov/",
        "http://www.sec.gov/",
        "https://www.sec.gov:8443/",
        "https://www.sec.gov@evil.example/",
        "https://user:password@www.sec.gov/",
        "https://127.0.0.1/",
        "https://www.sec.gov/\ninvalid",
        "https://www.sec.gov/invalid path",
        "https://",
    ],
)
def test_invalid_source_identity(url):

    assert not source_matches_url("SEC_EDGAR", url)


def test_unknown_source():

    assert get_source("UNKNOWN") is None

    assert not source_matches_url(
        "UNKNOWN",
        "https://example.com/",
    )


def test_ai_cannot_act_as_primary_source():

    assert get_source("OPENAI_RESEARCH").authority == "discovery_only"

    assert get_source("GEMINI_RESEARCH").authority == "discovery_only"


def test_capability_selection():

    sources = {
        source.source_id
        for source in sources_for_capability("fundamentals")
    }

    assert "NSE" in sources
    assert "SEC_EDGAR" in sources

    assert "OPENAI_RESEARCH" not in sources
    assert "WORLD_BANK" not in sources


def test_issuer_domains_require_separate_validation():

    assert not source_matches_url(
        "COMPANY_OFFICIAL",
        "https://example.com/",
    )


def test_registry_is_immutable():

    with pytest.raises(TypeError):
        SOURCE_REGISTRY["UNKNOWN"] = None
