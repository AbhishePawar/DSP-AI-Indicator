"""Balance Sheet Intelligence engine (F2.3).

Deterministic domain analysis of normalized BalanceSheet series.
No forecasting, valuation, market data, or provider I/O.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from financial.balance_sheet import BalanceSheet
from financial.intelligence.balance_explainability import (
    BALANCE_RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.balance_models import (
    AssetMetrics,
    BalanceAnalysisMetadata,
    BalanceQualityFlag,
    BalanceSheetAnalysis,
    BalanceTrendSummary,
    EquityMetrics,
    LeverageMetrics,
    LiabilityMetrics,
    LiquidityMetrics,
    WorkingCapitalMetrics,
)
from financial.intelligence.balance_validation import (
    coerce_balance_series,
    validate_balance_for_analysis,
)
from financial.intelligence.income_models import TrendDirection
from financial.intelligence.quality_signals import (
    growth_gap,
    operating_working_capital,
    period_change_rate,
)
from financial.models import FinancialSnapshot, FinancialStatements
from financial.period import PeriodType

__all__ = ["BalanceSheetEngine", "BALANCE_INTELLIGENCE_VERSION"]

BALANCE_INTELLIGENCE_VERSION = "0.3.0-balance"

_STRONG_CURRENT = 1.5
_WEAK_CURRENT = 1.0
_HIGH_DTE = 2.0
_LOW_DTE = 0.5
_HIGH_GOODWILL = 0.25
_HIGH_INTANGIBLES = 0.30
_STRONG_EQUITY_RATIO = 0.40
_WEAK_EQUITY_RATIO = 0.20


def _safe_div(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None:
        return None
    if denom == 0:
        return None
    result = numer / denom
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior)


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _equity(bs: BalanceSheet) -> float | None:
    if bs.total_equity is not None:
        return bs.total_equity
    return bs.equity


def _total_debt(bs: BalanceSheet) -> float | None:
    parts = [bs.short_term_debt, bs.long_term_debt]
    if all(p is None for p in parts):
        return None
    return sum(p or 0.0 for p in parts)


def _current_assets(bs: BalanceSheet) -> float | None:
    if bs.current_assets is not None:
        return bs.current_assets
    parts = [
        bs.cash,
        bs.short_term_investments,
        bs.accounts_receivable,
        bs.inventory,
        bs.other_current_assets,
    ]
    if all(p is None for p in parts):
        return None
    return sum(p or 0.0 for p in parts)


def _confidence(n: int, *, has_value: bool) -> str:
    if not has_value:
        return "insufficient"
    if n >= 3:
        return "high"
    if n >= 2:
        return "medium"
    return "low"


def _trend_from_delta(delta: float | None, *, improve_when_up: bool = True) -> TrendDirection:
    if delta is None:
        return TrendDirection.STABLE
    thr = 0.02
    if abs(delta) < thr:
        return TrendDirection.STABLE
    up = delta > 0
    if improve_when_up:
        return TrendDirection.IMPROVING if up else TrendDirection.WEAKENING
    return TrendDirection.IMPROVING if not up else TrendDirection.WEAKENING


class BalanceSheetEngine:
    """Analyze one or more normalized balance sheets."""

    def analyze(
        self,
        source: BalanceSheet
        | FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[BalanceSheet | FinancialStatements],
        *,
        history: Sequence[BalanceSheet | FinancialStatements] | None = None,
        allow_negative_equity: bool = False,
    ) -> BalanceSheetAnalysis:
        """Run Balance Sheet Intelligence."""
        if history is not None and not isinstance(
            source, (list, tuple, FinancialSnapshot)
        ):
            series: list[Any] = list(history)
            series.append(source)
            balances, stmts, meta = coerce_balance_series(series)
        else:
            balances, stmts, meta = coerce_balance_series(source)

        primary = balances[-1]
        primary_stmt = stmts[-1]
        validation = validate_balance_for_analysis(
            primary,
            statements=primary_stmt,
            allow_negative_equity=allow_negative_equity,
        )

        explanations: list[MetricExplanation] = []
        liquidity = self._liquidity(balances, explanations)
        leverage = self._leverage(primary, explanations)
        assets = self._assets(primary, explanations)
        liabilities = self._liabilities(primary, explanations)
        equity = self._equity_metrics(balances, explanations)
        working = self._working_capital(
            balances,
            stmts,
            liquidity,
            leverage,
            assets,
            equity,
            explanations,
        )
        flags = self._flags(liquidity, leverage, assets, equity, working)
        trends = self._trends(balances, liquidity, leverage, assets, equity)
        metadata = BalanceAnalysisMetadata(
            engine_version=BALANCE_INTELLIGENCE_VERSION,
            periods_used=len(balances),
            primary_period_end=meta.get("period_end"),
            company=str(meta.get("company") or ""),
            ticker=str(meta.get("ticker") or ""),
        )
        return BalanceSheetAnalysis(
            liquidity=liquidity,
            leverage=leverage,
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            working_capital=working,
            quality_flags=flags,
            trend_summary=trends,
            validation=validation,
            explainability=tuple(explanations),
            metadata=metadata,
            research_disclaimer=BALANCE_RESEARCH_DISCLAIMER,
        )

    def _liquidity(
        self,
        balances: Sequence[BalanceSheet],
        out: list[MetricExplanation],
    ) -> LiquidityMetrics:
        bs = balances[-1]
        ca = _current_assets(bs)
        cl = bs.current_liabilities
        cash = bs.cash

        current_ratio = _safe_div(ca, cl)
        quick_numer = None
        if ca is not None:
            inv = bs.inventory or 0.0
            quick_numer = ca - inv
        quick_ratio = _safe_div(quick_numer, cl)
        cash_numer = None
        if cash is not None:
            cash_numer = cash + (bs.short_term_investments or 0.0)
        cash_ratio = _safe_div(cash_numer, cl)

        working_capital = None
        if ca is not None and cl is not None:
            working_capital = ca - cl
        # Net working capital: CA - inventory - CL (stricter)
        net_wc = None
        if ca is not None and cl is not None:
            net_wc = ca - (bs.inventory or 0.0) - cl

        wc_trend = None
        if len(balances) >= 2:
            prev = balances[-2]
            prev_ca = _current_assets(prev)
            prev_cl = prev.current_liabilities
            if (
                working_capital is not None
                and prev_ca is not None
                and prev_cl is not None
            ):
                prev_wc = prev_ca - prev_cl
                delta = _safe_div(working_capital - prev_wc, abs(prev_wc) if prev_wc != 0 else None)
                if delta is None and prev_wc == 0:
                    delta = 0.0 if working_capital == 0 else (1.0 if working_capital > 0 else -1.0)
                wc_trend = _trend_from_delta(delta, improve_when_up=True)
                out.append(
                    build_explanation(
                        name="working_capital_trend",
                        formula="Δ working_capital / |prior WC|",
                        inputs={
                            "current_wc": working_capital,
                            "prior_wc": prev_wc,
                        },
                        intermediates={"delta": delta},
                        result=delta,
                        confidence="medium",
                        interpretation=f"Working capital trend: {wc_trend.value}.",
                        limitations="Requires two periods with current assets and liabilities.",
                    )
                )

        for name, formula, result, inputs in (
            (
                "current_ratio",
                "current_assets / current_liabilities",
                current_ratio,
                {"current_assets": ca, "current_liabilities": cl},
            ),
            (
                "quick_ratio",
                "(current_assets - inventory) / current_liabilities",
                quick_ratio,
                {"current_assets": ca, "inventory": bs.inventory, "current_liabilities": cl},
            ),
            (
                "cash_ratio",
                "(cash + short_term_investments) / current_liabilities",
                cash_ratio,
                {"cash": cash, "short_term_investments": bs.short_term_investments, "current_liabilities": cl},
            ),
            (
                "working_capital",
                "current_assets - current_liabilities",
                working_capital,
                {"current_assets": ca, "current_liabilities": cl},
            ),
        ):
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs=inputs,
                    intermediates={},
                    result=result,
                    confidence=_confidence(1, has_value=result is not None),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} = {result:.4f}."
                    ),
                    limitations="Undefined when denominator is missing or zero.",
                )
            )

        return LiquidityMetrics(
            current_ratio=current_ratio,
            quick_ratio=quick_ratio,
            cash_ratio=cash_ratio,
            working_capital=working_capital,
            net_working_capital=net_wc,
            working_capital_trend=wc_trend,
        )

    def _leverage(
        self, bs: BalanceSheet, out: list[MetricExplanation]
    ) -> LeverageMetrics:
        equity = _equity(bs)
        assets = bs.total_assets
        debt = _total_debt(bs)
        cash = bs.cash or 0.0
        net_debt = None if debt is None else debt - cash

        dte = _safe_div(debt, equity)
        dta = _safe_div(debt, assets)
        equity_ratio = _safe_div(equity, assets)
        ndte = _safe_div(net_debt, equity)

        if dte is not None and dte > _HIGH_DTE:
            summary = "debt-heavy"
        elif dte is not None and dte < _LOW_DTE:
            summary = "equity-heavy"
        elif dte is not None:
            summary = "balanced"
        else:
            summary = "insufficient_data"

        for name, formula, result, inputs in (
            ("debt_to_equity", "total_debt / equity", dte, {"debt": debt, "equity": equity}),
            ("debt_to_assets", "total_debt / total_assets", dta, {"debt": debt, "total_assets": assets}),
            ("equity_ratio", "equity / total_assets", equity_ratio, {"equity": equity, "total_assets": assets}),
            ("net_debt", "total_debt - cash", net_debt, {"debt": debt, "cash": bs.cash}),
            ("net_debt_to_equity", "net_debt / equity", ndte, {"net_debt": net_debt, "equity": equity}),
        ):
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs=inputs,
                    intermediates={},
                    result=result,
                    confidence=_confidence(1, has_value=result is not None),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} = {result:.4f}."
                    ),
                    limitations="Debt uses short-term + long-term debt only.",
                )
            )

        return LeverageMetrics(
            debt_to_equity=dte,
            debt_to_assets=dta,
            equity_ratio=equity_ratio,
            net_debt=net_debt,
            net_debt_to_equity=ndte,
            capital_structure_summary=summary,
        )

    def _assets(
        self, bs: BalanceSheet, out: list[MetricExplanation]
    ) -> AssetMetrics:
        ta = bs.total_assets
        ca = _current_assets(bs)
        ca_comp = _safe_div(ca, ta)
        nca_comp = None if ca_comp is None else max(0.0, 1.0 - ca_comp)
        cash_c = _safe_div(bs.cash, ta)
        inv_c = _safe_div(bs.inventory, ta)
        ar_c = _safe_div(bs.accounts_receivable, ta)
        gw = _safe_div(bs.goodwill, ta)
        intang = _safe_div(bs.intangibles, ta)
        # Asset quality: prefer tangible / liquid — penalize goodwill+intangibles
        soft = None
        if gw is not None or intang is not None:
            soft = (gw or 0.0) + (intang or 0.0)
        quality = None
        if soft is not None:
            quality = _clip01(1.0 - soft)
        elif ca_comp is not None:
            quality = _clip01(0.5 + 0.5 * ca_comp)

        for name, formula, result, inputs in (
            ("current_asset_composition", "current_assets / total_assets", ca_comp, {"current_assets": ca, "total_assets": ta}),
            ("cash_concentration", "cash / total_assets", cash_c, {"cash": bs.cash, "total_assets": ta}),
            ("inventory_concentration", "inventory / total_assets", inv_c, {"inventory": bs.inventory, "total_assets": ta}),
            ("receivable_concentration", "accounts_receivable / total_assets", ar_c, {"accounts_receivable": bs.accounts_receivable, "total_assets": ta}),
            ("goodwill_pct", "goodwill / total_assets", gw, {"goodwill": bs.goodwill, "total_assets": ta}),
            ("intangible_asset_pct", "intangibles / total_assets", intang, {"intangibles": bs.intangibles, "total_assets": ta}),
            ("asset_quality_score", "clip(1 - (goodwill+intangibles)/assets, 0, 1)", quality, {"goodwill_pct": gw, "intangible_pct": intang}),
        ):
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs=inputs,
                    intermediates={},
                    result=result,
                    confidence=_confidence(1, has_value=result is not None),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} = {result:.4f}."
                    ),
                    limitations="Composition uses reported totals when available.",
                )
            )

        return AssetMetrics(
            current_asset_composition=ca_comp,
            non_current_asset_composition=nca_comp,
            cash_concentration=cash_c,
            inventory_concentration=inv_c,
            receivable_concentration=ar_c,
            goodwill_pct=gw,
            intangible_asset_pct=intang,
            asset_quality_score=quality,
        )

    def _liabilities(
        self, bs: BalanceSheet, out: list[MetricExplanation]
    ) -> LiabilityMetrics:
        tl = bs.total_liabilities
        cl_mix = _safe_div(bs.current_liabilities, tl)
        lt_mix = None if cl_mix is None else max(0.0, 1.0 - cl_mix)
        debt = _total_debt(bs)
        debt_structure = _safe_div(bs.long_term_debt, debt)  # LT share of debt
        lease_exp = _safe_div(bs.lease_liabilities, tl)
        deferred_exp = _safe_div(bs.deferred_tax, tl)

        for name, formula, result, inputs in (
            ("current_liability_mix", "current_liabilities / total_liabilities", cl_mix, {"current_liabilities": bs.current_liabilities, "total_liabilities": tl}),
            ("long_term_liability_mix", "1 - current_liability_mix", lt_mix, {"current_liability_mix": cl_mix}),
            ("debt_structure", "long_term_debt / total_debt", debt_structure, {"long_term_debt": bs.long_term_debt, "total_debt": debt}),
            ("lease_liability_exposure", "lease_liabilities / total_liabilities", lease_exp, {"lease_liabilities": bs.lease_liabilities, "total_liabilities": tl}),
            ("deferred_tax_exposure", "deferred_tax / total_liabilities", deferred_exp, {"deferred_tax": bs.deferred_tax, "total_liabilities": tl}),
        ):
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs=inputs,
                    intermediates={},
                    result=result,
                    confidence=_confidence(1, has_value=result is not None),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} = {result:.4f}."
                    ),
                    limitations="Mix ratios require total liabilities.",
                )
            )

        return LiabilityMetrics(
            current_liability_mix=cl_mix,
            long_term_liability_mix=lt_mix,
            debt_structure=debt_structure,
            lease_liability_exposure=lease_exp,
            deferred_tax_exposure=deferred_exp,
        )

    def _equity_metrics(
        self,
        balances: Sequence[BalanceSheet],
        out: list[MetricExplanation],
    ) -> EquityMetrics:
        bs = balances[-1]
        book = _equity(bs)
        gw = bs.goodwill or 0.0
        intang = bs.intangibles or 0.0
        tangible = None if book is None else book - gw - intang
        re_ratio = _safe_div(bs.retained_earnings, book)
        treasury_impact = _safe_div(bs.treasury_shares, book)
        # treasury shares often negative on BS — use abs for impact magnitude
        if treasury_impact is not None:
            treasury_impact = abs(treasury_impact)

        equity_growth = None
        if len(balances) >= 2:
            equity_growth = _growth(book, _equity(balances[-2]))

        # Capital quality: equity ratio × (1 - treasury impact) × tangible/book
        eq_ratio = _safe_div(book, bs.total_assets)
        tang_share = _safe_div(tangible, book) if book and book != 0 else None
        capital_quality = None
        if eq_ratio is not None:
            capital_quality = eq_ratio
            if tang_share is not None:
                capital_quality = _clip01(eq_ratio * max(0.0, tang_share))

        for name, formula, result, inputs in (
            ("book_value", "total_equity (or equity)", book, {"total_equity": bs.total_equity, "equity": bs.equity}),
            ("tangible_book_value", "book_value - goodwill - intangibles", tangible, {"book_value": book, "goodwill": bs.goodwill, "intangibles": bs.intangibles}),
            ("retained_earnings_ratio", "retained_earnings / book_value", re_ratio, {"retained_earnings": bs.retained_earnings, "book_value": book}),
            ("treasury_share_impact", "|treasury_shares| / book_value", treasury_impact, {"treasury_shares": bs.treasury_shares, "book_value": book}),
            ("equity_growth", "(equity_t - equity_t-1) / |equity_t-1|", equity_growth, {"current": book, "prior": _equity(balances[-2]) if len(balances) >= 2 else None}),
            ("capital_quality", "clip(equity_ratio × tangible_share)", capital_quality, {"equity_ratio": eq_ratio, "tangible_share": tang_share}),
        ):
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs=inputs,
                    intermediates={},
                    result=result,
                    confidence=_confidence(len(balances), has_value=result is not None),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} = {result:.4f}."
                    ),
                    limitations="Research heuristic — not an audit of equity accounts.",
                )
            )

        return EquityMetrics(
            book_value=book,
            tangible_book_value=tangible,
            retained_earnings_ratio=re_ratio,
            treasury_share_impact=treasury_impact,
            equity_growth=equity_growth,
            capital_quality=capital_quality,
        )

    def _working_capital(
        self,
        balances: Sequence[BalanceSheet],
        stmts: Sequence[FinancialStatements | None],
        liquidity: LiquidityMetrics,
        leverage: LeverageMetrics,
        assets: AssetMetrics,
        equity: EquityMetrics,
        out: list[MetricExplanation],
    ) -> WorkingCapitalMetrics:
        bs = balances[-1]
        cash_pos = bs.cash
        # Inventory efficiency proxy: lower inventory concentration is better
        inv_eff = None
        if assets.inventory_concentration is not None:
            inv_eff = _clip01(1.0 - assets.inventory_concentration)
        recv_dep = assets.receivable_concentration
        # Liquidity buffer: cash ratio clipped
        buffer = _clip01(liquidity.cash_ratio) if liquidity.cash_ratio is not None else None
        # Short-term solvency: current ratio scaled (2.0 → 1.0)
        solvency = None
        if liquidity.current_ratio is not None:
            solvency = _clip01(liquidity.current_ratio / 2.0)

        liq_q = solvency
        cap_q = equity.capital_quality
        asset_q = assets.asset_quality_score
        debt_burden = _clip01(leverage.debt_to_assets) if leverage.debt_to_assets is not None else None
        # Flexibility: high equity, low net debt/equity, strong liquidity
        flex = None
        parts = [p for p in (solvency, cap_q, asset_q) if p is not None]
        if parts:
            flex = sum(parts) / len(parts)
            if debt_burden is not None:
                flex = _clip01(flex * (1.0 - 0.5 * debt_burden))

        strength_parts = [p for p in (liq_q, cap_q, asset_q, flex) if p is not None]
        strength = sum(strength_parts) / len(strength_parts) if strength_parts else None

        owc = operating_working_capital(
            bs.accounts_receivable, bs.inventory, bs.accounts_payable
        )
        owc_change = None
        owc_change_rate = None
        ar_g = None
        inv_g = None
        ap_g = None
        ar_vs_rev = None
        inv_vs_rev = None
        ap_vs_cogs = None

        # Adjacent annual fiscal periods only for growth / ΔOWC (never quarterly-as-years).
        if len(balances) >= 2 and len(stmts) >= 2:
            cur_stmt = stmts[-1]
            prev_stmt = stmts[-2]
            if (
                cur_stmt is not None
                and prev_stmt is not None
                and cur_stmt.period.period_type is PeriodType.ANNUAL
                and prev_stmt.period.period_type is PeriodType.ANNUAL
                and cur_stmt.period.fiscal_year is not None
                and prev_stmt.period.fiscal_year is not None
                and cur_stmt.period.fiscal_year > prev_stmt.period.fiscal_year
            ):
                prev = balances[-2]
                prev_owc = operating_working_capital(
                    prev.accounts_receivable, prev.inventory, prev.accounts_payable
                )
                if owc is not None and prev_owc is not None:
                    owc_change = owc - prev_owc
                    owc_change_rate = period_change_rate(owc, prev_owc)
                ar_g = period_change_rate(bs.accounts_receivable, prev.accounts_receivable)
                inv_g = period_change_rate(bs.inventory, prev.inventory)
                ap_g = period_change_rate(bs.accounts_payable, prev.accounts_payable)
                rev_g = period_change_rate(
                    cur_stmt.income_statement.revenue,
                    prev_stmt.income_statement.revenue,
                )
                cogs_g = period_change_rate(
                    cur_stmt.income_statement.cogs,
                    prev_stmt.income_statement.cogs,
                )
                ar_vs_rev = growth_gap(ar_g, rev_g)
                inv_vs_rev = growth_gap(inv_g, rev_g)
                ap_vs_cogs = growth_gap(ap_g, cogs_g)

        out.append(
            build_explanation(
                name="balance_sheet_strength",
                formula="mean(liquidity_quality, capital_quality, asset_quality, flexibility)",
                inputs={
                    "liquidity_quality": liq_q,
                    "capital_quality": cap_q,
                    "asset_quality": asset_q,
                    "financial_flexibility": flex,
                },
                intermediates={},
                result=strength,
                confidence=_confidence(1, has_value=strength is not None),
                interpretation=(
                    "Strength unavailable."
                    if strength is None
                    else f"Balance sheet strength score = {strength:.4f}."
                ),
                limitations="Composite research score — not a credit rating.",
            )
        )
        out.append(
            build_explanation(
                name="operating_working_capital",
                formula="accounts_receivable + inventory - accounts_payable",
                inputs={
                    "accounts_receivable": bs.accounts_receivable,
                    "inventory": bs.inventory,
                    "accounts_payable": bs.accounts_payable,
                },
                intermediates={
                    "owc_change": owc_change,
                    "receivables_vs_revenue_growth": ar_vs_rev,
                    "inventory_vs_revenue_growth": inv_vs_rev,
                },
                result=owc,
                confidence=_confidence(1, has_value=owc is not None),
                interpretation=(
                    "Operating working capital unavailable."
                    if owc is None
                    else f"Operating WC = {owc:.4f}."
                ),
                limitations=(
                    "Requires AR, inventory, and AP. Excludes cash and debt by design. "
                    "Growth gaps are evidence only — no invented warning thresholds. "
                    "Authenticated vendor schemas that omit AR/Inv/AP remain unavailable."
                ),
            )
        )

        return WorkingCapitalMetrics(
            cash_position=cash_pos,
            inventory_efficiency=inv_eff,
            receivable_dependence=recv_dep,
            liquidity_buffer=buffer,
            short_term_solvency=solvency,
            balance_sheet_strength=strength,
            liquidity_quality=liq_q,
            capital_quality=cap_q,
            asset_quality=asset_q,
            debt_burden=debt_burden,
            financial_flexibility=flex,
            operating_working_capital=owc,
            operating_working_capital_change=owc_change,
            operating_working_capital_change_rate=owc_change_rate,
            receivables_growth=ar_g,
            inventory_growth=inv_g,
            payables_growth=ap_g,
            receivables_vs_revenue_growth=ar_vs_rev,
            inventory_vs_revenue_growth=inv_vs_rev,
            payables_vs_cogs_growth=ap_vs_cogs,
        )

    def _flags(
        self,
        liquidity: LiquidityMetrics,
        leverage: LeverageMetrics,
        assets: AssetMetrics,
        equity: EquityMetrics,
        working: WorkingCapitalMetrics,
    ) -> tuple[BalanceQualityFlag, ...]:
        flags: list[BalanceQualityFlag] = []
        cr = liquidity.current_ratio
        if cr is not None:
            if cr >= _STRONG_CURRENT:
                flags.append(BalanceQualityFlag.STRONG_LIQUIDITY)
            elif cr < _WEAK_CURRENT:
                flags.append(BalanceQualityFlag.WEAK_LIQUIDITY)

        if leverage.debt_to_equity is not None:
            if leverage.debt_to_equity >= _HIGH_DTE:
                flags.append(BalanceQualityFlag.EXCESSIVE_LEVERAGE)
            elif leverage.debt_to_equity <= _LOW_DTE:
                flags.append(BalanceQualityFlag.CONSERVATIVE_CAPITAL_STRUCTURE)

        if assets.goodwill_pct is not None and assets.goodwill_pct >= _HIGH_GOODWILL:
            flags.append(BalanceQualityFlag.HIGH_GOODWILL)
        if (
            assets.intangible_asset_pct is not None
            and assets.intangible_asset_pct >= _HIGH_INTANGIBLES
        ):
            flags.append(BalanceQualityFlag.HIGH_INTANGIBLE_ASSETS)

        if (
            (liquidity.working_capital is not None and liquidity.working_capital < 0)
            or (cr is not None and cr < _WEAK_CURRENT)
        ):
            flags.append(BalanceQualityFlag.WORKING_CAPITAL_PRESSURE)

        if leverage.equity_ratio is not None:
            if leverage.equity_ratio >= _STRONG_EQUITY_RATIO:
                flags.append(BalanceQualityFlag.STRONG_EQUITY_BASE)
            elif leverage.equity_ratio < _WEAK_EQUITY_RATIO:
                flags.append(BalanceQualityFlag.WEAK_EQUITY_BASE)

        warning = (
            BalanceQualityFlag.WEAK_LIQUIDITY in flags
            or BalanceQualityFlag.EXCESSIVE_LEVERAGE in flags
            or BalanceQualityFlag.WORKING_CAPITAL_PRESSURE in flags
            or BalanceQualityFlag.WEAK_EQUITY_BASE in flags
        )
        healthy = (
            BalanceQualityFlag.STRONG_LIQUIDITY in flags
            and BalanceQualityFlag.STRONG_EQUITY_BASE in flags
            and BalanceQualityFlag.EXCESSIVE_LEVERAGE not in flags
            and BalanceQualityFlag.WORKING_CAPITAL_PRESSURE not in flags
        )
        if healthy:
            flags.append(BalanceQualityFlag.HEALTHY_BALANCE_SHEET)
        elif warning:
            flags.append(BalanceQualityFlag.BALANCE_SHEET_WARNING)

        return tuple(dict.fromkeys(flags))

    def _trends(
        self,
        balances: Sequence[BalanceSheet],
        liquidity: LiquidityMetrics,
        leverage: LeverageMetrics,
        assets: AssetMetrics,
        equity: EquityMetrics,
    ) -> BalanceTrendSummary:
        if len(balances) < 2:
            return BalanceTrendSummary()

        prev = balances[-2]
        # Liquidity trend via current ratio
        prev_ca = _current_assets(prev)
        prev_cr = _safe_div(prev_ca, prev.current_liabilities)
        cr_delta = None
        if liquidity.current_ratio is not None and prev_cr is not None:
            cr_delta = liquidity.current_ratio - prev_cr
        liq_trend = _trend_from_delta(cr_delta, improve_when_up=True)

        prev_debt = _total_debt(prev)
        prev_eq = _equity(prev)
        prev_dte = _safe_div(prev_debt, prev_eq)
        dte_delta = None
        if leverage.debt_to_equity is not None and prev_dte is not None:
            dte_delta = leverage.debt_to_equity - prev_dte
        lev_trend = _trend_from_delta(dte_delta, improve_when_up=False)

        prev_gw = _safe_div(prev.goodwill, prev.total_assets)
        prev_int = _safe_div(prev.intangibles, prev.total_assets)
        prev_soft = None
        if prev_gw is not None or prev_int is not None:
            prev_soft = (prev_gw or 0.0) + (prev_int or 0.0)
        cur_soft = None
        if assets.goodwill_pct is not None or assets.intangible_asset_pct is not None:
            cur_soft = (assets.goodwill_pct or 0.0) + (assets.intangible_asset_pct or 0.0)
        soft_delta = None
        if cur_soft is not None and prev_soft is not None:
            soft_delta = cur_soft - prev_soft
        aq_trend = _trend_from_delta(soft_delta, improve_when_up=False)

        prev_er = _safe_div(prev_eq, prev.total_assets)
        er_delta = None
        if leverage.equity_ratio is not None and prev_er is not None:
            er_delta = leverage.equity_ratio - prev_er
        cap_trend = _trend_from_delta(er_delta, improve_when_up=True)

        wc_trend = liquidity.working_capital_trend or TrendDirection.STABLE

        return BalanceTrendSummary(
            liquidity=liq_trend,
            leverage=lev_trend,
            asset_quality=aq_trend,
            capital_structure=cap_trend,
            working_capital=wc_trend,
        )
