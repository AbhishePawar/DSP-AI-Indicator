"""Deterministic PDF statement reconstruction from positional text.

Uses pypdf visitor coordinates. No LLM pairing. Ambiguous columns stay
UNKNOWN. Standalone pages never feed consolidated fields.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO

from data_engine.official_research.extraction import ExtractedField
from data_engine.official_research.semantics import semantic_field_status

__all__ = [
    "PdfSpan",
    "PeriodColumn",
    "ReconstructedRow",
    "StatementPage",
    "balance_sheet_identity",
    "extract_field_from_statements",
    "reconstruct_statement_pages",
    "spans_from_pdf",
]

_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue from operations", "total revenue", "revenue"),
    "operating_profit": ("operating profit",),
    "ebit": ("ebit", "earnings before interest and tax"),
    "net_income": (
        "profit attributable to owners",
        "profit attributable to",
        "owners of the company",
        "profit after tax",
        "profit for the year",
        "profit for the period",
        "net income",
        "net profit",
    ),
    "equity": ("shareholders equity", "shareholders' equity", "total equity", "equity"),
    "cfo": (
        "net cash from operating activities",
        "net cash generated from operating activities",
        "net cash flows from operating activities",
        "net cash flow from operating activities",
        "cash flow from operating activities",
        "cash from operations",
        "cfo",
    ),
    "capex": ("capital expenditure", "capex"),
    "cash": ("cash and cash equivalents",),
    "debt": ("total borrowings", "borrowings"),
    "total_assets": ("total assets",),
    "total_liabilities": ("total liabilities",),
}

_Y_TOL = 3.5
_X_TOL = 42.0
_AMBIGUOUS_GAP = 12.0

_PL = re.compile(
    r"statements? of profit\s*(?:and|&)\s*loss|"
    r"statement of financial performance|"
    r"statement of comprehensive income|"
    r"profit and loss account",
    re.I,
)
_BS = re.compile(r"balance sheet|statement of financial position", re.I)
_CF = re.compile(r"statement of cash flows|cash flow statement", re.I)
_STAND = re.compile(r"\bstandalone\b", re.I)
_CONS = re.compile(r"\bconsolidated\b", re.I)
_NUMBER = re.compile(r"^\(?[\d,]+(?:\.\d+)?\)?$")
_EMBEDDED_NUM = re.compile(r"\(?\d{1,3}(?:,\d{2,3})+(?:\.\d+)?\)?|\(\d{2,}\)|\(\d{1,3}(?:,\d{2,3})+\)")
_NOTE = re.compile(r"^(note|notes?)\b", re.I)
_UNIT_CRORE = re.compile(
    r"(₹|rs\.?|inr|[ih?`]).{0,16}(crore|crs)\b|"
    r"\bin crores?\b|"
    r"\(\s*[₹ih?`]?\s*(in\s+)?crores?\s*\)|"
    r"all amounts in\s+[₹ih?`]?\s*crores?",
    re.I,
)
_UNIT_MILLION = re.compile(
    r"(₹|rs\.?|inr|[ih?`]).{0,16}millions?|"
    r"\bin millions?\b|"
    r"\(\s*[ih?`]?\s*in millions?",
    re.I,
)
_UNIT_LAKH = re.compile(r"(₹|rs\.?|inr).{0,16}(lakh|lac)s?\b|\bin lakhs?\b", re.I)
_UNIT_ACTUAL = re.compile(r"\bin actuals?\b|\bin rupees \(actual\)", re.I)
_PL_STRUCT = re.compile(r"revenue from operations", re.I)
_PL_PROFIT = re.compile(
    r"profit (for the year|before tax|after tax)|consolidated net profit",
    re.I,
)
_HIGHLIGHTS = re.compile(
    r"financial highlights|year at a glance|performance highlights|"
    r"five[- ]year (summary|review|highlights)|key financial (highlights|metrics)|"
    r"board.?s report",
    re.I,
)
_MIXED_BASIS_HEADERS = re.compile(
    r"standalone.{0,80}consolidated|consolidated.{0,80}standalone",
    re.I,
)
_BS_STRUCT = re.compile(r"\btotal assets\b|\bcapital and liabilities\b", re.I)
_BS_EQ = re.compile(r"\b(total equity|equity and liabilities|capital and liabilities)\b", re.I)
_CF_STRUCT = re.compile(
    r"cash flows from operating activities|"
    r"net cash generated from operating activities|"
    r"net cash flows from operating activities|"
    r"net cash from operating activities",
    re.I,
)
_YEAR_ONLY = re.compile(r"^20\d{2}$")
_ORDINAL = re.compile(r"(\d{1,2})(?:st|nd|rd|th)", re.I)
_DOT_DATE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(20\d{2})\b")
_MONTH_YEAR = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)[.,]?\s+(20\d{2})\b",
    re.I,
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True, slots=True)
class PdfSpan:
    page: int
    x: float
    y: float
    text: str
    font_size: float | None = None


@dataclass(frozen=True, slots=True)
class PeriodColumn:
    x: float
    period_end: date
    label: str


@dataclass(frozen=True, slots=True)
class ReconstructedRow:
    label: str
    current_raw: str | None
    prior_raw: str | None
    current_period: date | None
    prior_period: date | None
    unit_scale: str | None
    currency: str | None
    basis: str | None
    page: int
    statement: str
    pairing: str
    y: float


@dataclass(frozen=True, slots=True)
class StatementPage:
    page: int
    statement_type: str
    statement_name: str
    basis: str
    unit_scale: str | None
    unit_multiplier: Decimal | None
    currency: str | None
    columns: tuple[PeriodColumn, ...]
    rows: tuple[ReconstructedRow, ...]
    spans: tuple[PdfSpan, ...]


def spans_from_pdf(
    payload: bytes, *, page_numbers: tuple[int, ...] | None = None
) -> tuple[tuple[PdfSpan, ...], ...]:
    """One visitor pass per requested page. Empty pages remain empty tuples."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ()
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        reader = PdfReader(BytesIO(payload))
    except Exception:
        return ()
    wanted = None if page_numbers is None else {int(item) for item in page_numbers}
    pages: list[tuple[PdfSpan, ...]] = []
    for index, page in enumerate(reader.pages, start=1):
        if wanted is not None and index not in wanted:
            pages.append(())
            continue
        found: list[PdfSpan] = []

        def visitor(
            text: object,
            cm: object,
            tm: object,
            font_dict: object,
            font_size: object,
            *,
            page_no: int = index,
        ) -> None:
            raw = str(text or "").strip()
            if not raw:
                return
            try:
                x = float(tm[4])  # type: ignore[index]
                y = float(tm[5])  # type: ignore[index]
            except (TypeError, IndexError, ValueError):
                return
            size = None
            try:
                if font_size is not None:
                    size = float(font_size)
            except (TypeError, ValueError):
                size = None
            found.append(PdfSpan(page=page_no, x=x, y=y, text=raw, font_size=size))

        try:
            page.extract_text(visitor_text=visitor)
        except Exception:
            found = []
        pages.append(tuple(found))
    return tuple(pages)


