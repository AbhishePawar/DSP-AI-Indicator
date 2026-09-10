"""RAW → RECONCILED → VERIFIED. Agents cannot write VERIFIED."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from data_engine.official_research.dsp_gate import (
    default_unverified_assumptions,
    dsp_gate,
)
from data_engine.official_research.models import (
    EvidenceItem,
    EvidenceStage,
    FailureStatus,
    ResearchResult,
)
from data_engine.official_research.source_policy import SourcePolicy
from data_engine.official_research.verified_dataset import (
    FinancialField,
    FinancialSnapshotVerified,
    SecurityIdentity,
    ShareCountSnapshot,
    VerifiedDataset,
)

__all__ = ["EvidenceJudge"]


class EvidenceJudge:
    """DSP judge. Never promotes LLM answers or secondary sources."""

    def __init__(self, policy: SourcePolicy | None = None) -> None:
        self._policy = policy or SourcePolicy()

    def ingest_raw(self, item: EvidenceItem) -> EvidenceItem:
        if item.stage != "RAW":
            raise ValueError("ingest_raw requires stage=RAW")
        if item.status == "VERIFIED":
            raise ValueError("RAW evidence cannot already be VERIFIED")
        return item

    def reconcile(self, item: EvidenceItem) -> EvidenceItem:
        if item.stage != "RAW":
            raise ValueError("reconcile requires RAW evidence")
        if item.identity_status != "PASS":
            return self._copy(item, stage="RECONCILED", status="UNKNOWN")
        if item.semantic_status != "PASS":
            return self._copy(item, stage="RECONCILED", status="UNKNOWN")
        if item.value is None or item.value == "":
            return self._copy(item, stage="RECONCILED", status="UNKNOWN")
        if not self._policy.may_verify(item.source_url, source_type=item.source_type):
            if self._policy.is_discovery_only(
                item.source_url, source_type=item.source_type
            ):
                return self._copy(item, stage="RECONCILED", status="UNAVAILABLE")
            return self._copy(item, stage="RECONCILED", status="UNAVAILABLE")
        return self._copy(item, stage="RECONCILED", status="UNKNOWN")

    def verify(self, item: EvidenceItem, *, production: bool = False) -> EvidenceItem:
        if item.stage != "RECONCILED":
            raise ValueError(
                "verify requires RECONCILED evidence; RAW cannot enter DSP"
            )
        if production and item.mode == "MOCK":
            return self._copy(item, status="UNAVAILABLE")
        if item.value is None or item.value == "":
            return self._copy(item, status="UNKNOWN")
        if item.identity_status != "PASS" or item.semantic_status != "PASS":
            return self._copy(item, status="UNKNOWN")
        if item.freshness_status == "FAIL":
            return self._copy(item, status="REFRESH_REQUIRED")
        if item.corporate_action_status == "REFRESH_REQUIRED":
            return self._copy(item, status="REFRESH_REQUIRED")
        if item.corporate_action_status == "CONFLICT":
            return self._copy(item, status="CONFLICT")
        if item.corporate_action_status == "FAIL":
            return self._copy(item, status="REFRESH_REQUIRED")
        if (
            item.field == "shares_outstanding"
            and item.corporate_action_status == "UNKNOWN"
        ):
            return self._copy(item, status="UNKNOWN")
        if item.source_type in {"llm", "agent_claim"}:
            return self._copy(item, status="UNAVAILABLE")
        if item.field == "shares_outstanding" and item.as_of is None:
            return self._copy(item, status="UNKNOWN")
        if not self._policy.may_verify(item.source_url, source_type=item.source_type):
            return self._copy(item, status="UNAVAILABLE")
        if item.agent in {
            "gemini_find",
            "chatgpt_verify",
            "deep_search_attack",
            "claude_review",
        } and item.source_type not in {"exchange_eod", "company_ir", "regulator"}:
            return self._copy(item, status="UNAVAILABLE")
        return self._copy(item, stage="VERIFIED", status="VERIFIED")

    def promote(self, item: EvidenceItem, *, production: bool = False) -> EvidenceItem:
        raw = self.ingest_raw(item)
        reconciled = self.reconcile(raw)
        return self.verify(reconciled, production=production)

    def build_verified_dataset(
        self,
        result: ResearchResult,
        *,
        extra: tuple[EvidenceItem, ...] = (),
        production: bool = False,
        capital_events: tuple = (),
    ) -> VerifiedDataset:
        """Assemble the only dataset allowed into DSP."""
        if production and result.mode == "MOCK":
            return VerifiedDataset(
                identity=None,
                identity_status="UNAVAILABLE",
                price=None,
                price_status="UNAVAILABLE",
                shares=None,
                shares_status="UNAVAILABLE",
                financials=None,
                corporate_action_status="UNKNOWN",
                evidence=(),
                currentness_status="UNAVAILABLE",
                data_quality_status="UNAVAILABLE",
                valuation_gate=self._unavailable_gate(
                    "MOCK evidence cannot enter production"
                ),
                unresolved=("MOCK evidence cannot enter production",),
                mode=result.mode,
            )
        ledger = tuple(result.evidence) + tuple(extra)
        promoted: list[EvidenceItem] = []
        for item in ledger:
            if item.stage == "VERIFIED" and item.status == "VERIFIED":
                if production and item.mode == "MOCK":
                    continue
                promoted.append(item)
                continue
            if item.stage == "RAW":
                try:
                    promoted.append(self.promote(item, production=production))
                except ValueError:
                    promoted.append(item)
            elif item.stage == "RECONCILED":
                promoted.append(self.verify(item, production=production))
            else:
                promoted.append(item)

        verified_rows = tuple(
            item
            for item in promoted
            if item.stage == "VERIFIED" and item.status == "VERIFIED"
        )
        identity = None
        identity_status: FailureStatus = result.identity_status
        if (
            result.identity_status == "VERIFIED"
            and result.isin
            and result.mic
            and result.ticker
            and result.company
        ):
            identity = SecurityIdentity(
                isin=result.isin,
                mic=result.mic,
                ticker=result.ticker,
                company_name=result.company,
            )
        price = result.price
        price_status: FailureStatus = "UNAVAILABLE"
        if price is not None:
            if price.price_kind == "PREVIOUS_CLOSE":
                price_status = "UNAVAILABLE"
                price = None
            elif any(
                item.field in {"eod_close", "price", "ClsPric"}
                and item.status == "VERIFIED"
                for item in verified_rows
            ):
                price_status = "VERIFIED"
            else:
                price_status = "UNAVAILABLE"
                price = None

        shares = self._shares_from(verified_rows, promoted)
        financials = self._financials_from(promoted)
        unresolved = list(result.unresolved)
        for item in promoted:
            if item.field and item.status in {
                "REFRESH_REQUIRED",
                "CONFLICT",
                "UNKNOWN",
            }:
                unresolved.append(f"{item.field}:{item.status}")

        dataset = VerifiedDataset(
            identity=identity,
            identity_status=identity_status,
            price=price if price_status == "VERIFIED" else None,
            price_status=(
                price_status if identity_status == "VERIFIED" else identity_status
            ),
            shares=shares,
            shares_status=shares.status if shares else "UNAVAILABLE",
            financials=financials,
            corporate_action_status=(
                shares.corporate_action_status if shares else "UNKNOWN"
            ),
            evidence=tuple(promoted),
            currentness_status=(
                "VERIFIED" if price_status == "VERIFIED" else "UNAVAILABLE"
            ),
            data_quality_status=(
                "VERIFIED" if identity_status == "VERIFIED" else identity_status
            ),
            valuation_gate=self._unavailable_gate("pending gate"),
            assumptions=default_unverified_assumptions(),
            unresolved=tuple(dict.fromkeys(unresolved)),
            mode=result.mode,
            capital_events=tuple(capital_events),
        )
        decision = dsp_gate(dataset)
        return VerifiedDataset(
            identity=dataset.identity,
            identity_status=dataset.identity_status,
            price=dataset.price,
            price_status=dataset.price_status,
            shares=dataset.shares,
            shares_status=dataset.shares_status,
            financials=dataset.financials,
            corporate_action_status=dataset.corporate_action_status,
            evidence=dataset.evidence,
            currentness_status=dataset.currentness_status,
            data_quality_status=dataset.data_quality_status,
            valuation_gate=decision.valuation,
            assumptions=decision.assumptions,
            unresolved=dataset.unresolved,
            mode=dataset.mode,
            capital_events=tuple(capital_events),
        )

    @staticmethod
    def _unavailable_gate(detail: str):
        from data_engine.official_research.semantics import ValuationGateResult

        return ValuationGateResult(method=None, status="UNAVAILABLE", detail=detail)

    @staticmethod
    def _decimal(raw: str | None) -> Decimal | None:
        if raw is None or raw == "":
            return None
        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            return None

    def _shares_from(
        self,
        verified_rows: tuple[EvidenceItem, ...],
        all_rows: list[EvidenceItem],
    ) -> ShareCountSnapshot | None:
        for item in all_rows:
            if item.field != "shares_outstanding":
                continue
            if item.status == "REFRESH_REQUIRED":
                value = self._decimal(item.value)
                if value is None or item.as_of is None:
                    return ShareCountSnapshot(
                        shares=Decimal("0"),
                        as_of=item.as_of or date.min,
                        current_through=item.current_through or item.as_of or date.min,
                        last_verified_at=item.last_verified_at or item.retrieved_at,
                        source=item.source,
                        corporate_action_status="REFRESH_REQUIRED",
                        status="REFRESH_REQUIRED",
                        evidence_id=item.evidence_id,
                    )
                return ShareCountSnapshot(
                    shares=value,
                    as_of=item.as_of,
                    current_through=item.current_through or item.as_of,
                    last_verified_at=item.last_verified_at or item.retrieved_at,
                    source=item.source,
                    corporate_action_status="REFRESH_REQUIRED",
                    status="REFRESH_REQUIRED",
                    evidence_id=item.evidence_id,
                )
        for item in verified_rows:
            if item.field != "shares_outstanding":
                continue
            value = self._decimal(item.value)
            if value is None or value <= 0 or item.as_of is None:
                continue
            return ShareCountSnapshot(
                shares=value,
                as_of=item.as_of,
                current_through=item.current_through or item.as_of,
                last_verified_at=item.last_verified_at or item.retrieved_at,
                source=item.source,
                corporate_action_status=(
                    "VERIFIED"
                    if item.corporate_action_status in {"PASS", "VERIFIED"}
                    else "UNKNOWN"
                ),
                status="VERIFIED",
                evidence_id=item.evidence_id,
            )
        return None

    def _financials_from(
        self, rows: list[EvidenceItem]
    ) -> FinancialSnapshotVerified | None:
        mapping = {
            "revenue": "revenue",
            "operating_profit": "operating_profit",
            "ebit": "ebit",
            "net_income": "net_income",
            "equity": "equity",
            "cash": "cash",
            "cfo": "cfo",
            "capex": "capex",
            "debt": "debt",
            "total_assets": "total_assets",
            "total_liabilities": "total_liabilities",
        }
        fields: dict[str, FinancialField] = {}
        period_end = None
        basis = None
        field_bases: dict[str, str] = {}
        for name in mapping:
            matches = [item for item in rows if item.field == name]
            verified = [item for item in matches if item.status == "VERIFIED"]
            match: EvidenceItem | None = None
            if len(verified) > 1:
                restated_rows = [
                    item for item in verified if getattr(item, "restated", False)
                ]
                values = {item.value for item in verified}
                bases = {
                    item.statement_basis
                    for item in verified
                    if item.statement_basis
                }
                if restated_rows and len(values) > 1:
                    match = restated_rows[-1]
                elif len(values) > 1 or len(bases) > 1:
                    conflict = verified[0]
                    fields[name] = FinancialField(
                        name=name,
                        value=None,
                        status="CONFLICT",
                        as_of=conflict.as_of,
                        evidence_id=conflict.evidence_id,
                        source=conflict.source,
                    )
                    continue
            if match is None:
                match = next((item for item in matches if item.status == "VERIFIED"), None)
            if match is None:
                match = next(iter(matches), None)
            if match is None:
                fields[name] = FinancialField(
                    name=name, value=None, status="UNAVAILABLE"
                )
                continue
            status = (
                match.status
                if match.status
                in {
                    "VERIFIED",
                    "REFRESH_REQUIRED",
                    "CONFLICT",
                    "UNKNOWN",
                    "UNAVAILABLE",
                }
                else "UNKNOWN"
            )
            value = self._decimal(match.value) if status == "VERIFIED" else None
            if status != "VERIFIED":
                value = None
            fields[name] = FinancialField(
                name=name,
                value=value,
                status=(
                    status
                    if status != "VERIFIED" or value is not None
                    else "UNAVAILABLE"
                ),
                as_of=match.as_of,
                evidence_id=match.evidence_id,
                source=match.source,
            )
            if period_end is None:
                period_end = match.as_of
            if basis is None:
                basis = match.statement_basis
            if status == "VERIFIED" and match.statement_basis:
                field_bases[name] = match.statement_basis
        labeled = set(field_bases.values())
        if len(labeled) > 1:
            fields = {
                name: (
                    FinancialField(
                        name=name,
                        value=None,
                        status="CONFLICT",
                        as_of=item.as_of,
                        evidence_id=item.evidence_id,
                        source=item.source,
                    )
                    if item.status == "VERIFIED"
                    else item
                )
                for name, item in fields.items()
            }
            basis = None
        if all(item.status == "UNAVAILABLE" for item in fields.values()):
            return FinancialSnapshotVerified(
                revenue=fields["revenue"],
                operating_profit=fields["operating_profit"],
                ebit=fields["ebit"],
                net_income=fields["net_income"],
                equity=fields["equity"],
                cash=fields["cash"],
                cfo=fields["cfo"],
                capex=fields["capex"],
                debt=fields["debt"],
                total_assets=fields["total_assets"],
                total_liabilities=fields["total_liabilities"],
                period_end=period_end,
                statement_basis=basis,
                unit_scale="actual",
            )
        return FinancialSnapshotVerified(
            revenue=fields["revenue"],
            operating_profit=fields["operating_profit"],
            ebit=fields["ebit"],
            net_income=fields["net_income"],
            equity=fields["equity"],
            cash=fields["cash"],
            cfo=fields["cfo"],
            capex=fields["capex"],
            debt=fields["debt"],
            total_assets=fields["total_assets"],
            total_liabilities=fields["total_liabilities"],
            period_end=period_end,
            statement_basis=basis,
            unit_scale="actual",
        )

    @staticmethod
    def _copy(
        item: EvidenceItem,
        *,
        stage: EvidenceStage | None = None,
        status: FailureStatus | None = None,
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=item.evidence_id,
            company=item.company,
            ticker=item.ticker,
            isin=item.isin,
            mic=item.mic,
            field=item.field,
            value=item.value,
            as_of=item.as_of,
            retrieved_at=item.retrieved_at,
            source=item.source,
            source_type=item.source_type,
            source_url=item.source_url,
            document_date=item.document_date,
            evidence_locator=item.evidence_locator,
            currency=item.currency,
            unit=item.unit,
            statement_basis=item.statement_basis,
            agent=item.agent,
            identity_status=item.identity_status,
            semantic_status=item.semantic_status,
            freshness_status=item.freshness_status,
            corporate_action_status=item.corporate_action_status,
            confidence=item.confidence,
            stage=stage or item.stage,
            status=status or item.status,
            mode=item.mode,
            raw_price_field=item.raw_price_field,
            current_through=item.current_through,
            last_verified_at=item.last_verified_at,
            period=item.period,
            raw_value=item.raw_value,
            raw_unit=item.raw_unit,
            restated=item.restated,
        )
