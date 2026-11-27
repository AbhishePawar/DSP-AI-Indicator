"""Cross-snapshot mutual fund identity reconciliation."""

import re

from collections import Counter

from data_engine.reference_catalog import normalize


def valid_isin(value):

    if not isinstance(value, str):
        return False

    if not re.fullmatch(
        r"[A-Z]{2}[A-Z0-9]{9}[0-9]",
        value,
    ):
        return False

    digits = "".join(
        str(ord(c) - 55) if c.isalpha() else c
        for c in value
    )

    total = 0

    for index, digit in enumerate(reversed(digits)):

        number = int(digit)

        if index % 2:

            number *= 2

            if number > 9:
                number -= 9

        total += number

    return total % 10 == 0


def reconcile_amfi_nav(snapshot, catalog):

    matched = {}
    quarantined = {}
    counts = Counter()

    for code, row in snapshot["records"].items():

        reason = None

        matches = catalog.resolve(
            "AMFI:" + code,
            exchange="AMFI",
        )

        if len(matches) != 1:

            reason = "missing_or_ambiguous_identity"

        else:

            reference = matches[0]

            observed = {
                normalize(row[key])
                for key in (
                    "isin_growth_or_payout",
                    "isin_reinvestment",
                )
                if row.get(key)
            }

            expected = set(reference.isins)

            if row.get("scheme_code") != code:

                reason = "scheme_code_mismatch"

            elif not observed or not expected:

                reason = "missing_isin"

            elif not all(
                valid_isin(isin) for isin in observed
            ):

                reason = "invalid_isin_checksum"

            elif observed != expected:

                reason = "isin_mismatch"

            elif normalize(row.get("scheme_name")) != normalize(
                reference.name
            ):

                reason = "name_mismatch"

            elif normalize(row.get("plan")) != normalize(
                reference.plan
            ):

                reason = "plan_mismatch"

            elif normalize(row.get("option")) != normalize(
                reference.option
            ):

                reason = "option_mismatch"

        if reason is not None:

            counts[reason] += 1

            quarantined[code] = reason

            continue

        matched[code] = {
            **row,
            "instrument_id": reference.instrument_id,
            "identity_status": "cross_snapshot_matched",
            "isin_checksum_valid": True,
            "independent_identity_verified": False,
            "authorized_for_valuation": False,
        }

        counts["identity_matched"] += 1

        if row.get("freshness") == "recent":

            counts["recent_identity_matched"] += 1

    return {
        "source": "AMFI",
        "source_url": snapshot.get("source_url"),
        "source_content_hash": snapshot.get(
            "content_hash"
        ),
        "source_text_hash": snapshot.get(
            "extracted_text_hash"
        ),
        "as_of": snapshot.get("as_of"),
        "input_count": len(snapshot["records"]),
        "matched_count": len(matched),
        "quarantined_count": len(quarantined),
        "counts": dict(counts),
        "records": matched,
        "quarantined": quarantined,
        "independent_identity_verified": False,
        "authorized_for_valuation": False,
    }
