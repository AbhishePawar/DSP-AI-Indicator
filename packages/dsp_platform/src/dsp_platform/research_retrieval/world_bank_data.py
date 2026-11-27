"""Governed public macroeconomic data acquisition."""

import json

from datetime import date
from decimal import Decimal
from types import MappingProxyType
from urllib.parse import urlencode

from data_engine.source_access_policy import (
    evaluate_source_access,
)

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyPolicy,
)


INDICATORS = MappingProxyType({
    "gdp_growth": (
        "NY.GDP.MKTP.KD.ZG", "percent"
    ),
    "gdp_current_usd": (
        "NY.GDP.MKTP.CD", "USD"
    ),
    "inflation": (
        "FP.CPI.TOTL.ZG", "percent"
    ),
    "population": (
        "SP.POP.TOTL", "people"
    ),
    "domestic_credit": (
        "FS.AST.PRVT.GD.ZS", "percent_of_gdp"
    ),
    "market_cap_gdp": (
        "CM.MKT.LCAP.GD.ZS", "percent_of_gdp"
    ),
    "capital_formation": (
        "NE.GDI.TOTL.ZS", "percent_of_gdp"
    ),
    "foreign_direct_investment": (
        "BX.KLT.DINV.WD.GD.ZS", "percent_of_gdp"
    ),
})


class WorldBankDataError(ValueError):
    pass


class WorldBankDataService:

    def __init__(self, fetcher=None):

        self.fetcher = fetcher if fetcher is not None else (
            DefaultSafeHttpFetcher(
                policy=UrlSafetyPolicy(
                    timeout_seconds=10,
                    max_redirects=0,
                    max_body_bytes=2_000_000,
                )
            )
        )

    def acquire(
        self,
        indicator,
        *,
        start_year=2000,
        end_year=None,
    ):

        definition = INDICATORS.get(indicator)

        if definition is None:
            raise WorldBankDataError(
                "Unsupported economic indicator"
            )

        if end_year is None:
            end_year = date.today().year

        if (
            type(start_year) is not int
            or type(end_year) is not int
            or not 1960 <= start_year <= end_year
            or end_year > date.today().year
        ):
            raise WorldBankDataError(
                "Invalid economic reporting period"
            )

        code, unit = definition

        query = urlencode({
            "format": "json",
            "date": f"{start_year}:{end_year}",
            "per_page": 100,
        })

        url = (
            "https://api.worldbank.org/v2/country/IND/"
            f"indicator/{code}?{query}"
        )

        access = evaluate_source_access(
            "WORLD_BANK",
            "economics",
            url,
        )

        if not access.permitted:

            raise WorldBankDataError(access.reason)

        document = self.fetcher.fetch(url)

        if (
            document.status_code != 200
            or document.url != url
            or document.final_url != url
            or document.redirect_chain
        ):

            raise WorldBankDataError(
                "Unexpected source destination"
            )

        payload = json.loads(
            document.text_content,
            parse_float=Decimal,
        )

        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[0], dict)
            or not isinstance(payload[1], list)
        ):

            raise WorldBankDataError(
                "Invalid economic dataset response"
            )

        if int(payload[0].get("pages", 0)) != 1:

            raise WorldBankDataError(
                "Incomplete or paginated dataset"
            )

        observations = {}

        for item in payload[1]:

            if item.get("countryiso3code") != "IND":

                raise WorldBankDataError(
                    "Country identity mismatch"
                )

            if item.get("indicator", {}).get("id") != code:

                raise WorldBankDataError(
                    "Indicator identity mismatch"
                )

            year = int(item["date"])

            if not start_year <= year <= end_year:

                raise WorldBankDataError(
                    "Unexpected observation period"
                )

            value = item.get("value")

            if value is None:
                continue

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, Decimal))
            ):

                raise WorldBankDataError(
                    "Invalid observation value"
                )

            number = Decimal(value)

            if not number.is_finite():

                raise WorldBankDataError(
                    "Non-finite observation"
                )

            if (
                year in observations
                and observations[year] != number
            ):

                raise WorldBankDataError(
                    "Conflicting economic observations"
                )

            observations[year] = number

        if not observations:

            raise WorldBankDataError(
                "No available observations"
            )

        return {
            "country": "IND",
            "indicator": indicator,
            "indicator_code": code,
            "unit": unit,
            "source": "WORLD_BANK",
            "source_url": url,
            "content_hash": document.content_hash,
            "retrieved_at": document.fetched_at,
            "dataset_last_updated": payload[0].get(
                "lastupdated"
            ),
            "observations": [
                {
                    "year": year,
                    "value": str(value),
                }
                for year, value in sorted(
                    observations.items()
                )
            ],
            "evidence_class": "public_macroeconomic_dataset",
            "authorized_for_valuation": False,
        }
