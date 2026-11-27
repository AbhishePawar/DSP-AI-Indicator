"""Structured SEC financial evidence acquisition.

Public regulatory evidence is not an authenticated commercial feed
and does not independently authorize production valuation.
"""

import json
import re

from datetime import date
from decimal import Decimal
from types import MappingProxyType
from urllib.parse import quote

from data_engine.source_access_policy import (
    evaluate_source_access,
)

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyPolicy,
)


ISSUERS = MappingProxyType({
    ("NSE", "INFY"): {
        "cik": "0001067491",
        "isin": "INE009A01021",
        "name": "Infosys",
    },
    ("NSE", "HDFCBANK"): {
        "cik": "0001144967",
        "isin": "INE040A01034",
        "name": "HDFC Bank",
    },
})


class SecFactsError(ValueError):
    pass


class SecCompanyFactsService:

    def __init__(self, fetcher=None):

        self.fetcher = fetcher if fetcher is not None else (
            DefaultSafeHttpFetcher(
                policy=UrlSafetyPolicy(
                    timeout_seconds=15,
                    max_redirects=0,
                    max_body_bytes=20_000_000,
                )
            )
        )

    def _fetch_json(self, url):

        if url.startswith(
            "https://data.sec.gov/submissions/"
        ):
            source_id = "SEC_SUBMISSIONS"
            capability = "filing_discovery"

        elif url.startswith(
            "https://data.sec.gov/api/xbrl/companyfacts/"
        ):
            source_id = "SEC_COMPANY_FACTS"
            capability = "structured_fundamentals"

        else:
            raise SecFactsError(
                "Unsupported SEC endpoint"
            )

        access = evaluate_source_access(
            source_id,
            capability,
            url,
        )

        if not access.permitted:
            raise SecFactsError(access.reason)

        document = self.fetcher.fetch(url)

        if (
            document.status_code != 200
            or document.url != url
            or document.final_url != url
            or document.redirect_chain
        ):
            raise SecFactsError(
                "Unexpected SEC document destination"
            )

        try:

            data = json.loads(
                document.text_content,
                parse_float=Decimal,
            )

        except (ValueError, TypeError):

            raise SecFactsError(
                "Invalid SEC structured response"
            ) from None

        if not isinstance(data, dict):
            raise SecFactsError(
                "Unexpected SEC response structure"
            )

        return data, document

    def acquire(
        self,
        ticker,
        *,
        exchange,
        fiscal_year,
    ):

        ticker = str(ticker).strip().upper()
        exchange = str(exchange).strip().upper()

        issuer = ISSUERS.get((exchange, ticker))

        if issuer is None:
            raise SecFactsError(
                "Unregistered SEC issuer identity"
            )

        if (
            type(fiscal_year) is not int
            or not 1990 <= fiscal_year <= date.today().year
        ):
            raise SecFactsError("Invalid reporting year")

        period_end = f"{fiscal_year}-03-31"
        period_start = f"{fiscal_year - 1}-04-01"

        cik = issuer["cik"]

        submissions_url = (
            "https://data.sec.gov/submissions/"
            f"CIK{cik}.json"
        )

        submissions, index_document = self._fetch_json(
            submissions_url
        )

        if str(submissions.get("cik")).zfill(10) != cik:
            raise SecFactsError("SEC index identity mismatch")

        recent = submissions["filings"]["recent"]

        if any(
            form == "20-F/A"
            and recent["reportDate"][i] == period_end
            for i, form in enumerate(recent["form"])
        ):
            raise SecFactsError(
                "Amended annual filing requires reconciliation"
            )

        filings = {}

        for i, form in enumerate(recent["form"]):

            if form != "20-F":
                continue

            if recent["reportDate"][i] != period_end:
                continue

            accession = recent["accessionNumber"][i]

            if not re.fullmatch(
                r"\d{10}-\d{2}-\d{6}", accession
            ):
                continue

            filed = date.fromisoformat(
                recent["filingDate"][i]
            )

            if not (
                date.fromisoformat(period_end)
                <= filed
                <= date.today()
            ):
                continue

            primary_document = recent["primaryDocument"][i]

            if not re.fullmatch(
                r"[A-Za-z0-9_.-]+", primary_document
            ):
                continue

            filings[accession] = {
                "accession": accession,
                "filed": filed.isoformat(),
                "form": form,
                "period_end": period_end,
                "url": (
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{int(cik)}/"
                    f"{accession.replace('-', '')}/"
                    f"{quote(primary_document)}"
                ),
            }

        if len(filings) != 1:

            raise SecFactsError(
                "Missing or ambiguous original annual filing"
            )

        accession, filing = next(iter(filings.items()))

        facts_url = (
            "https://data.sec.gov/api/xbrl/companyfacts/"
            f"CIK{cik}.json"
        )

        payload, document = self._fetch_json(facts_url)

        if str(payload.get("cik")).zfill(10) != cik:
            raise SecFactsError("SEC facts identity mismatch")

        facts = []
        conflicts = []

        for taxonomy, concepts in payload.get(
            "facts", {}
        ).items():

            for concept, definition in concepts.items():

                for unit, observations in definition.get(
                    "units", {}
                ).items():

                    grouped = {}

                    for item in observations:

                        if item.get("accn") != accession:
                            continue

                        if item.get("form") != "20-F":
                            continue

                        if item.get("filed") != filing["filed"]:
                            continue

                        if item.get("end") != period_end:
                            continue

                        start = item.get("start")

                        if start not in (None, period_start):
                            continue

                        value = item.get("val")

                        if (
                            isinstance(value, bool)
                            or not isinstance(
                                value, (int, Decimal)
                            )
                        ):
                            continue

                        number = Decimal(value)

                        if not number.is_finite():
                            continue

                        grouped.setdefault(
                            start, set()
                        ).add(number)

                    for start, values in grouped.items():

                        if len(values) != 1:

                            conflicts.append({
                                "taxonomy": taxonomy,
                                "concept": concept,
                                "unit": unit,
                                "start": start,
                                "end": period_end,
                                "values": [
                                    str(v)
                                    for v in sorted(values)
                                ],
                            })

                            continue

                        facts.append({
                            "taxonomy": taxonomy,
                            "concept": concept,
                            "label": definition.get("label"),
                            "unit": unit,
                            "value": str(next(iter(values))),
                            "start": start,
                            "end": period_end,
                            "accession": accession,
                            "filed": filing["filed"],
                        })

        if not facts:
            raise SecFactsError(
                "No eligible annual fact candidates"
            )

        return {
            "ticker": ticker,
            "exchange": exchange,
            "isin": issuer["isin"],
            "cik": cik,
            "issuer": payload.get("entityName"),
            "fiscal_year": fiscal_year,
            "filing": filing,
            "source_url": facts_url,
            "content_hash": document.content_hash,
            "index_content_hash": index_document.content_hash,
            "retrieved_at": document.fetched_at,
            "facts": facts,
            "conflicts": conflicts,
            "evidence_class": "public_regulatory_fact_candidates",
            "authenticated_provider": False,
            "financial_evidence_verified": False,
            "authorized_for_valuation": False,
        }