def _spans_from_selected_pages(
    payload: bytes, page_numbers: tuple[int, ...]
) -> dict[int, tuple[PdfSpan, ...]]:
    all_pages = spans_from_pdf(payload, page_numbers=page_numbers)
    return {
        index: spans
        for index, spans in enumerate(all_pages, start=1)
        if index in {int(item) for item in page_numbers}
    }


def reconstruct_statement_pages(
    payload: bytes,
    *,
    page_texts: tuple[str, ...] | None = None,
    precomputed_spans: tuple[tuple[PdfSpan, ...], ...] | None = None,
) -> tuple[StatementPage, ...]:
    """Build statement pages only when heading + coordinates + year columns exist."""
    if precomputed_spans is not None:
        pages = precomputed_spans
        indexed = list(enumerate(pages, start=1))
    elif page_texts:
        candidates = [
            index
            for index, text in enumerate(page_texts, start=1)
            if _statement_kind(text)[0] is not None
        ]
        expanded: set[int] = set()
        for index in candidates:
            expanded.add(index)
            if index + 1 <= len(page_texts):
                expanded.add(index + 1)
        selected = _spans_from_selected_pages(payload, tuple(sorted(expanded)))
        indexed = [(index, selected.get(index, ())) for index in sorted(expanded)]
    else:
        pages = spans_from_pdf(payload)
        indexed = list(enumerate(pages, start=1))
    rebuilt: list[StatementPage] = []
    for index, spans in indexed:
        blob = " ".join(span.text for span in spans)
        if page_texts is not None and index <= len(page_texts):
            blob = f"{page_texts[index - 1]}\n{blob}"
        previous_text = ""
        if page_texts is not None and index > 1:
            previous_text = page_texts[index - 2][-900:]
        kind, name = _statement_kind(blob, previous_text=previous_text)
        if kind is None and rebuilt and rebuilt[-1].page == index - 1:
            prev = rebuilt[-1]
            if prev.statement_type == "bs" and re.search(
                r"total liabilities|total equity and liabilities|total equity\b|"
                r"capital and liabilities",
                blob,
                re.I,
            ):
                kind, name = "bs", prev.statement_name
            elif prev.statement_type == "cf" and re.search(
                r"cash flows from (investing|financing)|cash and cash equivalents at the end",
                blob,
                re.I,
            ):
                kind, name = "cf", prev.statement_name
            elif prev.statement_type == "pl" and re.search(
                r"profit attributable|owners of the company|shareholders of the company",
                blob,
                re.I,
            ):
                kind, name = "pl", prev.statement_name
        if kind is None:
            continue
        basis = _basis(blob)
        if basis is None:
            basis = _basis(previous_text)
        if basis != "consolidated":
            continue
        if _numeric_span_count(spans) < 2:
            continue
        unit_scale, multiplier, currency = _page_unit(spans)
        if (
            unit_scale is None
            and rebuilt
            and rebuilt[-1].page == index - 1
            and rebuilt[-1].statement_type == kind
            and rebuilt[-1].unit_scale is not None
        ):
            unit_scale = rebuilt[-1].unit_scale
            multiplier = rebuilt[-1].unit_multiplier
            currency = rebuilt[-1].currency or currency
        columns = _period_columns(spans)
        if len(columns) < 2:
            continue
        rows = _rows_for_page(
            spans,
            columns=columns,
            unit_scale=unit_scale,
            currency=currency,
            basis=basis or "consolidated",
            statement=name,
            page=index,
        )
        rebuilt.append(
            StatementPage(
                page=index,
                statement_type=kind,
                statement_name=name,
                basis=basis or "consolidated",
                unit_scale=unit_scale,
                unit_multiplier=multiplier,
                currency=currency,
                columns=columns,
                rows=tuple(rows),
                spans=spans,
            )
        )
    return tuple(rebuilt)


