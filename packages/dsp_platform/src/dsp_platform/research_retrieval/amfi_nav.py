"""Governed AMFI mutual fund NAV acquisition."""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from zoneinfo import ZoneInfo

from data_engine.source_access_policy import (
    evaluate_source_access,
)

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyPolicy,
)


AMFI_URL = (
    "https://portal.amfiindia.com/spages/NAVAll.txt"
)


class AmfiNavError(ValueError):
    pass


def parse_amfi_nav(text, *, as_of=None):

    if as_of is None:
        as_of = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).date()

    records = {}
    rejected = Counter()
    conflicts = set()
    formats = Counter()

    for line in text.splitlines():

        fields = [
            field.strip()
            for field in line.split(";")
        ]

        code = fields[0] if fields else ""

        if not code.isascii() or not code.isdigit():
            continue

        if len(fields) == 8:

            (
                code, isin1, isin2, name,
                plan, option, nav, nav_date,
            ) = fields

            formats["eight_column"] += 1

        elif len(fields) == 6:

            (
                code, isin1, isin2,
                name, nav, nav_date,
            ) = fields

            plan = None
            option = None

            formats["six_column"] += 1

        else:

            rejected["unsupported_row_format"] += 1
            continue

        if not name:

            rejected["missing_name"] += 1
            continue

        try:

            number = Decimal(nav)

            if not number.is_finite() or number <= 0:

                rejected["invalid_nav"] += 1
                continue

        except InvalidOperation:

            rejected["unavailable_nav"] += 1
            continue

        try:

            observed = datetime.strptime(
                nav_date, "%d-%b-%Y"
            ).date()

        except ValueError:

            rejected["invalid_date"] += 1
            continue

        if observed > as_of:

            rejected["future_date"] += 1
            continue

        age = (as_of - observed).days

        record = {
            "scheme_code": code,
            "scheme_name": name,
            "isin_growth_or_payout": (
                isin1 if isin1 not in ("", "-") else None
            ),
            "isin_reinvestment": (
                isin2 if isin2 not in ("", "-") else None
            ),
            "plan": plan or None,
            "option": option or None,
            "nav": str(number),
            "currency": "INR",
            "nav_date": observed.isoformat(),
            "age_days": age,
            "freshness": (
                "recent" if age <= 7 else "historical"
            ),
        }

        if code in conflicts:
            continue

        if (
            code in records
            and records[code] != record
        ):

            conflicts.add(code)
            records.pop(code, None)
            continue

        records[code] = record

    if not records:

        raise AmfiNavError(
            "No valid AMFI NAV observations"
        )

    return {
        "as_of": as_of.isoformat(),
        "records": records,
        "record_count": len(records),
        "conflicting_scheme_codes": sorted(conflicts),
        "rejected": dict(rejected),
        "formats": dict(formats),
        "recent_count": sum(
            item["freshness"] == "recent"
            for item in records.values()
        ),
    }


class AmfiNavService:

    def __init__(self, fetcher=None):

        self.fetcher = (
            fetcher if fetcher is not None else
            DefaultSafeHttpFetcher(
                policy=UrlSafetyPolicy(
                    timeout_seconds=20,
                    max_redirects=0,
                    max_body_bytes=15_000_000,
                )
            )
        )

    def acquire(self):

        access = evaluate_source_access(
            "AMFI",
            "fund_nav",
            AMFI_URL,
        )

        if not access.permitted:
            raise AmfiNavError(access.reason)

        document = self.fetcher.fetch(AMFI_URL)

        if (
            document.status_code != 200
            or document.url != AMFI_URL
            or document.final_url != AMFI_URL
            or document.redirect_chain
        ):

            raise AmfiNavError(
                "Unexpected AMFI source destination"
            )

        result = parse_amfi_nav(
            document.text_content
        )

        return {
            **result,
            "source": "AMFI",
            "source_url": AMFI_URL,
            "content_hash": document.content_hash,
            "extracted_text_hash": sha256(
                document.text_content.encode("utf-8")
            ).hexdigest(),
            "retrieved_at": document.fetched_at,
            "evidence_class": "public_amfi_nav_dataset",
            "scheme_identity_reconciled": False,
            "authenticated_provider": False,
            "authorized_for_valuation": False,
        }
