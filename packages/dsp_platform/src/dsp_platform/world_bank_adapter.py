"""World Bank integration with existing economic data contracts."""

from datetime import date
from types import MappingProxyType

from contracts.enums import EconomicFrequency

from data_engine.adapters import BaseAdapter
from data_engine.ports import EconomicDataPort
from data_engine.exceptions import DataEngineError
from data_engine.normalization import DefaultEconomicNormalizer
from data_engine.raw_models import (
    RawEconomicDataPoint,
    RawEconomicSeries,
)

from dsp_platform.research_retrieval.world_bank_data import (
    INDICATORS,
    WorldBankDataService,
)


INDICATOR_MAPPING = MappingProxyType({
    "GDP_GROWTH": (
        "gdp_growth", "Reported real GDP growth"
    ),
    "GDP_CURRENT_USD": (
        "gdp_current_usd", "GDP at current USD"
    ),
    "INFLATION_RATE": (
        "inflation", "Reported consumer price inflation"
    ),
    "POPULATION": (
        "population", "Population"
    ),
    "DOMESTIC_CREDIT_GDP": (
        "domestic_credit", "Domestic credit as share of GDP"
    ),
    "MARKET_CAP_GDP": (
        "market_cap_gdp", "Market capitalization as share of GDP"
    ),
    "CAPITAL_FORMATION_GDP": (
        "capital_formation", "Capital formation as share of GDP"
    ),
    "FDI_GDP": (
        "foreign_direct_investment",
        "Foreign direct investment as share of GDP"
    ),
})


class WorldBankEconomicAdapter(
    BaseAdapter,
    EconomicDataPort,
):

    def __init__(self, service=None):

        self._service = (
            service if service is not None
            else WorldBankDataService()
        )

        self._normalizer = DefaultEconomicNormalizer()

    @property
    def provider_name(self):

        return "world_bank"

    def acquire_with_evidence(
        self, indicator_code, country
    ):

        code = indicator_code.strip().upper()

        if country.strip().upper() != "IN":

            raise DataEngineError(
                "World Bank adapter currently supports India only"
            )

        definition = INDICATOR_MAPPING.get(code)

        if definition is None:

            raise DataEngineError(
                "Unsupported World Bank indicator"
            )

        source_code, name = definition

        try:

            evidence = self._service.acquire(
                source_code,
                start_year=2000,
            )

            if (
                evidence["country"] != "IND"
                or evidence["indicator"] != source_code
                or evidence["indicator_code"]
                != INDICATORS[source_code][0]
                or evidence["unit"]
                != INDICATORS[source_code][1]
            ):

                raise DataEngineError(
                    "Economic source identity mismatch"
                )

            raw = RawEconomicSeries(
                provider_id=self.provider_name,
                indicator_code=code,
                indicator_name=name,
                country="IN",
                frequency=EconomicFrequency.ANNUAL,
                unit=evidence["unit"],
                points=tuple(
                    RawEconomicDataPoint(
                        observation_date=date(
                            row["year"], 12, 31
                        ),
                        value=row["value"],
                    )
                    for row in evidence["observations"]
                ),
            )

            return (
                self._normalizer.normalize(raw),
                evidence,
            )

        except DataEngineError:
            raise

        except Exception as exc:

            raise DataEngineError(
                "World Bank economic acquisition failed: "
                + type(exc).__name__
            ) from exc

    def get_economic_series(
        self, indicator_code, country
    ):

        series, _evidence = self.acquire_with_evidence(
            indicator_code, country
        )

        return series