def extract_field_from_statements(
    pages: tuple[StatementPage, ...],
    field: str,
) -> ExtractedField | None:
    """Map an explicit row to a DSP field. CONFLICT if distinct UNIQUE values."""
    requested = field.strip().lower().replace(" ", "_")
    labels = _FIELD_LABELS.get(requested)
    if labels is None:
        return None
    wanted_kind = {
        "revenue": "pl",
        "operating_profit": "pl",
        "ebit": "pl",
        "net_income": "pl",
        "equity": "bs",
        "cash": "bs",
        "debt": "bs",
        "total_assets": "bs",
        "total_liabilities": "bs",
        "cfo": "cf",
        "capex": "cf",
    }.get(requested)
    hits: list[tuple[ReconstructedRow, StatementPage, str]] = []
    for page in pages:
        if wanted_kind and page.statement_type != wanted_kind:
            continue
        if page.basis == "standalone":
            continue
        for row in page.rows:
            matched = _row_label_match(row.label, labels, requested)
            if matched is None:
                continue
            if row.pairing != "UNIQUE" or not row.current_raw:
                continue
            semantic = semantic_field_status(
                requested_field=requested, document_label=matched
            )
            if semantic != "VERIFIED":
                continue
            hits.append((row, page, matched))
    if not hits:
        return None
    if requested == "net_income":
        owners = [
            item
            for item in hits
            if (
                "attributable" in item[0].label.lower()
                or "owners of the company" in item[0].label.lower()
                or "equity holders" in item[0].label.lower()
            )
            and "non-controlling" not in item[0].label.lower()
        ]
        if owners:
            hits = owners
    distinct = {item[0].current_raw for item in hits}
    first_row, page, matched = hits[0]
    if page.unit_multiplier is None or first_row.unit_scale is None:
        return None
    locator = (
        f"page={page.page};statement={page.statement_name};"
        f"row={first_row.label};column={_column_label(page, first_row)}"
    )
    period_end = first_row.current_period
    period_start = None
    if period_end is not None and period_end.month == 3 and period_end.day == 31:
        period_start = date(period_end.year - 1, 4, 1)
    if len(distinct) > 1:
        return ExtractedField(
            field=requested,
            value="",
            as_of=period_end,
            locator=locator,
            semantic_status="CONFLICT",
            currency=first_row.currency,
            raw_value=first_row.current_raw,
            raw_unit=first_row.unit_scale,
            period_start=period_start,
            period_end=period_end,
            period_type="FY",
            statement_basis=first_row.basis,
        )
    raw = (first_row.current_raw or "").replace(",", "")
    multiplier = page.unit_multiplier or Decimal("1")
    try:
        normalized = Decimal(raw) * multiplier
    except (InvalidOperation, ValueError):
        return None
    status = "VERIFIED"
    if requested in {"total_assets", "equity", "total_liabilities"}:
        if balance_sheet_identity(pages) == "CONFLICT":
            status = "CONFLICT"
    return ExtractedField(
        field=requested,
        value=format(normalized, "f"),
        as_of=period_end,
        locator=locator,
        semantic_status=status,
        currency=first_row.currency,
        raw_value=raw,
        raw_unit=first_row.unit_scale,
        unit_scale="actual",
        period_start=period_start,
        period_end=period_end,
        period_type="FY",
        statement_basis=first_row.basis or page.basis,
    )


