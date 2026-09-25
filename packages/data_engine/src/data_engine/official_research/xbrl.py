"""Generic XBRL instance extraction. Not an issuer taxonomy fork.

Facts become ExtractedField candidates only when concept, unit, period, and
statement basis are explicit. EvidenceJudge still verifies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from data_engine.official_research.extraction import (
    ExtractedField,
    canonical_share_semantic_type,
)

__all__ = [
    "XbrlExtractionResult",
    "extract_shareholding_xbrl_fields",
    "extract_xbrl_fields",
    "is_xbrl_payload",
    "xbrl_to_labeled_text",
]

_CONCEPT_FIELDS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "revenuefromoperations",
        "revenuefromoperation",
        "totalrevenuefromoperations",
        "incomefromoperations",
    ),
    "net_income": (
        "profitaftertax",
        "profitlossforperiod",
        "profitfortheyear",
        "profitfortheperiod",
        "profitattributabletoownersofthecompany",
        "profitorlossattributabletoownersofparent",
        "profitattributabletoowners",
        "netprofit",
    ),
    "cfo": (
        "netcashflowsfromoperatingactivities",
        "netcashfromoperatingactivities",
        "netcashgeneratedfromoperatingactivities",
        "cashflowsfromusedinoperatingactivities",
    ),
    "capex": (
        "capitalexpenditure",
        "capex",
        "purchaseofpropertyplantandequipmentclassifiedasinvestingactivities",
        "purchaseofpropertyplantandequipment",
        "paymentstoacquirepropertyplantandequipment",
        "paymentstopurchasepropertyplantandequipment",
        "purchaseoftangibleassetsclassifiedasinvestingactivities",
        "capitalexpenditureonpropertyplantandequipment",
        "additionstopropertyplantandequipment",
    ),
    "cash": (
        "cashandcashequivalents",
        "cashandbankbalances",
        "cashcashequivalents",
    ),
    "debt": ("borrowings", "totalborrowings", "noncurrentborrowings", "currentborrowings"),
    "equity": (
        "totalequity",
        "equityattributabletoownersofparent",
        "equityattributabletoownersofthecompany",
        "equityattributabletoowners",
        "shareholdersequity",
        "equity",
    ),
    "finance_costs": (
        "financecosts",
        "financecost",
        "interestexpense",
        "financecostsclassifiedasoperatingactivities",
        "interestpaidclassifiedasoperatingactivities",
    ),
    "total_assets": ("totalassets", "assetstotal", "assets"),
    "total_liabilities": ("totalliabilities", "liabilitiestotal", "liabilities"),
}

_SHARE_OUTSTANDING_CONCEPTS = frozenset(
    {
        "numberofequitysharesoutstanding",
        "equitysharesoutstanding",
        "totalnumberofequitysharesoutstanding",
        "noofequitysharesoutstanding",
        "numberofsharesoutstanding",
    }
)
_FORBIDDEN_SHARE_CONCEPTS = frozenset(
    {
        "weightedaverage",
        "diluted",
        "potential",
        "authorised",
        "authorized",
        "freefloat",
        "promoter",
        "facevalue",
        "paidupvalue",
        "paidupcapital",
    }
)
_PREVIOUS_HINTS = ("previous", "prior", "comparative", "preceding")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True, slots=True)
class XbrlExtractionResult:
    fields: dict[str, ExtractedField]
    issues: tuple[str, ...]
    entity_isins: tuple[str, ...]
    labeled_text: str
    identity_ok: bool


def is_xbrl_payload(payload: bytes | str) -> bool:
    raw = payload[:800] if isinstance(payload, (bytes, bytearray)) else str(payload)[:800]
    if isinstance(raw, (bytes, bytearray)):
        try:
            head = raw.decode("utf-8", errors="replace")
        except Exception:
            return False
    else:
        head = raw
    lowered = head.lstrip("\ufeff").lower()
    return "<xbrl" in lowered or "xbrli:xbrl" in lowered or "xmlns:xbrli" in lowered


def extract_xbrl_fields(
    payload: bytes | str,
    *,
    isin: str,
    preferred_basis: str = "consolidated",
    document_basis: str | None = None,
) -> XbrlExtractionResult:
    """Parse one XBRL instance. Wrong ISIN or unlabeled units stay UNKNOWN."""
    text = _decode(payload)
    if not text.strip():
        return XbrlExtractionResult({}, ("empty XBRL document",), (), "", False)
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return XbrlExtractionResult({}, ("malformed XBRL/XML",), (), "", False)
    contexts = _contexts(root)
    units = _units(root)
    isins = tuple(dict.fromkeys((*_entity_isins(contexts), *_isin_facts(root))))
    identity_ok = not isins or isin.strip().upper() in isins
    if not identity_ok:
        return XbrlExtractionResult(
            {},
            ("XBRL entity identifier does not match listing ISIN",),
            isins,
            text[:4000],
            False,
        )
    facts = _facts(root, contexts, units)
    if not facts:
        return XbrlExtractionResult(
            {},
            ("no numeric XBRL facts",),
            isins,
            xbrl_to_labeled_text({}, isins=isins),
            True,
        )
    chosen: dict[str, ExtractedField] = {}
    issues: list[str] = []
    for field, concepts in _CONCEPT_FIELDS.items():
        picked = _pick_fact(
            facts,
            concepts,
            preferred_basis=preferred_basis,
            document_basis=document_basis,
        )
        if picked is None:
            continue
        if picked.unit_scale is None or picked.currency is None:
            issues.append(f"{field} XBRL unit unlabeled")
            continue
        if picked.as_of is None:
            issues.append(f"{field} XBRL period unlabeled")
            continue
        if picked.statement_basis is None:
            issues.append(f"{field} XBRL consolidation unlabeled")
            continue
        chosen[field] = picked
    share = _pick_share_fact(
        facts, preferred_basis=preferred_basis, document_basis=document_basis
    )
    if share is not None:
        chosen["shares_outstanding"] = share
    elif "shares_outstanding" not in chosen:
        derived = _derive_paid_up_share_count(
            facts,
            root=root,
            preferred_basis=preferred_basis,
            document_basis=document_basis,
        )
        if derived is not None:
            chosen["shares_outstanding"] = derived
    if not chosen:
        issues.append("no explicitly labeled XBRL financial particulars")
    labeled = xbrl_to_labeled_text(chosen, isins=isins)
    return XbrlExtractionResult(
        chosen,
        tuple(issues),
        isins,
        labeled,
        True,
    )


def xbrl_to_labeled_text(
    fields: dict[str, ExtractedField],
    *,
    isins: tuple[str, ...] = (),
) -> str:
    """Deterministic labeled dialect for identity/CA follow-up. Not a new source."""
    lines = ["XBRL instance"]
    for item in isins:
        lines.append(f"ISIN {item}")
    if any(item.statement_basis == "consolidated" for item in fields.values()):
        lines.append("consolidated audited financial statements")
    elif any(item.statement_basis == "standalone" for item in fields.values()):
        lines.append("standalone financial statements")
    if any(item.currency == "INR" for item in fields.values()):
        lines.append("₹ INR")
    if any(item.unit_scale == "actual" for item in fields.values()):
        lines.append("unit: actual")
    as_of = next((item.as_of for item in fields.values() if item.as_of is not None), None)
    if as_of is not None:
        lines.append(f"year ended {as_of.isoformat()}")
        lines.append(f"as_of: {as_of.isoformat()}")
    labels = {
        "revenue": "Revenue from operations",
        "net_income": "Profit for the year",
        "cfo": "Net cash from operating activities",
        "capex": "capital expenditure",
        "cash": "Cash and cash equivalents",
        "debt": "Borrowings",
        "equity": "Total equity",
        "total_assets": "Total assets",
        "total_liabilities": "Total liabilities",
        "shares_outstanding": "equity shares outstanding",
    }
    for field, extracted in fields.items():
        label = labels.get(field, field)
        lines.append(f"{label} {extracted.value}")
        lines.append(f"locator: {extracted.locator}")
    return "\n".join(lines)


def _decode(payload: bytes | str) -> str:
    if isinstance(payload, str):
        return payload
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    if ":" in tag:
        return tag.split(":", 1)[-1]
    return tag


def _compact(name: str) -> str:
    return "".join(ch for ch in str(name or "").lower() if ch.isalnum())


def _text(node: ElementTree.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return str(node.text).strip()


def _child(node: ElementTree.Element, *names: str) -> ElementTree.Element | None:
    wanted = {_compact(name) for name in names}
    for child in node.iter():
        if _compact(_local(child.tag)) in wanted:
            return child
    return None


def _parse_day(raw: str) -> date | None:
    match = _DATE.search(str(raw or ""))
    if match is None:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class _Context:
    ident: str
    isin: str | None
    start: date | None
    end: date | None
    instant: date | None
    basis: str | None
    previous: bool


@dataclass(frozen=True, slots=True)
class _Unit:
    ident: str
    measure: str
    currency: str | None
    unit_scale: str | None
    kind: str


@dataclass(frozen=True, slots=True)
class _Fact:
    concept: str
    value: Decimal
    context: _Context
    unit: _Unit | None
    locator: str


def _contexts(root: ElementTree.Element) -> dict[str, _Context]:
    found: dict[str, _Context] = {}
    for node in root.iter():
        if _compact(_local(node.tag)) != "context":
            continue
        ident = str(node.attrib.get("id") or "").strip()
        if not ident:
            continue
        ident_node = _child(node, "identifier")
        isin = None
        token = _text(ident_node).upper()
        match = re.search(r"IN[A-Z0-9]{10}", token or "")
        if match:
            isin = match.group(0)
        start = _parse_day(_text(_child(node, "startDate")))
        end = _parse_day(_text(_child(node, "endDate")))
        instant = _parse_day(_text(_child(node, "instant")))
        scenario_blob = " ".join(_text(item) for item in node.iter())
        blob = f"{ident} {scenario_blob}".lower()
        basis = None
        if "non-consolidated" in blob or "nonconsolidated" in blob:
            basis = "standalone"
        elif "standalone" in blob:
            basis = "standalone"
        elif "consolidated" in blob:
            basis = "consolidated"
        previous = any(hint in blob for hint in _PREVIOUS_HINTS)
        found[ident] = _Context(
            ident=ident,
            isin=isin,
            start=start,
            end=end,
            instant=instant,
            basis=basis,
            previous=previous,
        )
    return found


def _units(root: ElementTree.Element) -> dict[str, _Unit]:
    found: dict[str, _Unit] = {}
    for node in root.iter():
        if _compact(_local(node.tag)) != "unit":
            continue
        ident = str(node.attrib.get("id") or "").strip()
        if not ident:
            continue
        measures = [
            _text(item)
            for item in node.iter()
            if _compact(_local(item.tag)) == "measure"
        ]
        measure = " ".join(part for part in measures if part)
        lowered = f"{ident} {measure}".lower()
        currency = None
        unit_scale = None
        kind = "unknown"
        if "share" in lowered or lowered.endswith(":pure") or lowered.endswith("pure"):
            kind = "shares"
            unit_scale = "actual"
        elif "crore" in lowered:
            currency = "INR"
            unit_scale = "crore_to_actual"
            kind = "money"
        elif "lakh" in lowered or "lac" in lowered:
            currency = "INR"
            unit_scale = "lakh_to_actual"
            kind = "money"
        elif "million" in lowered:
            currency = "INR" if "inr" in lowered or "iso4217" in lowered else None
            unit_scale = "million_to_actual"
            kind = "money"
        elif "iso4217:inr" in lowered or lowered.endswith("inr") or "inr" in lowered:
            currency = "INR"
            unit_scale = "actual"
            kind = "money"
        elif "usd" in lowered:
            currency = "USD"
            unit_scale = "actual"
            kind = "money"
        found[ident] = _Unit(
            ident=ident,
            measure=measure,
            currency=currency,
            unit_scale=unit_scale,
            kind=kind,
        )
    return found


def _entity_isins(contexts: dict[str, _Context]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.isin for item in contexts.values() if item.isin))


def _facts(
    root: ElementTree.Element,
    contexts: dict[str, _Context],
    units: dict[str, _Unit],
) -> list[_Fact]:
    found: list[_Fact] = []
    for node in root.iter():
        if node.get("contextRef") is None:
            continue
        concept = _local(node.tag)
        compact = _compact(concept)
        if compact in {"context", "unit", "xbrl"}:
            continue
        raw = _text(node)
        if not raw:
            continue
        try:
            value = Decimal(raw.replace(",", ""))
        except (InvalidOperation, ValueError):
            continue
        context = contexts.get(str(node.attrib.get("contextRef") or "").strip())
        if context is None:
            continue
        unit = units.get(str(node.attrib.get("unitRef") or "").strip())
        found.append(
            _Fact(
                concept=concept,
                value=value,
                context=context,
                unit=unit,
                locator=concept,
            )
        )
    return found


def _scale(value: Decimal, unit: _Unit | None) -> tuple[Decimal, str | None, str | None]:
    if unit is None or unit.unit_scale is None:
        return value, None, None
    multiplier = {
        "actual": Decimal("1"),
        "crore_to_actual": Decimal("10000000"),
        "lakh_to_actual": Decimal("100000"),
        "million_to_actual": Decimal("1000000"),
    }.get(unit.unit_scale)
    if multiplier is None:
        return value, unit.currency, None
    return value * multiplier, unit.currency, "actual"


def _rank(fact: _Fact, *, preferred_basis: str) -> tuple[int, date]:
    score = 0
    ident = fact.context.ident.lower()
    if fact.context.previous:
        score -= 50
    if any(token in ident for token in ("fourd", "year", "annual", "twelve")):
        score += 40
    if any(token in ident for token in ("oned", "threemonth", "quarter")):
        score -= 40
    if fact.context.start and fact.context.end:
        days = (fact.context.end - fact.context.start).days
        if days >= 300:
            score += 20
        elif days <= 120:
            score -= 10
    if fact.context.basis == preferred_basis:
        score += 20
    elif fact.context.basis is None:
        score -= 5
    else:
        score -= 20
    as_of = fact.context.instant or fact.context.end or date.min
    return (score, as_of)


def _to_field(
    field: str,
    fact: _Fact,
    *,
    document_basis: str | None = None,
) -> ExtractedField | None:
    if fact.unit is None:
        return None
    scaled, currency, unit_scale = _scale(fact.value, fact.unit)
    as_of = fact.context.instant or fact.context.end
    period_type = "FY"
    ident = fact.context.ident.lower()
    if any(token in ident for token in ("fourd", "year", "annual", "twelve")):
        period_type = "FY"
    elif fact.context.start and fact.context.end:
        delta = (fact.context.end - fact.context.start).days
        if delta <= 100:
            period_type = "quarter"
        elif delta <= 200:
            period_type = "half-year"
        elif delta <= 280:
            period_type = "nine-month"
        else:
            period_type = "FY"
    basis = fact.context.basis or document_basis
    return ExtractedField(
        field=field,
        value=format(scaled, "f"),
        as_of=as_of,
        locator=fact.locator,
        semantic_status="VERIFIED",
        currency=currency if field != "shares_outstanding" else None,
        raw_value=format(fact.value, "f"),
        raw_unit=fact.unit.measure or fact.unit.ident,
        unit_scale=unit_scale if field != "shares_outstanding" else "actual",
        period_start=fact.context.start,
        period_end=as_of,
        period_type=period_type,
        statement_basis=basis,
    )


_NON_CAPEX_INVESTING = frozenset(
    {
        "cashflowsfromusedininvestingactivities",
        "cashflowsusedinobtainingcontrolofsubsidiariesorotherbusinessesclassifiedasinvestingactivities",
        "purchaseofgoodwillclassifiedasinvestingactivities",
        "purchaseofintangibleassetsclassifiedasinvestingactivities",
        "purchaseofintangibleassetsunderdevelopment",
        "purchaseofinvestmentpropertyclassifiedasinvestingactivities",
        "purchaseofotherlongtermassetsclassifiedasinvestingactivities",
        "purchaseofbiologicalassetsotherthanbearerplantsclassifiedasinvestingactivities",
        "othercashpaymentstoacquireequityordebtinstrumentsofotherentitiesclassifiedasinvestingactivities",
        "otherinflowsoutflowsofcashclassifiedasinvestingactivities",
    }
)


def _capex_concept_forbidden(concept: str, *, field_concepts: set[str]) -> bool:
    compact = _compact(concept)
    if compact in _NON_CAPEX_INVESTING:
        return True
    capex_wanted = set(_CONCEPT_FIELDS["capex"])
    if field_concepts & capex_wanted and compact not in capex_wanted:
        return True
    return False


def _pick_fact(
    facts: list[_Fact],
    concepts: tuple[str, ...],
    *,
    preferred_basis: str,
    document_basis: str | None = None,
) -> ExtractedField | None:
    wanted = set(concepts)
    matches = [
        fact
        for fact in facts
        if _compact(fact.concept) in wanted
        and fact.unit is not None
        and fact.unit.kind == "money"
        and not _capex_concept_forbidden(fact.concept, field_concepts=wanted)
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: _rank(item, preferred_basis=preferred_basis), reverse=True)
    best = matches[0]
    if best.context.previous:
        return None
    field = next(
        name
        for name, labels in _CONCEPT_FIELDS.items()
        if _compact(best.concept) in labels
    )
    extracted = _to_field(field, best, document_basis=document_basis)
    if extracted is not None and extracted.period_type == "quarter":
        return None
    return extracted


def _pick_share_fact(
    facts: list[_Fact],
    *,
    preferred_basis: str,
    document_basis: str | None = None,
) -> ExtractedField | None:
    matches: list[_Fact] = []
    for fact in facts:
        compact = _compact(fact.concept)
        if any(token in compact for token in _FORBIDDEN_SHARE_CONCEPTS):
            continue
        if compact not in _SHARE_OUTSTANDING_CONCEPTS:
            continue
        if canonical_share_semantic_type(fact.concept) != "TOTAL_OUTSTANDING":
            continue
        if fact.unit is not None and fact.unit.kind not in {"shares", "unknown"}:
            continue
        matches.append(fact)
    if not matches:
        return None
    matches.sort(key=lambda item: _rank(item, preferred_basis=preferred_basis), reverse=True)
    best = matches[0]
    if best.context.previous:
        return None
    as_of = best.context.instant or best.context.end
    if as_of is None:
        return ExtractedField(
            field="shares_outstanding",
            value="",
            as_of=None,
            locator=best.locator,
            semantic_status="UNKNOWN",
            raw_value=format(best.value, "f"),
        )
    return ExtractedField(
        field="shares_outstanding",
        value=format(best.value, "f"),
        as_of=as_of,
        locator=best.locator,
        semantic_status="VERIFIED",
        raw_value=format(best.value, "f"),
        unit_scale="actual",
        period_end=as_of,
        period_type="FY",
        statement_basis=best.context.basis or document_basis,
    )


def extract_shareholding_xbrl_fields(
    payload: bytes | str,
    *,
    isin: str,
) -> XbrlExtractionResult:
    """SEBI/NSE shareholding-pattern XBRL. Category rows are not TOTAL_OUTSTANDING."""
    text = _decode(payload)
    if not text.strip():
        return XbrlExtractionResult({}, ("empty XBRL document",), (), "", False)
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return XbrlExtractionResult({}, ("malformed XBRL/XML",), (), "", False)
    contexts = _contexts(root)
    units = _units(root)
    isins = tuple(dict.fromkeys((*_entity_isins(contexts), *_isin_facts(root))))
    identity_ok = not isins or isin.strip().upper() in isins
    if not identity_ok:
        return XbrlExtractionResult(
            {},
            ("XBRL entity identifier does not match listing ISIN",),
            isins,
            text[:4000],
            False,
        )
    facts = _facts(root, contexts, units)
    report_date = _report_date(root)
    picked = _pick_shareholding_total(facts, report_date=report_date)
    fields: dict[str, ExtractedField] = {}
    issues: list[str] = []
    if picked is None:
        issues.append("shareholding pattern total fully-paid equity shares unlabeled")
    else:
        fields["shares_outstanding"] = picked
    labeled = xbrl_to_labeled_text(fields, isins=isins)
    if report_date is not None:
        labeled = f"{labeled}\nas_of: {report_date.isoformat()}\nISIN {isin}"
    return XbrlExtractionResult(fields, tuple(issues), isins, labeled, True)


def _isin_facts(root: ElementTree.Element) -> tuple[str, ...]:
    found: list[str] = []
    for node in root.iter():
        if _compact(_local(node.tag)) != "isin":
            continue
        token = _text(node).strip().upper()
        match = re.search(r"IN[A-Z0-9]{10}", token)
        if match:
            found.append(match.group(0))
    return tuple(dict.fromkeys(found))


def _report_date(root: ElementTree.Element) -> date | None:
    for node in root.iter():
        if _compact(_local(node.tag)) in {"dateofreport", "dateofshareholding", "asondate"}:
            parsed = _parse_day(_text(node))
            if parsed is not None:
                return parsed
    return None


def _category_shareholding_context(ident: str) -> bool:
    blob = ident.lower()
    if "shareholdingpattern" in blob:
        return False
    return any(
        token in blob
        for token in (
            "promoter",
            "public",
            "institution",
            "mutual",
            "insurance",
            "noninstitution",
            "custodian",
            "employee",
            "individual",
            "foreign",
            "subcategory",
            "nonpromoter",
        )
    )


def _pick_shareholding_total(
    facts: list[_Fact],
    *,
    report_date: date | None,
) -> ExtractedField | None:
    matches: list[_Fact] = []
    for fact in facts:
        compact = _compact(fact.concept)
        if compact != "numberoffullypaidupequityshares":
            continue
        if _category_shareholding_context(fact.context.ident):
            continue
        if "shareholdingpattern" not in fact.context.ident.lower():
            continue
        if fact.unit is not None and fact.unit.kind not in {"shares", "unknown"}:
            continue
        matches.append(fact)
    if not matches:
        return None
    matches.sort(key=lambda item: item.value, reverse=True)
    best = matches[0]
    as_of = report_date or best.context.instant or best.context.end
    if as_of is None:
        return ExtractedField(
            field="shares_outstanding",
            value="",
            as_of=None,
            locator="ShareholdingPattern.NumberOfFullyPaidUpEquityShares",
            semantic_status="UNKNOWN",
            raw_value=format(best.value, "f"),
        )
    return ExtractedField(
        field="shares_outstanding",
        value=format(best.value, "f"),
        as_of=as_of,
        locator="ShareholdingPattern.NumberOfFullyPaidUpEquityShares",
        semantic_status="VERIFIED",
        raw_value=format(best.value, "f"),
        unit_scale="actual",
        period_end=as_of,
        period_type="quarter",
    )


def _is_per_share_unit(unit: _Unit | None) -> bool:
    if unit is None:
        return False
    blob = f"{unit.ident} {unit.measure}".lower().replace(" ", "")
    return "pershare" in blob or ("iso4217" in blob and "share" in blob)


def _boolean_flag(root: ElementTree.Element, *names: str) -> bool | None:
    wanted = {_compact(name) for name in names}
    for node in root.iter():
        if _compact(_local(node.tag)) not in wanted:
            continue
        token = _text(node).strip().lower()
        if token in {"true", "1", "yes"}:
            return True
        if token in {"false", "0", "no"}:
            return False
    return None


def _derive_paid_up_share_count(
    facts: list[_Fact],
    *,
    root: ElementTree.Element,
    preferred_basis: str,
    document_basis: str | None,
) -> ExtractedField | None:
    """Paid-up capital / face value is PAID_UP, never a silent TOTAL_OUTSTANDING."""
    partly = _boolean_flag(
        root,
        "WhetherTheListedEntityHasIssuedAnyPartlyPaidUpShares",
        "PartlyPaidUpShares",
    )
    if partly is True:
        return None
    dvr = _boolean_flag(
        root,
        "WhetherCompanyHasEquitySharesWithDifferentialVotingRights",
    )
    if dvr is True:
        return None
    face_matches = [
        fact
        for fact in facts
        if _compact(fact.concept)
        in {"facevalueofequitysharecapital", "facevalueofequityshare"}
        and _is_per_share_unit(fact.unit)
        and fact.value > 0
        and not fact.context.previous
    ]
    paid_matches = [
        fact
        for fact in facts
        if _compact(fact.concept)
        in {
            "paidupvalueofequitysharecapital",
            "equitysharecapital",
            "paidupcapital",
        }
        and fact.unit is not None
        and fact.unit.kind == "money"
        and not _is_per_share_unit(fact.unit)
        and fact.value > 0
        and not fact.context.previous
    ]
    if not face_matches or not paid_matches:
        return None
    face_matches.sort(key=lambda item: _rank(item, preferred_basis=preferred_basis), reverse=True)
    paid_matches.sort(key=lambda item: _rank(item, preferred_basis=preferred_basis), reverse=True)
    face = face_matches[0]
    paid = next(
        (
            item
            for item in paid_matches
            if item.context.ident == face.context.ident
        ),
        paid_matches[0],
    )
    try:
        shares = (paid.value / face.value).quantize(Decimal("1"))
    except (InvalidOperation, ZeroDivisionError):
        return None
    remainder = abs((paid.value / face.value) - shares)
    if remainder > Decimal("0.01"):
        return None
    if shares <= 0:
        return None
    as_of = paid.context.instant or paid.context.end or face.context.instant or face.context.end
    return ExtractedField(
        field="shares_outstanding",
        value=format(shares, "f"),
        as_of=as_of,
        locator="derived:PaidUpValueOfEquityShareCapital/FaceValueOfEquityShareCapital",
        semantic_status="VERIFIED",
        raw_value=format(shares, "f"),
        unit_scale="actual",
        period_end=as_of,
        period_type="FY",
        statement_basis=paid.context.basis or face.context.basis or document_basis,
    )
