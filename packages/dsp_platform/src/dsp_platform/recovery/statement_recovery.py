"""Targeted missing financial statement recovery from regulatory filings (P0).

Retrieves authoritative public filings, uses Gemini and OpenAI for independent
extraction and cross-validation, enforces financial integrity and equation checks,
and maintains P1-03 without fabricating data or weakening valuation authority.
"""

from __future__ import annotations
import concurrent.futures

import json
import logging
import math
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from data_engine import (
    AuthenticatedFinancialStatements,
    AuthenticatedStatementPeriod,
    CompanyIdentity,
    Filing,
    FinancialStatementProvenance,
    StatementField,
    utc_now,
)

_LOG = logging.getLogger("dsp.recovery.statement_recovery")

_NUMERIC_LINE_ITEMS = (
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "ebit",
    "ebitda",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "cash_and_equivalents",
    "current_assets",
    "total_assets",
    "current_liabilities",
    "total_liabilities",
    "total_equity",
    "total_debt",
    "long_term_debt",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "shares_outstanding",
)


class StatementRecoveryStatus(str, Enum):
    AUTHENTICATED = "authenticated"
    RECOVERED_AND_VALIDATED = "recovered_and_validated"
    PARTIALLY_RECOVERED = "partially_recovered"
    UNAVAILABLE = "unavailable"
    CONFLICT_REJECTED = "conflict_rejected"


@dataclass(frozen=True, slots=True)
class FieldValidationResult:
    field_name: str
    status: str  # "agreed", "conflict", "single_model", "rejected", "missing"
    value: Decimal | None
    model_a_value: Decimal | None = None
    model_b_value: Decimal | None = None
    relative_diff: float | None = None
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "status": self.status,
            "value": float(self.value) if self.value is not None else None,
            "model_a_value": (
                float(self.model_a_value) if self.model_a_value is not None else None
            ),
            "model_b_value": (
                float(self.model_b_value) if self.model_b_value is not None else None
            ),
            "relative_diff": self.relative_diff,
            "rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True, slots=True)
