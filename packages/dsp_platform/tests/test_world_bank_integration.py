from datetime import date

import pytest

from contracts.enums import EconomicFrequency
from contracts.domain.economic_series import (
    EconomicDataPoint,
    EconomicSeries,
)

from data_engine.exceptions import DataEngineError

from dsp_platform.config import (
    Environment,
    PlatformConfig,
    ProviderSettings,
)

from dsp_platform.world_bank_adapter import (
    WorldBankEconomicAdapter,
    INDICATOR_MAPPING,
)

from dsp_platform.wiring import (
    build_analysis_components,
)

from dsp_platform.research_retrieval.world_bank_data import (
    INDICATORS,
)

from snapshot_bridge.economic import (
    EconomicSnapshotBuilder,
)

from snapshot_bridge.exceptions import (
    SnapshotBridgeError,
)


class FakeEvidenceService:

    def __init__(self, changes=None):

        self.changes = changes or {}
        self.calls = []

    def acquire(self, indicator, **kwargs):

        self.calls.append(indicator)

        code, unit = INDICATORS[indicator]

        result = {
            "country": "IND",
            "indicator": indicator,
            "indicator_code": code,
            "unit": unit,
            "source": "WORLD_BANK",
            "content_hash": "a" * 64,
            "observations": [
                {"year": 2024, "value": "6.5"},
                {"year": 2025, "value": "7.5"},
            ],
        }

        result.update(self.changes)

        return result


@pytest.mark.parametrize(
    "code", tuple(INDICATOR_MAPPING)
)
def test_all_indicators_normalized(code):

    adapter = WorldBankEconomicAdapter(
        FakeEvidenceService()
    )

    result, evidence = adapter.acquire_with_evidence(
        code, "IN"
    )

    assert result.indicator_code == code
    assert result.country == "IN"
    assert result.frequency == EconomicFrequency.ANNUAL
    assert len(result.points) == 2

    assert result.points[-1].observation_date == (
        date(2025, 12, 31)
    )

    assert result.points[-1].value == 7.5
    assert evidence["source"] == "WORLD_BANK"


def test_unsupported_country_blocked():

    service = FakeEvidenceService()

    adapter = WorldBankEconomicAdapter(service)

    with pytest.raises(DataEngineError):

        adapter.get_economic_series(
            "GDP_GROWTH", "US"
        )

    assert not service.calls


@pytest.mark.parametrize(
    "code", ["GDP", "CPI", "UNKNOWN"]
)
def test_incompatible_indicators_rejected(code):

    service = FakeEvidenceService()

    adapter = WorldBankEconomicAdapter(service)

    with pytest.raises(DataEngineError):

        adapter.get_economic_series(code, "IN")

    assert not service.calls


def test_source_identity_mismatch():

    adapter = WorldBankEconomicAdapter(
        FakeEvidenceService({"country": "USA"})
    )

    with pytest.raises(DataEngineError):

        adapter.get_economic_series(
            "GDP_GROWTH", "IN"
        )


def test_indicator_identity_mismatch():

    adapter = WorldBankEconomicAdapter(
        FakeEvidenceService({
            "indicator": "population"
        })
    )

    with pytest.raises(DataEngineError):

        adapter.get_economic_series(
            "GDP_GROWTH", "IN"
        )


def test_empty_dataset_rejected():

    adapter = WorldBankEconomicAdapter(
        FakeEvidenceService({
            "observations": []
        })
    )

    with pytest.raises(DataEngineError):

        adapter.get_economic_series(
            "GDP_GROWTH", "IN"
        )


def make_series(code, value, unit="percent"):

    return EconomicSeries(
        indicator_code=code,
        indicator_name=code,
        country="IN",
        frequency=EconomicFrequency.ANNUAL,
        unit=unit,
        points=(
            EconomicDataPoint(
                observation_date=date(2025, 12, 31),
                value=value,
            ),
        ),
    )


def test_reported_growth_not_calculated_twice():

    snapshot = EconomicSnapshotBuilder.build(
        {
            "GDP_GROWTH": make_series(
                "GDP_GROWTH", 7.5
            ),
            "INFLATION_RATE": make_series(
                "INFLATION_RATE", 2.4
            ),
        },
        country="IN",
    )

    assert snapshot.gdp_growth == pytest.approx(0.075)
    assert snapshot.cpi_inflation == pytest.approx(0.024)

    assert snapshot.interest_rate is None
    assert snapshot.unemployment is None


def test_negative_growth_preserved():

    snapshot = EconomicSnapshotBuilder.build(
        {
            "GDP_GROWTH": make_series(
                "GDP_GROWTH", -5.0
            ),
        },
        country="IN",
    )

    assert snapshot.gdp_growth == pytest.approx(-0.05)


def test_zero_growth_preserved():

    snapshot = EconomicSnapshotBuilder.build(
        {
            "GDP_GROWTH": make_series(
                "GDP_GROWTH", 0
            ),
        },
        country="IN",
    )

    assert snapshot.gdp_growth == 0


def test_incorrect_percentage_unit_rejected():

    with pytest.raises(SnapshotBridgeError):

        EconomicSnapshotBuilder.build(
            {
                "GDP_GROWTH": make_series(
                    "GDP_GROWTH",
                    0.075,
                    unit="decimal",
                ),
            },
            country="IN",
        )


def test_world_bank_registration_without_fred_key():

    config = PlatformConfig(
        environment=Environment.DEVELOPMENT,
        providers=ProviderSettings(
            economic_provider_id="world_bank",
            enable_economic=True,
        ),
    )

    _, registry = build_analysis_components(config)

    assert registry.get(
        "world_bank"
    ).provider_name == "world_bank"


@pytest.mark.parametrize(
    "changes",
    [
        {"unit": "USD"},
        {"indicator_code": "INVALID"},
    ],
)
def test_source_metadata_mismatch(changes):

    adapter = WorldBankEconomicAdapter(
        FakeEvidenceService(changes)
    )

    with pytest.raises(DataEngineError):

        adapter.get_economic_series(
            "GDP_GROWTH", "IN"
        )


def test_cross_country_snapshot_rejected():

    from dataclasses import replace

    series = replace(
        make_series("GDP_GROWTH", 7.5),
        country="US",
    )

    with pytest.raises(
        SnapshotBridgeError,
        match="country mismatch",
    ):

        EconomicSnapshotBuilder.build(
            {"GDP_GROWTH": series},
            country="IN",
        )


def test_future_observation_rejected():

    with pytest.raises(
        SnapshotBridgeError,
        match="after requested analysis date",
    ):

        EconomicSnapshotBuilder.build(
            {
                "GDP_GROWTH": make_series(
                    "GDP_GROWTH", 7.5
                ),
            },
            country="IN",
            as_of=date(2024, 12, 31),
        )