def _column_label(page: StatementPage, row: ReconstructedRow) -> str:
    if row.current_period is None:
        return ""
    for col in page.columns:
        if col.period_end == row.current_period:
            return col.label
    return row.current_period.isoformat()


def balance_sheet_identity(pages: tuple[StatementPage, ...]) -> str:
    """Assets = equity + liabilities. Does not rewrite extracted values."""
    assets_n = _statement_total(pages, "total assets", kind="bs")
    equity_n = _statement_total(
        pages, "total equity", kind="bs", skip=("liabilities", "attributable")
    )
    liab_n = _statement_total(pages, "total liabilities", kind="bs", skip=("equity and",))
    if assets_n is None or equity_n is None or liab_n is None:
        return "UNKNOWN"
    if assets_n == equity_n + liab_n:
        return "PASS"
    return "CONFLICT"


def _statement_total(
    pages: tuple[StatementPage, ...],
    label: str,
    *,
    kind: str,
    skip: tuple[str, ...] = (),
) -> Decimal | None:
    found: list[Decimal] = []
    for page in pages:
        if page.statement_type != kind or page.unit_multiplier is None:
            continue
        for row in page.rows:
            lowered = row.label.lower()
            if label not in lowered:
                continue
            if any(token in lowered for token in skip):
                continue
            if row.pairing != "UNIQUE" or not row.current_raw:
                continue
            try:
                found.append(Decimal(row.current_raw.replace(",", "")) * page.unit_multiplier)
            except (InvalidOperation, ValueError):
                continue
    distinct = set(found)
    if len(distinct) != 1:
        return None
    return found[0]


def _statement_kind(text: str, *, previous_text: str = "") -> tuple[str | None, str]:
    standalone = bool(_STAND.search(text) and not _CONS.search(text))
    prefix = "Standalone" if standalone else "Consolidated"
    titled_pl = bool(_PL.search(text))
    titled_bs = bool(_BS.search(text))
    titled_cf = bool(_CF.search(text))
    if _HIGHLIGHTS.search(text) and not (titled_pl or titled_bs or titled_cf):
        return None, ""
    if _PL_STRUCT.search(text) and _PL_PROFIT.search(text):
        if (_HIGHLIGHTS.search(text) or _MIXED_BASIS_HEADERS.search(text)) and not titled_pl:
            return None, ""
        return "pl", f"{prefix} Statement of Profit and Loss"
    if _BS_STRUCT.search(text) and _BS_EQ.search(text):
        return "bs", f"{prefix} Balance Sheet"
    if _CF_STRUCT.search(text):
        return "cf", f"{prefix} Statement of Cash Flows"
    if titled_pl and _PL_PROFIT.search(text):
        return "pl", f"{prefix} Statement of Profit and Loss"
    if titled_bs and (_BS_STRUCT.search(text) or _BS_EQ.search(text)):
        return "bs", f"{prefix} Balance Sheet"
    if titled_cf and _CF_STRUCT.search(text):
        return "cf", f"{prefix} Statement of Cash Flows"
    if previous_text:
        if _BS.search(previous_text) and (
            _BS_STRUCT.search(text) or _BS_EQ.search(text)
        ):
            return "bs", f"{prefix} Balance Sheet"
        if _PL.search(previous_text) and (
            _PL_STRUCT.search(text) or _PL_PROFIT.search(text)
        ):
            return "pl", f"{prefix} Statement of Profit and Loss"
        if _CF.search(previous_text) and _CF_STRUCT.search(text):
            return "cf", f"{prefix} Statement of Cash Flows"
    return None, ""


