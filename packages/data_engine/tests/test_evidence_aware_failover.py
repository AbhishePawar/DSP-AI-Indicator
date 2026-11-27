from types import SimpleNamespace

from data_engine.connector_framework.failover import (
    FailoverGroup,
)


class Audit:

    def __init__(self):

        self.events = []

    def record(self, event, **kwargs):

        self.events.append((event, kwargs))


def provider(provider_id, result):

    return SimpleNamespace(
        provider_id=provider_id,
        result=result,
    )


def group(providers, validator=None):

    return FailoverGroup(
        providers,
        call=lambda service, query: service.result,
        domain="fundamentals",
        operation="annual_statements",
        audit=Audit(),
        validate_result=validator,
    )


def complete(result):

    return all(
        result.get(key) is not None
        for key in (
            "revenue",
            "net_income",
            "total_assets",
            "operating_cash_flow",
        )
    )


COMPLETE = {
    "revenue": 1000,
    "net_income": 100,
    "total_assets": 2000,
    "operating_cash_flow": 150,
}


def test_incomplete_source_does_not_stop_failover():

    result = group(
        [
            provider("sec_facts", {"shares": 500}),
            provider("official_filing", COMPLETE),
        ],
        complete,
    ).call("INFY")

    assert result.provider_id == "official_filing"

    assert result.attempted_provider_ids == (
        "sec_facts",
        "official_filing",
    )


def test_complete_first_provider_accepted():

    result = group(
        [
            provider("primary", COMPLETE),
            provider("secondary", COMPLETE),
        ],
        complete,
    ).call("INFY")

    assert result.provider_id == "primary"

    assert result.attempted_provider_ids == (
        "primary",
    )


def test_all_incomplete_sources_return_unavailable():

    result = group(
        [
            provider("a", {"shares": 500}),
            provider("b", {"revenue": 1000}),
        ],
        complete,
    ).call("INFY")

    assert result is None


def test_missing_source_triggers_fallback():

    result = group(
        [
            provider("a", None),
            provider("b", COMPLETE),
        ],
        complete,
    ).call("INFY")

    assert result.provider_id == "b"


def test_validator_failure_triggers_fallback():

    def validate(result):

        if result.get("malformed"):
            raise ValueError("Malformed evidence")

        return complete(result)

    result = group(
        [
            provider("a", {"malformed": True}),
            provider("b", COMPLETE),
        ],
        validate,
    ).call("INFY")

    assert result.provider_id == "b"


def test_existing_behavior_preserved_without_validator():

    result = group(
        [provider("legacy", {"shares": 500})]
    ).call("INFY")

    assert result.provider_id == "legacy"


def test_reported_zero_not_treated_as_missing():

    zero_profit = {
        **COMPLETE,
        "net_income": 0,
    }

    result = group(
        [provider("primary", zero_profit)],
        complete,
    ).call("INFY")

    assert result is not None


def test_insufficient_evidence_is_audited():

    audit = Audit()

    router = FailoverGroup(
        [
            provider("a", {"shares": 500}),
            provider("b", COMPLETE),
        ],
        call=lambda service, query: service.result,
        domain="fundamentals",
        operation="annual_statements",
        audit=audit,
        validate_result=complete,
    )

    result = router.call("INFY")

    assert result.provider_id == "b"

    assert any(
        event == "insufficient_evidence"
        and kwargs["provider_id"] == "a"
        for event, kwargs in audit.events
    )