class RecoveryDiagnostics:
    attempted: bool = False
    models_called: tuple[str, ...] = ()
    models_succeeded: tuple[str, ...] = ()
    models_failed: tuple[str, ...] = ()
    filings_checked: int = 0
    total_latency_ms: float = 0.0
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "models_called": list(self.models_called),
            "models_succeeded": list(self.models_succeeded),
            "models_failed": list(self.models_failed),
            "filings_checked": self.filings_checked,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class RecoveryProvenance:
    status: StatementRecoveryStatus
    source_url: str | None = None
    source_type: str = "regulatory_filing"
    filing_date: str | None = None
    period_end: str | None = None
    period_type: str | None = None
    exchange: str | None = None
    reporting_currency: str = "USD"
    statement_basis: str = "consolidated"
    unit_scale: str = "actual"
    models_used: tuple[str, ...] = ()
    validated_fields: tuple[str, ...] = ()
    rejected_fields: tuple[str, ...] = ()
    conflicts: tuple[dict[str, Any], ...] = ()
    retrieval_timestamp: str = ""
    diagnostics: RecoveryDiagnostics = field(default_factory=RecoveryDiagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "filing_date": self.filing_date,
            "period_end": self.period_end,
            "period_type": self.period_type,
            "exchange": self.exchange,
            "reporting_currency": self.reporting_currency,
            "statement_basis": self.statement_basis,
            "unit_scale": self.unit_scale,
            "models_used": list(self.models_used),
            "validated_fields": list(self.validated_fields),
            "rejected_fields": list(self.rejected_fields),
            "conflicts": list(self.conflicts),
            "retrieval_timestamp": self.retrieval_timestamp,
            "diagnostics": self.diagnostics.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class StatementRecoveryResult:
    status: StatementRecoveryStatus
    provenance: RecoveryProvenance
    recovered_statements: AuthenticatedFinancialStatements | None = None
    unavailability_reason: str | None = None

    def is_usable(self) -> bool:
        return (
            self.recovered_statements is not None
            and self.recovered_statements.has_any_period()
            and self.status
            in (
                StatementRecoveryStatus.RECOVERED_AND_VALIDATED,
                StatementRecoveryStatus.PARTIALLY_RECOVERED,
            )
        )


def _safe_parse_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if not isinstance(val, str):
        return None
    s = val.strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        pass
    try:
        if "T" in s:
            return date.fromisoformat(s.split("T")[0])
        if " " in s:
            return date.fromisoformat(s.split(" ")[0])
    except Exception:
        pass
    return None

def _safe_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite():
            return None
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        try:
            d = Decimal(str(value))
            if d.is_nan() or d.is_infinite():
                return None
            return d
        except Exception:
            return None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            d = Decimal(cleaned)
            if d.is_nan() or d.is_infinite():
                return None
            return d
        except Exception:
            return None
    return None


def _normalize_scale(scale_name: str | None) -> Decimal:
    """Multiplier to convert reported units into actual units."""
    if not scale_name:
        return Decimal("1")
    s = scale_name.strip().lower()
    if s in ("actual", "units", "ones"):
        return Decimal("1")
    if s in ("thousands", "thousand", "k"):
        return Decimal("1000")
    if s in ("millions", "million", "m"):
        return Decimal("1000000")
    if s in ("billions", "billion", "b"):
        return Decimal("1000000000")
    if s in ("lakhs", "lakh", "lac", "lacs"):
        return Decimal("100000")
    if s in ("crores", "crore", "cr"):
        return Decimal("10000000")
    return Decimal("1")


class StatementRecoveryService:
    """Orchestrates targeted recovery of financial statements."""

    def __init__(
        self,
        *,
        filings_service: Any = None,
        llm_registry: Any = None,
        gemini_adapter: Any = None,
        openai_adapter: Any = None,
        relative_tolerance: float = 0.05,
        max_content_bytes: int = 50000,
    ) -> None:
        self._filings_service = filings_service
        self._llm_registry = llm_registry
        self._gemini_adapter = gemini_adapter
        self._openai_adapter = openai_adapter
        self._relative_tolerance = relative_tolerance
        self._max_content_bytes = max_content_bytes

    def _resolve_models(self) -> tuple[Any | None, Any | None]:
        gemini = self._gemini_adapter
        openai = self._openai_adapter
        if gemini is not None and openai is not None:
            return gemini, openai

        registry = self._llm_registry
        if registry is None:
            try:
                from llm_adapters import build_default_registry

                registry = build_default_registry()
            except Exception:
                registry = None

        if registry is not None:
            if gemini is None:
                g = registry.get("gemini")
                if g and getattr(g, "is_configured", lambda: True)():
                    gemini = g
            if openai is None:
                o = registry.get("openai")
                if o and getattr(o, "is_configured", lambda: True)():
                    openai = o

        return gemini, openai

    def recover(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        filing_text: str | None = None,
        filing: Filing | None = None,
    ) -> StatementRecoveryResult:
        """Attempt non-blocking targeted recovery from authoritative filings."""
        start_time = datetime.now(tz=UTC)
        sym = symbol.strip().upper()
        diag_errors: list[str] = []
        diag_models_called: list[str] = []
        diag_models_succeeded: list[str] = []
        diag_models_failed: list[str] = []

        # 1. Resolve filing evidence
        active_filing = filing
        active_text = filing_text
        checked_filings = 1 if active_filing else 0

        if active_filing is None and active_text is None:
            active_filing, active_text, checked_filings = self._find_filing_evidence(sym, exchange=exchange)

        # Enforce that evidence must be actual document content, not empty metadata
        if not active_text or not active_text.strip():
            elapsed = (datetime.now(tz=UTC) - start_time).total_seconds() * 1000.0
            diag = RecoveryDiagnostics(
                attempted=True,
                filings_checked=checked_filings,
                total_latency_ms=elapsed,
                errors=("Authoritative filing content unavailable for extraction",),
            )
            prov = RecoveryProvenance(
                status=StatementRecoveryStatus.UNAVAILABLE,
                source_url=active_filing.url if active_filing else None,
                filing_date=active_filing.filed_at.isoformat()
                if active_filing and active_filing.filed_at
                else None,
                exchange=exchange,
                reporting_currency=currency,
                retrieval_timestamp=start_time.isoformat(),
                diagnostics=diag,
            )
            return StatementRecoveryResult(
                status=StatementRecoveryStatus.UNAVAILABLE,
                provenance=prov,
                unavailability_reason="Authoritative filing content unavailable for extraction",
            )

        # Bound content length to prevent unbounded token usage and cost
        bounded_content = active_text[: self._max_content_bytes]

        # 2. Invoke Gemini and OpenAI independently for extraction
        gemini_model, openai_model = self._resolve_models()

        if gemini_model is None and openai_model is None:
            elapsed = (datetime.now(tz=UTC) - start_time).total_seconds() * 1000.0
            diag = RecoveryDiagnostics(
                attempted=True,
                filings_checked=1 if active_filing else 0,
                total_latency_ms=elapsed,
                errors=("No LLM providers configured or available for recovery",),
            )
            prov = RecoveryProvenance(
                status=StatementRecoveryStatus.UNAVAILABLE,
                source_url=active_filing.url if active_filing else None,
                filing_date=active_filing.filed_at.isoformat()
                if active_filing and active_filing.filed_at
                else None,
                exchange=exchange,
                reporting_currency=currency,
                retrieval_timestamp=start_time.isoformat(),
                diagnostics=diag,
            )
            return StatementRecoveryResult(
                status=StatementRecoveryStatus.UNAVAILABLE,
                provenance=prov,
                unavailability_reason="No LLM providers available for recovery extraction",
            )

        gemini_raw: dict[str, Any] | None = None
        openai_raw: dict[str, Any] | None = None

        system_instruction = (
            "You are a strict financial statement data extractor. Given the following regulatory filing document, "
            "extract the latest audited annual financial statement line items. Return a valid JSON object only with NO markdown formatting, "
            "NO extra keys, and NO reasoning. Missing or unavailable numbers MUST be null. Do not fabricate, estimate, or extrapolate. "
            "Shares outstanding must be the actual count of common shares, NOT a shareholding percentage."
        )

        user_prompt = (
            f"Company symbol: {sym}\n"
            f"Exchange: {exchange or 'Any'}\n\n"
            f"Regulatory Filing Content:\n{bounded_content}\n\n"
            "Extract the following JSON structure exactly:\n"
            "{\n"
            '  "issuer_symbol": string,\n'
            '  "period_type": "annual",\n'
            '  "period_end": "YYYY-MM-DD",\n'
            '  "filing_date": "YYYY-MM-DD",\n'
            '  "currency": string,\n'
            '  "statement_basis": "consolidated" | "standalone",\n'
            '  "unit_scale": "actual" | "thousands" | "millions" | "billions" | "crores" | "lakhs",\n'
            '  "shares_outstanding": number | null,\n'
            '  "revenue": number | null,\n'
            '  "cost_of_revenue": number | null,\n'
            '  "gross_profit": number | null,\n'
            '  "operating_income": number | null,\n'
            '  "ebit": number | null,\n'
            '  "ebitda": number | null,\n'
            '  "net_income": number | null,\n'
            '  "eps_basic": number | null,\n'
            '  "eps_diluted": number | null,\n'
            '  "cash_and_equivalents": number | null,\n'
            '  "current_assets": number | null,\n'
            '  "total_assets": number | null,\n'
            '  "current_liabilities": number | null,\n'
            '  "total_liabilities": number | null,\n'
            '  "total_equity": number | null,\n'
            '  "total_debt": number | null,\n'
            '  "long_term_debt": number | null,\n'
            '  "operating_cash_flow": number | null,\n'
            '  "investing_cash_flow": number | null,\n'
            '  "financing_cash_flow": number | null,\n'
            '  "capital_expenditures": number | null,\n'
            '  "free_cash_flow": number | null\n'
            "}"
        )

        req = LanguageModelRequest(
            request_id=f"recovery-{sym}-{uuid.uuid4().hex[:8]}",
            intent_class=UserIntentType.EXPLAIN_REPORT,
            prompt_parts=(system_instruction, user_prompt),
            context_digest_ids=("filings_recovery",),
            provenance=("dsp_platform.recovery.statement_recovery",),
        )

        def _call_model(name: str, model: Any) -> tuple[str, dict[str, Any] | None, str | None]:
            try:
                res = model.invoke(req)
                if res and res.status == LanguageModelStatus.COMPLETE:
                    text_out = getattr(res, "narrative_text", None) or getattr(
                        res, "content", None
                    )
                    parsed = self._parse_json_response(text_out)
                    if parsed:
                        return name, parsed, None
                    return name, None, f"{name.capitalize()} returned invalid or unparseable JSON"
                return name, None, f"{name.capitalize()} invocation unsuccessful"
            except Exception as exc:
                return name, None, f"{name.capitalize()} error: {type(exc).__name__}"

        models_to_run: list[tuple[str, Any]] = []
        if gemini_model is not None:
            diag_models_called.append("gemini")
            models_to_run.append(("gemini", gemini_model))
        if openai_model is not None:
            diag_models_called.append("openai")
            models_to_run.append(("openai", openai_model))

        if models_to_run:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(models_to_run)) as executor:
                fut_map = {executor.submit(_call_model, mname, mmod): mname for mname, mmod in models_to_run}
                try:
                    for fut in concurrent.futures.as_completed(fut_map, timeout=30.0):
                        mname = fut_map[fut]
                        try:
                            mod_name, data, err = fut.result()
                            if data is not None:
                                diag_models_succeeded.append(mod_name)
                                if mod_name == "gemini":
                                    gemini_raw = data
                                else:
                                    openai_raw = data
                            else:
                                diag_models_failed.append(mod_name)
                                if err:
                                    diag_errors.append(err)
                        except Exception as exc:
                            diag_models_failed.append(mname)
                            diag_errors.append(f"{mname.capitalize()} error: {type(exc).__name__}")
                except (TimeoutError, concurrent.futures.TimeoutError):
                    for fut, mname in fut_map.items():
                        if not fut.done() and mname not in diag_models_failed and mname not in diag_models_succeeded:
                            diag_models_failed.append(mname)
                            diag_errors.append(f"{mname.capitalize()} error: TimeoutError")

        elapsed = (datetime.now(tz=UTC) - start_time).total_seconds() * 1000.0

        if gemini_raw is None and openai_raw is None:
            diag = RecoveryDiagnostics(
                attempted=True,
                models_called=tuple(diag_models_called),
                models_succeeded=tuple(diag_models_succeeded),
                models_failed=tuple(diag_models_failed),
                filings_checked=1 if active_filing else 0,
                total_latency_ms=elapsed,
                errors=tuple(diag_errors)
                or ("No LLM provider produced valid extraction",),
            )
            prov = RecoveryProvenance(
                status=StatementRecoveryStatus.UNAVAILABLE,
                source_url=active_filing.url if active_filing else None,
                filing_date=active_filing.filed_at.isoformat()
                if active_filing and active_filing.filed_at
                else None,
                exchange=exchange,
                reporting_currency=currency,
                retrieval_timestamp=start_time.isoformat(),
                diagnostics=diag,
            )
            return StatementRecoveryResult(
                status=StatementRecoveryStatus.UNAVAILABLE,
                provenance=prov,
                unavailability_reason="LLM models unavailable or produced invalid extractions",
            )

        # 3. Cross-validate and reconcile line items
        reconciled = self._reconcile_extractions(
            gemini_data=gemini_raw,
            openai_data=openai_raw,
            symbol=sym,
            expected_exchange=exchange,
            expected_currency=currency,
        )

        diag = RecoveryDiagnostics(
            attempted=True,
            models_called=tuple(diag_models_called),
            models_succeeded=tuple(diag_models_succeeded),
            models_failed=tuple(diag_models_failed),
            filings_checked=1 if active_filing else 0,
            total_latency_ms=elapsed,
            errors=tuple(diag_errors),
        )

        filing_url = (
            active_filing.url if active_filing else reconciled.get("source_url")
        )
        filing_d = (
            active_filing.filed_at.isoformat()
            if active_filing and active_filing.filed_at
            else reconciled.get("filing_date")
        )

        validated_keys = tuple(reconciled["validated_keys"])
        rejected_keys = tuple(reconciled["rejected_keys"])
        conflicts = tuple(reconciled["conflicts"])

        status = reconciled["status"]
        bundle = None
        if status in (
            StatementRecoveryStatus.RECOVERED_AND_VALIDATED,
            StatementRecoveryStatus.PARTIALLY_RECOVERED,
        ):
            bundle = self._build_statement_bundle(
                symbol=sym,
                exchange=exchange,
                currency=reconciled["currency"],
                period_end=reconciled["period_end"],
                filing_date=filing_d,
                period_type=reconciled["period_type"],
                basis=reconciled["basis"],
                unit_scale=reconciled["unit_scale"],
                fields=reconciled["fields"],
                source_url=filing_url,
                models_used=tuple(diag_models_succeeded),
                status=status,
                validated_keys=validated_keys,
                rejected_keys=rejected_keys,
                conflicts=conflicts,
            )

        prov = RecoveryProvenance(
            status=status,
            source_url=filing_url,
            source_type="regulatory_filing",
            filing_date=filing_d,
            period_end=reconciled["period_end"].isoformat()
            if reconciled.get("period_end")
            else None,
            period_type=reconciled["period_type"],
            exchange=exchange,
            reporting_currency=reconciled["currency"],
            statement_basis=reconciled["basis"],
            unit_scale=reconciled["unit_scale"],
            models_used=tuple(diag_models_succeeded),
            validated_fields=validated_keys,
            rejected_fields=rejected_keys,
            conflicts=conflicts,
            retrieval_timestamp=start_time.isoformat(),
            diagnostics=diag,
        )

        return StatementRecoveryResult(
            status=status,
            provenance=prov,
            recovered_statements=bundle,
            unavailability_reason=reconciled.get("reason"),
        )

    def _parse_json_response(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()
        try:
            val = json.loads(cleaned)
            return val if isinstance(val, dict) else None
        except Exception:
            m = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if m:
                try:
                    val = json.loads(m.group(0))
                    return val if isinstance(val, dict) else None
                except Exception:
                    pass
        return None

    def _find_filing_evidence(
        self, symbol: str, exchange: str | None = None
    ) -> tuple[Filing | None, str | None, int]:
        """Search filing candidates, skipping metadata-only or malformed candidates until valid document content is found."""
        checked_count = 0
        try:
            from dsp_platform.filings import get_authenticated_filings

            result = get_authenticated_filings(symbol, exchange=exchange, limit=10)
            if result and result.get("filings"):
                filings = result["filings"]
                for f in filings:
                    checked_count += 1
                    try:
                        content = (
                            f.get("content")
                            or f.get("text")
                            or (f.get("metadata") or {}).get("content")
                        )
                        if not content or not str(content).strip():
                            # Candidate has metadata only; continue searching remaining candidates
                            continue

                        url = f.get("url")
                        title = f.get("title") or ""
                        filed_at = f.get("filed_at")
                        filing_id = f.get("filing_id") or f"{symbol}-filing"
                        period_of_report = f.get("period_of_report")

                        filed_at_date = _safe_parse_date(filed_at) or date.today()
                        period_of_report_date = _safe_parse_date(period_of_report)

                        filing_obj = Filing(
                            filing_id=filing_id,
                            filing_type=f.get("filing_type") or "annual_report",
                            title=title,
                            url=url or "",
                            filed_at=filed_at_date,
                            period_of_report=period_of_report_date,
                            source="Regulatory Filings",
                        )
                        return filing_obj, str(content).strip(), checked_count
                    except Exception:
                        continue
        except Exception as exc:
            _LOG.warning(
                "filings_lookup_failed",
                extra={"symbol": symbol, "error": type(exc).__name__},
            )
        return None, None, checked_count

    def _find_best_filing(
        self, symbol: str, exchange: str | None = None
    ) -> tuple[Filing | None, str | None]:
        """Backward-compatible alias returning (Filing, content) or (None, None)."""
        filing, content, _ = self._find_filing_evidence(symbol, exchange=exchange)
        return filing, content

    def _reconcile_extractions(
        self,
        *,
        gemini_data: dict[str, Any] | None,
        openai_data: dict[str, Any] | None,
        symbol: str,
        expected_exchange: str | None,
        expected_currency: str,
    ) -> dict[str, Any]:
        """Reconcile fields between models, check 5% tolerance and integrity."""
        primary = gemini_data if gemini_data is not None else openai_data
        assert primary is not None

        # 1. Issuer identity validation
        extracted_sym = str(primary.get("issuer_symbol") or "").strip().upper()
        if (
            extracted_sym
            and extracted_sym != symbol
            and symbol not in extracted_sym
            and extracted_sym not in symbol
        ):
            return {
                "status": StatementRecoveryStatus.UNAVAILABLE,
                "reason": f"Issuer identity mismatch: expected {symbol}, got {extracted_sym}",
                "validated_keys": [],
                "rejected_keys": list(_NUMERIC_LINE_ITEMS),
                "conflicts": [],
                "currency": expected_currency,
                "basis": "consolidated",
                "unit_scale": "actual",
                "period_type": "annual",
                "period_end": None,
                "fields": {},
            }

        # 2. Period end validation
        period_end_raw = primary.get("period_end") or ""
        period_end: date | None = None
        if period_end_raw:
            try:
                period_end = date.fromisoformat(str(period_end_raw)[:10])
            except ValueError:
                period_end = None

        if period_end is None:
            return {
                "status": StatementRecoveryStatus.UNAVAILABLE,
                "reason": "Missing or invalid reporting period end in filing",
                "validated_keys": [],
                "rejected_keys": list(_NUMERIC_LINE_ITEMS),
                "conflicts": [],
                "currency": expected_currency,
                "basis": "consolidated",
                "unit_scale": "actual",
                "period_type": "annual",
                "period_end": None,
                "fields": {},
            }

        # Stale date checks: cannot be in the future, cannot be older than 4 years
        today = date.today()
        if period_end > today:
            return {
                "status": StatementRecoveryStatus.UNAVAILABLE,
                "reason": f"Reporting period end {period_end} is in the future",
                "validated_keys": [],
                "rejected_keys": list(_NUMERIC_LINE_ITEMS),
                "conflicts": [],
                "currency": expected_currency,
                "basis": "consolidated",
                "unit_scale": "actual",
                "period_type": "annual",
                "period_end": None,
                "fields": {},
            }

        if (today - period_end).days > 365 * 4:
            return {
                "status": StatementRecoveryStatus.UNAVAILABLE,
                "reason": f"Reporting period end {period_end} is stale (> 4 years)",
                "validated_keys": [],
                "rejected_keys": list(_NUMERIC_LINE_ITEMS),
                "conflicts": [],
                "currency": expected_currency,
                "basis": "consolidated",
                "unit_scale": "actual",
                "period_type": "annual",
                "period_end": None,
                "fields": {},
            }

        period_type = str(primary.get("period_type") or "annual").strip().lower()
        if period_type not in ("annual", "ttm"):
            return {
                "status": StatementRecoveryStatus.UNAVAILABLE,
                "reason": f"Invalid period type {period_type!r}; annual/ttm required",
                "validated_keys": [],
                "rejected_keys": list(_NUMERIC_LINE_ITEMS),
                "conflicts": [],
                "currency": expected_currency,
                "basis": "consolidated",
                "unit_scale": "actual",
                "period_type": period_type,
                "period_end": None,
                "fields": {},
            }

        currency = str(primary.get("currency") or expected_currency).strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            return {
                "status": StatementRecoveryStatus.UNAVAILABLE,
                "reason": f"Invalid reporting currency {currency!r}",
                "validated_keys": [],
                "rejected_keys": list(_NUMERIC_LINE_ITEMS),
                "conflicts": [],
                "currency": expected_currency,
                "basis": "consolidated",
                "unit_scale": "actual",
                "period_type": period_type,
                "period_end": None,
                "fields": {},
            }

        basis = str(primary.get("statement_basis") or "consolidated").strip().lower()
        if basis not in ("consolidated", "standalone"):
            basis = "consolidated"

        scale_str = str(primary.get("unit_scale") or "actual").strip().lower()
        multiplier = _normalize_scale(scale_str)

        both_models = gemini_data is not None and openai_data is not None

        validated_keys: list[str] = []
        rejected_keys: list[str] = []
        conflicts: list[dict[str, Any]] = []
        field_values: dict[str, Decimal | None] = {}

        # 3. Compare numeric items
        for key in _NUMERIC_LINE_ITEMS:
            g_raw = gemini_data.get(key) if gemini_data else None
            o_raw = openai_data.get(key) if openai_data else None

            g_dec = _safe_decimal(g_raw)
            o_dec = _safe_decimal(o_raw)

            # Apply scale multiplier except for per-share metrics and shares
            if key not in ("eps_basic", "eps_diluted", "shares_outstanding"):
                if g_dec is not None and scale_str != "actual":
                    g_dec = g_dec * multiplier
                if o_dec is not None and scale_str != "actual":
                    o_dec = o_dec * multiplier

            if both_models:
                if g_dec is None and o_dec is None:
                    field_values[key] = None
                    continue

                if g_dec is None or o_dec is None:
                    rejected_keys.append(key)
                    conflicts.append(
                        {
                            "field": key,
                            "reason": "field_present_in_only_one_model",
                            "gemini": float(g_dec) if g_dec is not None else None,
                            "openai": float(o_dec) if o_dec is not None else None,
                        }
                    )
                    field_values[key] = None
                    continue

                # Signs check: for capex, compare magnitudes
                if key == "capital_expenditures":
                    val_a = abs(g_dec)
                    val_b = abs(o_dec)
                else:
                    if (g_dec > 0 and o_dec < 0) or (g_dec < 0 and o_dec > 0):
                        rejected_keys.append(key)
                        conflicts.append(
                            {
                                "field": key,
                                "reason": "sign_conflict",
                                "gemini": float(g_dec),
                                "openai": float(o_dec),
                            }
                        )
                        field_values[key] = None
                        continue
                    val_a = g_dec
                    val_b = o_dec

                diff = abs(val_a - val_b)
                denom = max(abs(val_a), abs(val_b))

                if denom == 0:
                    rel_diff = 0.0
                else:
                    rel_diff = float(diff / denom)

                if rel_diff <= self._relative_tolerance:
                    # Agreement within 5%
                    accepted_val = g_dec
                    if key == "capital_expenditures":
                        accepted_val = abs(accepted_val)
                    field_values[key] = accepted_val
                    validated_keys.append(key)
                else:
                    rejected_keys.append(key)
                    conflicts.append(
                        {
                            "field": key,
                            "reason": f"relative_difference_{rel_diff:.4f}_exceeds_threshold_{self._relative_tolerance}",
                            "gemini": float(g_dec),
                            "openai": float(o_dec),
                            "relative_diff": round(rel_diff, 4),
                        }
                    )
                    field_values[key] = None
            else:
                # Single-model mode: require internal accounting consistency
                single_dec = g_dec if g_dec is not None else o_dec
                if single_dec is not None:
                    if key == "capital_expenditures":
                        single_dec = abs(single_dec)
                    field_values[key] = single_dec
                    validated_keys.append(key)
                else:
                    field_values[key] = None

        # 4. P1-03: Shares Outstanding Safeguards
        # Shareholding percentages (<= 100) must NEVER be treated as shares outstanding
        shares = field_values.get("shares_outstanding")
        if shares is not None:
            if shares <= Decimal("100.0"):
                rejected_keys.append("shares_outstanding")
                if "shares_outstanding" in validated_keys:
                    validated_keys.remove("shares_outstanding")
                conflicts.append(
                    {
                        "field": "shares_outstanding",
                        "reason": "shares_value_resembles_percentage_rejected",
                        "value": float(shares),
                    }
                )
                field_values["shares_outstanding"] = None

        # 5. Financial Integrity: Balance Sheet Equation (Assets = Liabilities + Equity)
        tot_assets = field_values.get("total_assets")
        tot_liab = field_values.get("total_liabilities")
        tot_equity = field_values.get("total_equity")
        if tot_assets is not None and tot_liab is not None and tot_equity is not None:
            if tot_assets < Decimal("0"):
                for bs_k in ("total_assets", "total_liabilities", "total_equity"):
                    if bs_k in validated_keys:
                        validated_keys.remove(bs_k)
                    rejected_keys.append(bs_k)
                    field_values[bs_k] = None
                conflicts.append(
                    {
                        "field": "total_assets",
                        "reason": "negative_total_assets_rejected",
                    }
                )
            else:
                calc_liab_eq = tot_liab + tot_equity
                bs_diff = abs(tot_assets - calc_liab_eq)
                bs_denom = max(abs(tot_assets), Decimal("1"))
                bs_rel_diff = float(bs_diff / bs_denom)
                if bs_rel_diff > 0.05:
                    for bs_k in ("total_assets", "total_liabilities", "total_equity"):
                        if bs_k in validated_keys:
                            validated_keys.remove(bs_k)
                        rejected_keys.append(bs_k)
                        field_values[bs_k] = None
                    conflicts.append(
                        {
                            "field": "balance_sheet_equation",
                            "reason": f"assets_liabilities_equity_equation_mismatch_{bs_rel_diff:.4f}",
                            "total_assets": float(tot_assets),
                            "total_liabilities": float(tot_liab),
                            "total_equity": float(tot_equity),
                        }
                    )

        # 6. Financial Integrity: Cash Flow Equation (FCF = OCF - Capex)
        ocf = field_values.get("operating_cash_flow")
        capex = field_values.get("capital_expenditures")
        fcf = field_values.get("free_cash_flow")
        if ocf is not None and capex is not None and fcf is not None:
            calc_fcf = ocf - abs(capex)
            cf_diff = abs(calc_fcf - fcf)
            cf_denom = max(abs(fcf), Decimal("1"))
            cf_rel_diff = float(cf_diff / cf_denom)
            if cf_rel_diff > 0.05:
                for cf_k in ("capital_expenditures", "free_cash_flow"):
                    if cf_k in validated_keys:
                        validated_keys.remove(cf_k)
                    rejected_keys.append(cf_k)
                    field_values[cf_k] = None
                conflicts.append(
                    {
                        "field": "cash_flow_equation",
                        "reason": f"fcf_equation_mismatch_{cf_rel_diff:.4f}",
                        "operating_cash_flow": float(ocf),
                        "capital_expenditures": float(capex),
                        "free_cash_flow": float(fcf),
                    }
                )

        # 7. Reject negative revenue
        rev = field_values.get("revenue")
        if rev is not None and rev < Decimal("0"):
            if "revenue" in validated_keys:
                validated_keys.remove("revenue")
            rejected_keys.append("revenue")
            field_values["revenue"] = None
            conflicts.append(
                {
                    "field": "revenue",
                    "reason": "negative_revenue_rejected",
                }
            )

        # 8. Determine final recovery status
        essential_keys = {
            "revenue",
            "net_income",
            "total_assets",
            "total_equity",
            "operating_cash_flow",
        }
        validated_set = set(validated_keys)
        has_essential = essential_keys.issubset(validated_set)
        has_any = len(validated_keys) > 0

        if has_essential and len(conflicts) == 0:
            status = StatementRecoveryStatus.RECOVERED_AND_VALIDATED
        elif has_any:
            status = StatementRecoveryStatus.PARTIALLY_RECOVERED
        else:
            status = (
                StatementRecoveryStatus.CONFLICT_REJECTED
                if conflicts
                else StatementRecoveryStatus.UNAVAILABLE
            )

        return {
            "status": status,
            "period_end": period_end,
            "period_type": period_type,
            "currency": currency,
            "basis": basis,
            "unit_scale": scale_str,
            "fields": field_values,
            "validated_keys": validated_keys,
            "rejected_keys": rejected_keys,
            "conflicts": conflicts,
            "reason": None
            if status
            in (
                StatementRecoveryStatus.RECOVERED_AND_VALIDATED,
                StatementRecoveryStatus.PARTIALLY_RECOVERED,
            )
            else "No fields survived cross-validation and integrity checks",
        }

    def _build_statement_bundle(
        self,
        *,
        symbol: str,
        exchange: str | None,
        currency: str,
        period_end: date,
        filing_date: str | None,
        period_type: str,
        basis: str,
        unit_scale: str,
        fields: dict[str, Decimal | None],
        source_url: str | None,
        models_used: tuple[str, ...],
        status: StatementRecoveryStatus,
        validated_keys: tuple[str, ...],
        rejected_keys: tuple[str, ...],
        conflicts: tuple[dict[str, Any], ...],
    ) -> AuthenticatedFinancialStatements:
        def _f(key: str) -> StatementField:
            v = fields.get(key)
            return StatementField.of(v) if v is not None else StatementField.missing()

        shares_field = _f("shares_outstanding")

        f_date = None
        if filing_date:
            try:
                f_date = date.fromisoformat(str(filing_date)[:10])
            except ValueError:
                f_date = None

        period = AuthenticatedStatementPeriod(
            period_type=period_type,
            fiscal_year=period_end.year,
            fiscal_quarter=None,
            period_end=period_end,
            filing_date=f_date,
            reporting_currency=currency,
            restated=False,
            statement_basis=basis,
            unit_scale="actual",
            shares_outstanding=shares_field,
            revenue=_f("revenue"),
            cost_of_revenue=_f("cost_of_revenue"),
            gross_profit=_f("gross_profit"),
            operating_income=_f("operating_income"),
            ebit=_f("ebit"),
            ebitda=_f("ebitda"),
            net_income=_f("net_income"),
            eps_basic=_f("eps_basic"),
            eps_diluted=_f("eps_diluted"),
            cash_and_equivalents=_f("cash_and_equivalents"),
            current_assets=_f("current_assets"),
            total_assets=_f("total_assets"),
            current_liabilities=_f("current_liabilities"),
            total_liabilities=_f("total_liabilities"),
            total_equity=_f("total_equity"),
            total_debt=_f("total_debt"),
            long_term_debt=_f("long_term_debt"),
            operating_cash_flow=_f("operating_cash_flow"),
            investing_cash_flow=_f("investing_cash_flow"),
            financing_cash_flow=_f("financing_cash_flow"),
            capital_expenditures=_f("capital_expenditures"),
            free_cash_flow=_f("free_cash_flow"),
            dividends_paid=StatementField.missing(),
            share_buybacks=StatementField.missing(),
            roe=StatementField.missing(),
            roce=StatementField.missing(),
            debt_to_equity=StatementField.missing(),
            working_capital=StatementField.missing(),
            gross_margin=StatementField.missing(),
            operating_margin=StatementField.missing(),
            net_margin=StatementField.missing(),
            revenue_growth=StatementField.missing(),
            eps_growth=StatementField.missing(),
        )

        identity = CompanyIdentity(
            symbol=symbol,
            exchange=exchange,
            currency=currency,
        )

        provenance = FinancialStatementProvenance(
            provider_id="filings_recovery",
            provider_name="Authoritative Regulatory Filings Recovery",
            source_type="official_regulatory_filing",
            retrieved_at=utc_now(),
            auth_mode="verified_public_filing",
            metadata={
                "source_url": source_url or "",
                "models_used": ",".join(models_used),
                "statement_basis": basis,
                "recovery_status": status.value,
                "validated_fields": ",".join(validated_keys),
                "rejected_fields": ",".join(rejected_keys),
                "conflicts_count": str(len(conflicts)),
            },
        )

        return AuthenticatedFinancialStatements(
            identity=identity,
            periods=(period,),
            provenance=provenance,
            reporting_currency=currency,
        )


_LOCK = threading.Lock()
_SERVICE: StatementRecoveryService | None = None


def get_statement_recovery_service() -> StatementRecoveryService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            _SERVICE = StatementRecoveryService()
        return _SERVICE


def reset_statement_recovery_service_for_tests(
    service: StatementRecoveryService | None = None,
) -> None:
    global _SERVICE
    with _LOCK:
        _SERVICE = service