def _basis(text: str) -> str | None:
    if re.search(r"standalone financial statement", text, re.I) and not re.search(
        r"consolidated financial statement", text, re.I
    ):
        return "standalone"
    if re.search(r"consolidated financial statement", text, re.I):
        return "consolidated"
    if _STAND.search(text) and not _CONS.search(text):
        return "standalone"
    if _CONS.search(text):
        return "consolidated"
    return None


def _page_unit(
    spans: tuple[PdfSpan, ...],
) -> tuple[str | None, Decimal | None, str | None]:
    if not spans:
        return None, None, None
    blob = " ".join(span.text for span in spans)
    currency = "INR" if re.search(r"₹|inr\b|rs\.?", blob, re.I) else None
    if _UNIT_CRORE.search(blob):
        return "crore", Decimal("10000000"), currency or "INR"
    if _UNIT_MILLION.search(blob):
        return "million", Decimal("1000000"), currency or "INR"
    if _UNIT_LAKH.search(blob):
        return "lakh", Decimal("100000"), currency or "INR"
    if _UNIT_ACTUAL.search(blob):
        return "actual", Decimal("1"), currency or "INR"
    return None, None, currency


def _parse_header_date(text: str) -> date | None:
    blob = " ".join(text.split())
    blob = _ORDINAL.sub(r"\1", blob)
    month = (
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)"
    )
    match = re.search(
        rf"(\d{{1,2}})\s+{month}[.]?,?\s+(20\d{{2}})",
        blob,
        re.I,
    )
    if match:
        month_no = _MONTHS.get(match.group(2).lower()[:3], 0)
        if month_no:
            try:
                return date(int(match.group(3)), month_no, int(match.group(1)))
            except ValueError:
                return None
    us_match = re.search(
        rf"{month}\s+(\d{{1,2}})[.,]?\s+(20\d{{2}})",
        blob,
        re.I,
    )
    if us_match:
        month_no = _MONTHS.get(us_match.group(1).lower()[:3], 0)
        if month_no:
            try:
                return date(int(us_match.group(3)), month_no, int(us_match.group(2)))
            except ValueError:
                return None
    dotted = _DOT_DATE.search(blob)
    if dotted:
        day, month_no, year = int(dotted.group(1)), int(dotted.group(2)), int(dotted.group(3))
        if month_no > 12 and day <= 12:
            day, month_no = month_no, day
        try:
            return date(year, month_no, day)
        except ValueError:
            return None
    fy = re.search(r"\b(?:FY\s*)?(20\d{2})\s*[-–]\s*(\d{2})\b", blob, re.I)
    if fy:
        start = int(fy.group(1))
        end_yy = int(fy.group(2))
        end = (start // 100) * 100 + end_yy
        if end in {start, start + 1}:
            return date(end, 3, 31)
    if len(blob) <= 24:
        month_year = _MONTH_YEAR.fullmatch(blob) or _MONTH_YEAR.search(blob)
        if month_year and not re.search(r"\d{1,2}\s+" + month, blob, re.I):
            month_no = _MONTHS.get(month_year.group(1).lower()[:3], 0)
            if month_no == 3:
                try:
                    return date(int(month_year.group(2)), 3, 31)
                except ValueError:
                    return None
    return None


def _period_columns(spans: tuple[PdfSpan, ...]) -> tuple[PeriodColumn, ...]:
    dated: list[tuple[PdfSpan, date]] = []
    for span in spans:
        parsed = _parse_header_date(span.text)
        if parsed is None:
            continue
        if len(span.text) > 48:
            continue
        dated.append((span, parsed))
    if not dated:
        return _year_under_month_columns(spans)
    ordered = sorted(dated, key=lambda item: (-item[0].y, item[0].x))
    clusters: list[list[tuple[PdfSpan, date]]] = []
    for span, parsed in ordered:
        if clusters and abs(clusters[-1][0][0].y - span.y) <= _Y_TOL:
            clusters[-1].append((span, parsed))
            continue
        clusters.append([(span, parsed)])
    candidates: list[list[PeriodColumn]] = []
    for group in clusters:
        unique: dict[float, PeriodColumn] = {}
        for span, parsed in group:
            key = round(span.x / 8.0) * 8.0
            previous = unique.get(key)
            if previous is None or parsed > previous.period_end:
                unique[key] = PeriodColumn(
                    x=span.x, period_end=parsed, label=span.text.strip()
                )
        columns = sorted(unique.values(), key=lambda item: item.x)
        ends = {col.period_end for col in columns}
        if len(ends) < 2:
            continue
        if max(col.x for col in columns) < 200:
            continue
        candidates.append(columns)
    if not candidates:
        year_cols = _year_under_month_columns(spans)
        if year_cols:
            return year_cols
        return ()
    best = max(
        candidates,
        key=lambda cols: (max(col.period_end for col in cols), len({c.period_end for c in cols})),
    )
    by_period: dict[date, PeriodColumn] = {}
    for col in sorted(best, key=lambda item: item.x):
        by_period[col.period_end] = col
    distinct = sorted(by_period.values(), key=lambda item: item.period_end)
    if len(distinct) < 2:
        year_cols = _year_under_month_columns(spans)
        if year_cols:
            return year_cols
        return ()
    best = sorted(distinct[-2:], key=lambda item: item.x)
    return tuple(best)


def _year_under_month_columns(spans: tuple[PdfSpan, ...]) -> tuple[PeriodColumn, ...]:
    """Bind year-only headers (2026 2025) sitting under 'March 31,' / 'Year ended March 31,'."""
    years: list[PdfSpan] = []
    for span in spans:
        if _YEAR_ONLY.fullmatch(span.text.strip()):
            years.append(span)
            continue
        pair = re.fullmatch(r"(20\d{2})\s+(20\d{2})", span.text.strip())
        if pair:
            width = max(len(pair.group(1)) * 5.0, 12.0)
            years.append(
                PdfSpan(span.page, span.x, span.y, pair.group(1), span.font_size)
            )
            years.append(
                PdfSpan(
                    span.page,
                    span.x + width + 14.0,
                    span.y,
                    pair.group(2),
                    span.font_size,
                )
            )
    if len(years) < 2:
        return ()
    ordered = sorted(years, key=lambda item: (-item.y, item.x))
    clusters: list[list[PdfSpan]] = []
    for span in ordered:
        if clusters and abs(clusters[-1][0].y - span.y) <= _Y_TOL:
            clusters[-1].append(span)
            continue
        clusters.append([span])
    parent_re = re.compile(
        r"march\s*31|31\s*march|year ended march|as at march",
        re.I,
    )
    for group in clusters:
        unique_years: dict[int, PdfSpan] = {}
        for span in group:
            year = int(span.text.strip())
            unique_years[year] = span
        if len(unique_years) < 2:
            continue
        top = max(span.y for span in group)
        parent = None
        for span in spans:
            if span.y <= top or span.y > top + 55:
                continue
            if parent_re.search(span.text):
                parent = span
                break
        if parent is None:
            continue
        if max(span.x for span in unique_years.values()) < 200:
            continue
        columns = [
            PeriodColumn(
                x=span.x,
                period_end=date(year, 3, 31),
                label=f"March 31, {year}",
            )
            for year, span in sorted(unique_years.items())
        ]
        return tuple(sorted(columns, key=lambda item: item.x)[-2:])
    return ()


def _cluster_rows(spans: tuple[PdfSpan, ...]) -> list[list[PdfSpan]]:
    ordered = sorted(spans, key=lambda item: (-item.y, item.x))
    rows: list[list[PdfSpan]] = []
    for span in ordered:
        if rows and abs(rows[-1][0].y - span.y) <= _Y_TOL:
            rows[-1].append(span)
            continue
        rows.append([span])
    return rows


def _assign_number(
    span: PdfSpan, columns: tuple[PeriodColumn, ...]
) -> tuple[PeriodColumn | None, str]:
    right = span.x + max(len(span.text.replace(" ", "")) * 4.5, 12.0)
    distances = [(abs(right - col.x), col) for col in columns]
    distances.sort(key=lambda item: item[0])
    if not distances or distances[0][0] > _X_TOL:
        return None, "UNAVAILABLE"
    if len(distances) > 1 and abs(distances[0][0] - distances[1][0]) < _AMBIGUOUS_GAP:
        return None, "AMBIGUOUS"
    return distances[0][1], "UNIQUE"


def _rows_for_page(
    spans: tuple[PdfSpan, ...],
    *,
    columns: tuple[PeriodColumn, ...],
    unit_scale: str | None,
    currency: str | None,
    basis: str,
    statement: str,
    page: int,
) -> list[ReconstructedRow]:
    current_col = max(columns, key=lambda item: item.period_end)
    prior_candidates = [item for item in columns if item.period_end < current_col.period_end]
    prior_col = (
        max(prior_candidates, key=lambda item: item.period_end) if prior_candidates else None
    )
    rebuilt: list[ReconstructedRow] = []
    min_value_x = min(col.x for col in columns) - 20
    ordered_cols = sorted(columns, key=lambda item: item.x)
    for group in _cluster_rows(spans):
        labels: list[PdfSpan] = []
        numbers: list[PdfSpan] = []
        for span in group:
            extra_labels, extra_numbers = _split_embedded(span, ordered_cols)
            labels.extend(extra_labels)
            numbers.extend(extra_numbers)
        labels = [span for span in labels if not _NOTE.search(span.text)]
        label = " ".join(span.text for span in sorted(labels, key=lambda item: item.x)).strip()
        if rebuilt and "attributable" in rebuilt[-1].label.lower() and re.search(
            r"equity holders|owners of the company|shareholders of the company",
            label,
            re.I,
        ):
            label = f"{rebuilt[-1].label} {label}"
        elif (
            rebuilt
            and rebuilt[-1].current_raw is None
            and re.search(
                r"(from operating|generated from operating|property, plant and|profit for the)$",
                rebuilt[-1].label,
                re.I,
            )
        ):
            label = f"{rebuilt[-1].label} {label}"
        if len(label) < 4:
            continue
        usable: list[tuple[PdfSpan, str]] = []
        for span in numbers:
            token = _numeric_token(span.text)
            if token is None:
                continue
            try:
                value = Decimal(token)
            except (InvalidOperation, ValueError):
                continue
            if 0 < abs(value) < 100 and span.x < min_value_x:
                continue
            usable.append((span, token))
        current_raw = None
        prior_raw = None
        pairing = "UNAVAILABLE"
        if (
            len(usable) == 2
            and len(ordered_cols) == 2
            and abs(usable[0][0].x - usable[1][0].x) >= _AMBIGUOUS_GAP
        ):
            by_x = sorted(usable, key=lambda item: item[0].x)
            mapping = {
                ordered_cols[0].period_end: by_x[0][1],
                ordered_cols[1].period_end: by_x[1][1],
            }
            current_raw = mapping.get(current_col.period_end)
            prior_raw = None if prior_col is None else mapping.get(prior_col.period_end)
            pairing = "UNIQUE"
        else:
            statuses: list[str] = []
            for span, token in usable:
                column, status = _assign_number(span, columns)
                statuses.append(status)
                if column is None:
                    continue
                if column.period_end == current_col.period_end:
                    if current_raw is not None:
                        statuses.append("AMBIGUOUS")
                        current_raw = None
                        break
                    current_raw = token
                elif prior_col is not None and column.period_end == prior_col.period_end:
                    prior_raw = token
            if "AMBIGUOUS" in statuses and current_raw is None:
                pairing = "AMBIGUOUS"
            elif current_raw is not None:
                pairing = "UNIQUE"
        rebuilt.append(
            ReconstructedRow(
                label=label,
                current_raw=current_raw,
                prior_raw=prior_raw,
                current_period=current_col.period_end,
                prior_period=None if prior_col is None else prior_col.period_end,
                unit_scale=unit_scale,
                currency=currency,
                basis=basis or "consolidated",
                page=page,
                statement=statement,
                pairing=pairing,
                y=group[0].y,
            )
        )
    return rebuilt


def _numeric_span_count(spans: tuple[PdfSpan, ...]) -> int:
    count = 0
    for span in spans:
        if _NUMBER.match(span.text.replace(" ", "")):
            count += 1
            continue
        count += len(_EMBEDDED_NUM.findall(span.text))
    return count


def _numeric_token(text: str) -> str | None:
    token = text.replace(" ", "").replace(",", "")
    if token.startswith("(") and token.endswith(")"):
        token = "-" + token[1:-1]
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", token):
        return None
    digits = token.lstrip("-").replace(".", "", 1)
    if "." not in token and len(digits) > 12:
        return None
    return token


def _split_embedded(
    span: PdfSpan, columns: tuple[PeriodColumn, ...]
) -> tuple[list[PdfSpan], list[PdfSpan]]:
    text = span.text
    if _NUMBER.match(text.replace(" ", "")):
        return [], [span]
    matches = list(_EMBEDDED_NUM.finditer(text))
    if not matches:
        return [span], []
    labels: list[PdfSpan] = []
    numbers: list[PdfSpan] = []
    prefix = text[: matches[0].start()].strip()
    if prefix:
        labels.append(PdfSpan(span.page, span.x, span.y, prefix, span.font_size))
    for index, match in enumerate(matches):
        token = match.group()
        if index < len(columns):
            width = max(len(token.replace(" ", "")) * 4.5, 12.0)
            numbers.append(
                PdfSpan(span.page, columns[index].x - width, span.y, token, span.font_size)
            )
        else:
            numbers.append(
                PdfSpan(span.page, span.x + float(match.start()), span.y, token, span.font_size)
            )
    return labels, numbers


def _row_label_match(label: str, labels: tuple[str, ...], field: str) -> str | None:
    lowered = re.sub(r"\s+", " ", label.lower())
    concepts = [
        token
        for token in (
            "total assets",
            "total liabilities",
            "cash and cash equivalents",
            "trade payables",
            "revenue from operations",
        )
        if token in lowered
    ]
    if len(concepts) >= 2:
        return None
    if field == "net_income" and "non-controlling" in lowered:
        return None
    if field == "net_income" and "comprehensive" in lowered:
        return None
    if field == "net_income" and (
        "revenue from" in lowered
        or "total expenses" in lowered
        or "total income" in lowered
        or "basic (" in lowered
        or "earnings per" in lowered
        or "per share" in lowered
    ):
        return None
    if field == "cash" and (
        "other than cash" in lowered
        or "reserve bank" in lowered
        or "end of the year" in lowered
        or "end of the period" in lowered
    ):
        return None
    if field == "total_assets" and "liabilities" in lowered:
        return None
    if field == "total_liabilities" and "assets" in lowered and "total liabilities" not in lowered:
        return None
    if field == "equity" and "goodwill" in lowered:
        return None
    if field == "revenue" and (
        "interest earned" in lowered
        or "sale of products" in lowered
        or "sale of services" in lowered
        or "other operating revenue" in lowered
        or "current liabilities" in lowered
        or "total assets" in lowered
        or "note " in lowered
    ):
        return None
    if field == "ebit" and "ebitda" in lowered and "ebit" not in lowered.replace("ebitda", ""):
        return None
    if field == "debt" and "lease" in lowered and "borrow" not in lowered:
        return None
    if field == "equity" and (
        "share capital" in lowered
        or "other equity" in lowered
        or "attributable" in lowered
        or "liabilities" in lowered
    ):
        return None
    if field == "cfo" and ("add :" in lowered or "add:" in lowered):
        return None
    for allowed in labels:
        if allowed in lowered:
            if field == "net_income" and allowed == "owners of the company" and "attributable" not in lowered:
                continue
            if field == "revenue" and allowed == "revenue" and "from operations" in lowered:
                continue
            if field == "equity" and allowed == "equity" and "total equity" not in lowered:
                if "shareholders" not in lowered:
                    continue
            return allowed
    return None
