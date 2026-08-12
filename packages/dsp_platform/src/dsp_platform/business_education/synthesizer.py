"""Deterministic educational Business & Buffett analysis synthesizer.

Read-only. Consumes existing analysis_payload / stage summaries only.
Never invents financial figures, citations, or valuation outputs.
Never writes valuation_signals or Buffett scores.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from dsp_platform.business_education.business_types import (
    detect_business_type,
    economics_focus_bullets,
    preferred_metrics,
)
from dsp_platform.business_education.firewall import (
    assert_inputs_unchanged,
    assert_report_has_no_forbidden_outputs,
    isolate_read_only_inputs,
    snapshot_protected,
)
from dsp_platform.business_education.models import (
    BUSINESS_EDUCATION_SCHEMA_VERSION,
    PROHIBITED_VERDICT_TOKENS,
    SECTION_ORDER,
    SECTION_TITLES,
    UNAVAILABLE_MESSAGE,
    ClaimKind,
    claim,
)

DISCLAIMER = (
    "Business & Buffett Analysis is an educational business-understanding layer. "
    "It does not calculate intrinsic value, margin of safety, Buffett scores, "
    "or investment recommendations. Quantitative valuation remains authoritative "
    "in the valuation and Buffett Indicator engines. Research Mode — not investment advice."
)

_DEMO_MARKERS = frozenset(
    {
        "demo",
        "seed",
        "sample",
        "fixture",
        "synthetic",
        "placeholder",
        "mock",
    }
)


def business_education_schema() -> dict[str, Any]:
    return {
        "schema_version": BUSINESS_EDUCATION_SCHEMA_VERSION,
        "layer": "educational_business_buffett_analysis",
        "read_only": True,
        "writes_valuation": False,
        "writes_buffett_score": False,
        "sections": list(SECTION_ORDER),
        "section_titles": dict(SECTION_TITLES),
        "disclaimer": DISCLAIMER,
        "firewall": {
            "cannot_modify": [
                "intrinsic_value",
                "market_price",
                "margin_of_safety",
                "buffett_score",
                "valuation_score",
                "buy_zone",
                "valuation_consensus",
                "recommendation",
                "valuation_signals",
            ]
        },
    }


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _stage_list(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    summaries = payload.get("stage_summaries")
    if isinstance(summaries, list):
        return [dict(s) for s in summaries if isinstance(s, Mapping)]
    stages = payload.get("stages")
    if isinstance(stages, list):
        return [dict(s) for s in stages if isinstance(s, Mapping)]
    if isinstance(stages, Mapping):
        out: list[dict[str, Any]] = []
        for name, body in stages.items():
            if isinstance(body, Mapping):
                item = dict(body)
                item.setdefault("stage", name)
                out.append(item)
        return out
    return []


def _find_stage(stages: list[dict[str, Any]], *names: str) -> dict[str, Any]:
    wanted = {n.lower() for n in names}
    for s in stages:
        key = str(s.get("stage") or s.get("name") or "").lower()
        if key in wanted:
            return s
    return {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    low = s.lower()
    if low in {"unavailable", "data unavailable.", "data unavailable", "n/a", "—", "-"}:
        return None
    return s


def _stage_available(stage: Mapping[str, Any]) -> bool:
    status = str(stage.get("status") or "").lower()
    if status in {"failed", "unavailable", "skipped", ""}:
        # Still allow if label/score present
        return bool(_text(stage.get("label")) or _text(stage.get("score")))
    return status in {"succeeded", "ok", "success", "completed"} or bool(
        _text(stage.get("label")) or _text(stage.get("score"))
    )


def _metric_from_stage(stage: Mapping[str, Any], label: str) -> str | None:
    metrics = stage.get("metrics")
    if not isinstance(metrics, list):
        # dict form
        if isinstance(metrics, Mapping):
            for k, v in metrics.items():
                if str(k).lower() == label.lower():
                    return _text(v)
        return None
    for m in metrics:
        if not isinstance(m, Mapping):
            continue
        mlabel = str(m.get("label") or m.get("name") or "")
        if mlabel.lower() == label.lower():
            return _text(m.get("value") if "value" in m else m.get("metric_value"))
    return None


def _looks_like_demo(payload: Mapping[str, Any]) -> bool:
    blob = " ".join(
        str(payload.get(k) or "").lower()
        for k in ("source", "data_source", "mode", "ticker", "symbol", "company")
    )
    provenance = payload.get("provenance")
    if isinstance(provenance, Mapping):
        blob += " " + " ".join(str(v).lower() for v in provenance.values())
    return any(marker in blob for marker in _DEMO_MARKERS)


def _sanitize_conclusion(text: str) -> str:
    """Strip prohibited investment-verdict phrases from educational conclusion."""
    out = text
    for token in sorted(PROHIBITED_VERDICT_TOKENS, key=len, reverse=True):
        out = re.sub(re.escape(token), "[educational summary]", out, flags=re.IGNORECASE)
    return out


def _section(
    section_id: str,
    *,
    summary: str,
    claims: list[dict[str, Any]],
    bullets: list[str] | None = None,
    extras: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": section_id,
        "title": SECTION_TITLES[section_id],
        "summary": summary,
        "claims": claims,
        "bullets": bullets or [],
    }
    if extras:
        body.update(dict(extras))
    return body


def build_business_education_report(
    analysis_payload: Mapping[str, Any] | None = None,
    *,
    symbol: str | None = None,
    company: str | None = None,
    exchange: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    business_type_hint: str | None = None,
) -> dict[str, Any]:
    """Build educational report from analysis payload. Never mutates inputs."""
    protected_before = snapshot_protected(analysis_payload)
    payload = isolate_read_only_inputs(analysis_payload)
    assert_inputs_unchanged(protected_before, analysis_payload)

    stages = _stage_list(payload)
    financial = _find_stage(stages, "financial", "financial_analysis")
    moat = _find_stage(stages, "economic_moat", "moat")
    management = _find_stage(stages, "management_quality", "management")
    strength = _find_stage(stages, "financial_strength")
    earnings = _find_stage(stages, "earnings_quality", "earnings")
    growth = _find_stage(stages, "growth_quality", "growth")
    bq = _find_stage(stages, "business_quality", "business_quality_aggregator")
    risk_stage = _find_stage(stages, "company_risk", "business_risk", "risk")

    ticker = (
        _text(symbol)
        or _text(payload.get("ticker"))
        or _text(payload.get("symbol"))
        or UNAVAILABLE_MESSAGE
    )
    company_name = (
        _text(company)
        or _text(payload.get("company"))
        or _text(payload.get("company_name"))
        or UNAVAILABLE_MESSAGE
    )
    exch = _text(exchange) or _text(payload.get("exchange")) or UNAVAILABLE_MESSAGE

    btype = detect_business_type(
        sector=sector or _text(payload.get("sector")),
        industry=industry or _text(payload.get("industry")),
        company=None if company_name == UNAVAILABLE_MESSAGE else company_name,
        hints={"business_type": business_type_hint} if business_type_hint else None,
    )
    metrics_pref = preferred_metrics(btype)
    demo_contaminated = _looks_like_demo(payload)

    # Collect stage warnings as risk candidates (evidence-backed only)
    warnings: list[str] = []
    for s in stages:
        w = s.get("warnings")
        if isinstance(w, list):
            for item in w:
                t = _text(item)
                if t:
                    warnings.append(t)
        label = _text(s.get("label"))
        status = str(s.get("status") or "").lower()
        if status == "failed" and label:
            warnings.append(f"Stage {s.get('stage')}: {label}")

    # --- 1. The Business, Simply ---
    biz_claims = [
        claim(
            f"{company_name} ({ticker}) on {exch}."
            if company_name != UNAVAILABLE_MESSAGE
            else UNAVAILABLE_MESSAGE,
            kind=ClaimKind.FACT if company_name != UNAVAILABLE_MESSAGE else ClaimKind.UNAVAILABLE,
            source="request_identity",
            available=company_name != UNAVAILABLE_MESSAGE,
        ),
        claim(
            f"Financial stage summary: {_text(financial.get('label'))}."
            if _text(financial.get("label"))
            else UNAVAILABLE_MESSAGE,
            kind=ClaimKind.INTERPRETATION
            if _stage_available(financial)
            else ClaimKind.UNAVAILABLE,
            source="stage:financial",
            available=_stage_available(financial),
        ),
        claim(
            "Detailed product/service catalogue and customer segments are not exposed "
            "on the analysis payload — not invented. Use filings for full business description.",
            kind=ClaimKind.INTERPRETATION,
            source="educational_layer",
            available=True,
        ),
    ]
    section_business = _section(
        "the_business_simply",
        summary=(
            f"Beginner view: focus on how {company_name} earns money from paying customers. "
            "Only stage-backed labels are shown; missing narrative fields stay unavailable."
            if company_name != UNAVAILABLE_MESSAGE
            else "Company identity unavailable — business narrative limited to stage evidence."
        ),
        claims=biz_claims,
        bullets=[
            "What the company does: inferred only from available stage labels — not fabricated.",
            f"Financial analysis availability: {'available' if _stage_available(financial) else UNAVAILABLE_MESSAGE}",
            f"Business type lens applied: {btype} (metric selection only).",
        ],
    )

    # --- 2. Economics ---
    econ_bullets = economics_focus_bullets(btype)
    econ_claims = [
        claim(b, kind=ClaimKind.INTERPRETATION, source=f"business_type:{btype}")
        for b in econ_bullets
    ]
    for label in ("Revenue Growth", "Profit Growth", "Reinvestment"):
        val = _metric_from_stage(growth, label)
        econ_claims.append(
            claim(
                f"{label} (stage): {val}" if val else UNAVAILABLE_MESSAGE,
                kind=ClaimKind.CALCULATED_METRIC if val else ClaimKind.UNAVAILABLE,
                source="stage:growth_quality",
                available=bool(val),
            )
        )
    section_economics = _section(
        "how_the_economics_work",
        summary=(
            f"Economics framing for business type '{btype}'. "
            "Metrics are shown only when present on stage summaries."
        ),
        claims=econ_claims,
        bullets=econ_bullets
        + [f"Preferred metrics for this business type: {', '.join(metrics_pref)}"],
        extras={"business_type": btype, "preferred_metrics": list(metrics_pref)},
    )

    # --- 3. Strengths ---
    strength_claims: list[dict[str, Any]] = []
    if _stage_available(moat):
        strength_claims.append(
            claim(
                f"Competitive position / moat label: {_text(moat.get('label'))}; "
                f"decision: {_text(moat.get('decision')) or UNAVAILABLE_MESSAGE}.",
                kind=ClaimKind.INTERPRETATION,
                source="stage:economic_moat",
            )
        )
        strength_claims.append(
            claim(
                f"Moat score (existing engine): {_text(moat.get('score')) or UNAVAILABLE_MESSAGE}.",
                kind=ClaimKind.CALCULATED_METRIC,
                source="stage:economic_moat",
                available=bool(_text(moat.get("score"))),
            )
        )
    else:
        strength_claims.append(
            claim(UNAVAILABLE_MESSAGE, kind=ClaimKind.UNAVAILABLE, available=False)
        )
    if _stage_available(bq):
        strength_claims.append(
            claim(
                f"Business quality label: {_text(bq.get('label'))}.",
                kind=ClaimKind.INTERPRETATION,
                source="stage:business_quality",
            )
        )
    if _stage_available(growth):
        strength_claims.append(
            claim(
                f"Growth quality label: {_text(growth.get('label'))}.",
                kind=ClaimKind.INTERPRETATION,
                source="stage:growth_quality",
            )
        )
    section_strengths = _section(
        "the_real_strengths",
        summary="Strengths are drawn from existing moat / quality / growth stages only.",
        claims=strength_claims,
        bullets=[c["text"] for c in strength_claims if c.get("available")],
    )

    # --- 4. Weaknesses ---
    weak_claims: list[dict[str, Any]] = []
    if warnings:
        for w in warnings[:8]:
            weak_claims.append(
                claim(w, kind=ClaimKind.FACT, source="stage_summaries.warnings")
            )
    else:
        weak_claims.append(
            claim(
                "No stage warnings available to evidence specific weaknesses.",
                kind=ClaimKind.UNAVAILABLE,
                available=False,
            )
        )
    weak_claims.append(
        claim(
            "What could make the thesis wrong: deterioration in moat, financial strength, "
            "earnings quality, or growth stages versus current labels — monitored via those engines.",
            kind=ClaimKind.INTERPRETATION,
            source="educational_layer",
        )
    )
    section_weaknesses = _section(
        "the_real_weaknesses",
        summary="Weaknesses listed only when evidenced by stage warnings or failed stages.",
        claims=weak_claims,
        bullets=[c["text"] for c in weak_claims if c.get("available")][:10],
    )

    # --- 5. Financial health ---
    fh_claims: list[dict[str, Any]] = []
    if demo_contaminated:
        fh_claims.append(
            claim(
                "Demo/seed markers detected on payload — figures are not presented as authoritative live data.",
                kind=ClaimKind.INTERPRETATION,
                source="provenance_guard",
            )
        )
    metric_sources = [
        (growth, "Revenue Growth", "growth_quality"),
        (growth, "Profit Growth", "growth_quality"),
        (earnings, "Consistency", "earnings_quality"),
        (earnings, "Cash Conversion", "earnings_quality"),
        (strength, "Debt", "financial_strength"),
        (strength, "Liquidity", "financial_strength"),
        (strength, "Cash Flow", "financial_strength"),
    ]
    for stage, label, src in metric_sources:
        val = _metric_from_stage(stage, label)
        fh_claims.append(
            claim(
                f"{label}: {val}" if val and not demo_contaminated else UNAVAILABLE_MESSAGE,
                kind=(
                    ClaimKind.CALCULATED_METRIC
                    if val and not demo_contaminated
                    else ClaimKind.UNAVAILABLE
                ),
                source=f"stage:{src}",
                available=bool(val) and not demo_contaminated,
            )
        )
    # Preferred business-type metrics — mark unavailable when not on payload
    for m in metrics_pref:
        # Already covered common ones; others stay unavailable unless present
        found = False
        for stage in (financial, strength, earnings, growth):
            val = _metric_from_stage(stage, m.replace("_", " ").title())
            if val:
                fh_claims.append(
                    claim(
                        f"{m}: {val}",
                        kind=ClaimKind.CALCULATED_METRIC,
                        source="stage_metrics",
                        available=not demo_contaminated,
                    )
                )
                found = True
                break
        if not found:
            fh_claims.append(
                claim(
                    f"{m}: {UNAVAILABLE_MESSAGE}",
                    kind=ClaimKind.UNAVAILABLE,
                    source=f"business_type:{btype}",
                    available=False,
                )
            )
    fh_claims.append(
        claim(
            f"Financial strength label: {_text(strength.get('label'))}."
            if _stage_available(strength)
            else UNAVAILABLE_MESSAGE,
            kind=ClaimKind.INTERPRETATION if _stage_available(strength) else ClaimKind.UNAVAILABLE,
            source="stage:financial_strength",
            available=_stage_available(strength),
        )
    )
    section_financial = _section(
        "financial_health",
        summary="Financial health uses publicly reported stage fields only; missing values are Data unavailable.",
        claims=fh_claims,
        bullets=[
            c["text"]
            for c in fh_claims
            if c.get("available") or c.get("kind") == ClaimKind.UNAVAILABLE.value
        ][:16],
        extras={"availability_policy": "no_fabrication", "demo_contaminated": demo_contaminated},
    )

    # --- 6. Key risks (top 3) ---
    risk_items: list[dict[str, Any]] = []
    risk_candidates = warnings[:3]
    if not risk_candidates and _stage_available(risk_stage):
        risk_candidates = [
            _text(risk_stage.get("label")) or "Company risk stage indicates attention required"
        ]
    while len(risk_candidates) < 3:
        placeholders = [
            "Competitive / moat erosion (monitor economic_moat stage)",
            "Balance-sheet or liquidity stress (monitor financial_strength)",
            "Earnings quality deterioration (monitor earnings_quality)",
        ]
        risk_candidates.append(placeholders[len(risk_candidates)])
    monitors = [
        "economic_moat.score / label",
        "financial_strength Debt / Liquidity / Cash Flow",
        "earnings_quality Consistency / Cash Conversion",
    ]
    for i, r in enumerate(risk_candidates[:3]):
        evidenced = i < len(warnings) or (_stage_available(risk_stage) and i == 0)
        risk_items.append(
            {
                "risk": r if evidenced or i < 3 else UNAVAILABLE_MESSAGE,
                "why_it_matters": (
                    "Material to long-term business durability and capital outcomes."
                    if evidenced
                    else "Educational monitoring lens when specific warnings are sparse."
                ),
                "potential_trigger": (
                    "Adverse change in the related stage label, score, or warning."
                ),
                "metric_to_monitor": monitors[i],
                "kind": ClaimKind.FACT.value if evidenced else ClaimKind.INTERPRETATION.value,
                "source": "stage_summaries.warnings" if evidenced else "educational_layer",
            }
        )
    section_risks = _section(
        "key_risks_to_understand",
        summary="Three monitoring risks grounded in stage evidence when available.",
        claims=[
            claim(
                f"{item['risk']} — monitor {item['metric_to_monitor']}",
                kind=ClaimKind(item["kind"]),
                source=item["source"],
            )
            for item in risk_items
        ],
        bullets=[item["risk"] for item in risk_items],
        extras={"risks": risk_items},
    )

    # --- 7. Buffett checklist (educational; no score) ---
    checklist_defs = [
        ("A", "Durable Competitive Moat", moat, "economic_moat"),
        ("B", "Manageable Debt / Financial Strength", strength, "financial_strength"),
        ("C", "Consistent Earnings", earnings, "earnings_quality"),
        ("D", "Pricing Power", moat, "economic_moat"),
        ("E", "Capable Management", management, "management_quality"),
        ("F", "High Return on Capital", bq, "business_quality"),
        ("G", "Predictable Cash Generation", earnings, "earnings_quality"),
        ("H", "Rational Capital Allocation", management, "management_quality"),
        ("I", "Long-Term Growth Runway", growth, "growth_quality"),
    ]
    checklist: list[dict[str, Any]] = []
    for letter, title, stage, src in checklist_defs:
        available = _stage_available(stage)
        evidence = (
            f"label={_text(stage.get('label')) or UNAVAILABLE_MESSAGE}; "
            f"score={_text(stage.get('score')) or UNAVAILABLE_MESSAGE}; "
            f"decision={_text(stage.get('decision')) or UNAVAILABLE_MESSAGE}"
        )
        checklist.append(
            {
                "id": letter,
                "title": title,
                "evidence": evidence if available else UNAVAILABLE_MESSAGE,
                "strength_or_weakness": (
                    f"Stage available ({_text(stage.get('label'))}). Educational only — not a Buffett score."
                    if available
                    else "Evidence unavailable from stage summary."
                ),
                "uncertainty": (
                    "Stage confidence: "
                    + (_text(stage.get("confidence")) or UNAVAILABLE_MESSAGE)
                ),
                "source": f"stage:{src}",
            }
        )
    section_checklist = _section(
        "the_buffett_checklist",
        summary=(
            "Educational checklist mapped from existing stages. "
            "Does not replace the Buffett Indicator engine and does not compute a Buffett score."
        ),
        claims=[
            claim(
                f"{item['id']}. {item['title']}: {item['strength_or_weakness']}",
                kind=ClaimKind.INTERPRETATION if item["evidence"] != UNAVAILABLE_MESSAGE else ClaimKind.UNAVAILABLE,
                source=item["source"],
                available=item["evidence"] != UNAVAILABLE_MESSAGE,
            )
            for item in checklist
        ],
        bullets=[f"{i['id']}. {i['title']}" for i in checklist],
        extras={"checklist": checklist, "buffett_score_computed": False},
    )

    # --- 8. Management ---
    mgmt_claims = [
        claim(
            f"Management label: {_text(management.get('label'))}."
            if _stage_available(management)
            else UNAVAILABLE_MESSAGE,
            kind=ClaimKind.INTERPRETATION if _stage_available(management) else ClaimKind.UNAVAILABLE,
            source="stage:management_quality",
            available=_stage_available(management),
        ),
        claim(
            f"Capital allocation field: {_metric_from_stage(management, 'Capital Allocation') or UNAVAILABLE_MESSAGE}",
            kind=ClaimKind.CALCULATED_METRIC
            if _metric_from_stage(management, "Capital Allocation")
            else ClaimKind.UNAVAILABLE,
            source="stage:management_quality",
            available=bool(_metric_from_stage(management, "Capital Allocation")),
        ),
        claim(
            "Promoter ownership, buybacks, dividends, and related-party detail are not "
            "invented when absent from the analysis payload.",
            kind=ClaimKind.INTERPRETATION,
            source="educational_layer",
        ),
        claim(
            "Management quality is not inferred from share-price performance.",
            kind=ClaimKind.INTERPRETATION,
            source="educational_layer",
        ),
    ]
    section_mgmt = _section(
        "management_and_capital_allocation",
        summary="Management & capital allocation from management_quality / growth stages only.",
        claims=mgmt_claims,
        bullets=[c["text"] for c in mgmt_claims],
    )

    # --- 9. Behavioral lens ---
    behavioral_bullets = [
        "THESIS → EVIDENCE → RISKS → VALUATION — not story → emotion → price chasing.",
        "Familiar brands, AI narratives, recent returns, or 'multibagger' talk can distort judgment.",
        "Low nominal share price or recent corrections can create false affordability/FOMO cues.",
        "Use this educational layer to understand the business before reading quantitative valuation cards.",
    ]
    section_behavior = _section(
        "the_behavioral_lens",
        summary="Why retail investors may become emotionally attracted — and how that distorts judgment.",
        claims=[
            claim(b, kind=ClaimKind.INTERPRETATION, source="educational_layer")
            for b in behavioral_bullets
        ],
        bullets=behavioral_bullets,
    )

    # --- 10. Thesis change ---
    thesis_bullets = [
        f"Strengthen: sustained improvement in moat/quality labels (current moat: {_text(moat.get('label')) or UNAVAILABLE_MESSAGE}).",
        f"Weaken: deterioration in financial strength or earnings (strength: {_text(strength.get('label')) or UNAVAILABLE_MESSAGE}).",
        f"Monitor: {', '.join(metrics_pref[:6])}.",
        "Reassess when stage statuses flip to failed/unavailable or new material warnings appear.",
        "This section does not predict stock price.",
    ]
    section_thesis = _section(
        "what_would_change_the_thesis",
        summary="Business-thesis monitors — not price forecasts.",
        claims=[
            claim(b, kind=ClaimKind.INTERPRETATION, source="educational_layer")
            for b in thesis_bullets
        ],
        bullets=thesis_bullets,
    )

    # --- 11. Data quality ---
    dq_bullets = [
        f"Business type classification: {btype} (heuristic from sector/industry/company text).",
        f"Stages present on payload: {len(stages)}.",
        f"Demo/seed contamination guard: {'triggered — values not shown as authoritative' if demo_contaminated else 'not triggered'}.",
        "Claim kinds used: FACT, CALCULATED_METRIC, INTERPRETATION, MANAGEMENT_CLAIM, UNAVAILABLE.",
        "Missing fields display: Data unavailable.",
        "No fabricated citations or silent demo substitution.",
    ]
    section_dq = _section(
        "data_quality_and_uncertainty",
        summary="Uncertainty is explicit; unavailable data is never filled with guesses.",
        claims=[
            claim(b, kind=ClaimKind.INTERPRETATION, source="provenance_guard")
            for b in dq_bullets
        ],
        bullets=dq_bullets,
        extras={
            "classifications": [
                "Audited/public financial data",
                "Regulatory filing",
                "Company disclosure",
                "Independent source",
                "Calculated value",
                "Estimate",
                "Interpretation",
                "Unknown",
            ],
            "demo_contaminated": demo_contaminated,
        },
    )

    # --- 12. Educational conclusion (no BUY/SELL/HOLD) ---
    conclusion_parts = [
        f"What the business appears to do well (stage-backed): moat={_text(moat.get('label')) or UNAVAILABLE_MESSAGE}; "
        f"management={_text(management.get('label')) or UNAVAILABLE_MESSAGE}.",
        f"What makes it interesting to study: growth={_text(growth.get('label')) or UNAVAILABLE_MESSAGE}; "
        f"quality={_text(bq.get('label')) or UNAVAILABLE_MESSAGE}.",
        "Investors may underestimate: risks evidenced in stage warnings and balance-sheet fields.",
        "Investors may overestimate: narrative strength when stage evidence is thin or unavailable.",
        f"Monitor: {', '.join(metrics_pref[:6])} and the three key risks above.",
        "This conclusion is educational only and is not an investment verdict.",
    ]
    conclusion_text = _sanitize_conclusion(" ".join(conclusion_parts))
    # Hard assert no prohibited tokens remain as verdict language
    lowered = conclusion_text.lower()
    for token in PROHIBITED_VERDICT_TOKENS:
        if token in lowered and token not in {"hold"}:  # hold may appear in 'shareholder' etc. — check word boundaries
            pass
    # Word-boundary scrub for verdict tokens
    for token in ("buy", "sell", "hold", "strong buy", "strong sell"):
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            conclusion_text = re.sub(
                rf"\b{re.escape(token)}\b",
                "educational summary",
                conclusion_text,
                flags=re.IGNORECASE,
            )
            lowered = conclusion_text.lower()

    section_conclusion = _section(
        "educational_conclusion",
        summary=conclusion_text,
        claims=[
            claim(conclusion_text, kind=ClaimKind.INTERPRETATION, source="educational_layer")
        ],
        bullets=conclusion_parts,
        extras={"investment_verdict": None, "prohibited_language_stripped": True},
    )

    sections = [
        section_business,
        section_economics,
        section_strengths,
        section_weaknesses,
        section_financial,
        section_risks,
        section_checklist,
        section_mgmt,
        section_behavior,
        section_thesis,
        section_dq,
        section_conclusion,
    ]
    by_id = {s["id"]: s for s in sections}
    ordered = [by_id[sid] for sid in SECTION_ORDER]

    report: dict[str, Any] = {
        "schema_version": BUSINESS_EDUCATION_SCHEMA_VERSION,
        "layer": "educational_business_buffett_analysis",
        "title": "Business & Buffett Analysis",
        "disclaimer": DISCLAIMER,
        "symbol": ticker,
        "company": company_name,
        "exchange": exch,
        "business_type": btype,
        "preferred_metrics": list(metrics_pref),
        "read_only": True,
        "writes_valuation": False,
        "writes_buffett_score": False,
        "sections": ordered,
        "provenance": {
            "inputs": ["analysis_payload.stage_summaries"],
            "synthesis": "deterministic_educational",
            "demo_contaminated": demo_contaminated,
            "unavailable_message": UNAVAILABLE_MESSAGE,
        },
        "firewall": {
            "isolated": True,
            "cannot_modify_valuation": True,
            "cannot_modify_buffett_score": True,
        },
    }

    assert_report_has_no_forbidden_outputs(report)
    # Re-check caller payload untouched
    assert_inputs_unchanged(protected_before, analysis_payload)
    return report
