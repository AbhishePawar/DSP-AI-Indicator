"""Copilot 2.0 orchestrator — routes questions to existing engines and explains."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from dsp_platform.copilot_v2.intent import (
    COPILOT_MODES,
    classify_intent,
    extract_symbols,
    source_ref,
)
from dsp_platform.copilot_v2.memory import get_copilot_memory_store
import threading
from persistence.research_session import compute_session_id, get_research_session_service

_IDEMPOTENCY_LOCKS_GUARD = threading.Lock()
_IDEMPOTENCY_LOCKS: dict[tuple[str, str, str], threading.Lock] = {}

def _get_idempotency_lock(user_id: str, session_id: str, key: str) -> threading.Lock:
    lock_key = (user_id, session_id, key)
    with _IDEMPOTENCY_LOCKS_GUARD:
        if lock_key not in _IDEMPOTENCY_LOCKS:
            _IDEMPOTENCY_LOCKS[lock_key] = threading.Lock()
        return _IDEMPOTENCY_LOCKS[lock_key]

UNAVAILABLE_MESSAGE = "Data unavailable."
COPILOT_V2_SCHEMA_VERSION = "2.0.0"
COPILOT_V2_SERVICE_VERSION = "0.1.0"


def copilot_v2_schema() -> dict[str, Any]:
    return {
        "schema_version": COPILOT_V2_SCHEMA_VERSION,
        "service_version": COPILOT_V2_SERVICE_VERSION,
        "modes": list(COPILOT_MODES),
        "routes": [
            "/copilot/chat",
            "/copilot/company",
            "/copilot/portfolio",
            "/copilot/valuation",
            "/copilot/comparison",
            "/copilot/document",
            "/copilot/history",
        ],
        "rules": [
            "orchestration_and_explanation_only",
            "reuse_existing_engines",
            "no_duplicated_calculations",
            "no_browser_business_logic",
            "missing_is_data_unavailable",
            "never_fabricate_numbers",
        ],
        "engines_reused": [
            "company_workspace_analyse",
            "valuation_via_analyse_payload",
            "institutional_committee",
            "risk_via_analyse_payload",
            "portfolio_intelligence",
            "comparison",
            "data_connector_filings_news_transcripts",
            "research_copilot_extractive",
            "export_engine",
        ],
    }


def run_copilot_v2(
    *,
    platform: Any,
    message: str,
    mode: str | None = None,
    conversation_id: str | None = None,
    symbol: str | None = None,
    symbols: list[str] | None = None,
    portfolio_id: str | None = None,
    analysis_id: str | None = None,
    user_id: str | None = None,
    idempotency_key: str | None = None,
    analyse_response: Mapping[str, Any] | None = None,
    secondary_analyse_response: Mapping[str, Any] | None = None,
    research_object: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
    portfolio: Mapping[str, Any] | None = None,
    portfolio_intelligence: Mapping[str, Any] | None = None,
    committee_result: Mapping[str, Any] | None = None,
    comparison_result: Mapping[str, Any] | None = None,
    document_kind: str | None = None,
    workspace: str | None = None,
    buffett_mode: bool = False,
    research_orchestrator: Any | None = None,
    language_model: Any | None = None,
    provider_registry: Any | None = None,
    require_ai: bool = False,
) -> dict[str, Any]:
    """Answer using existing engine outputs only — never invent figures."""
    store = get_copilot_memory_store()
    created_at = datetime.now(tz=UTC).isoformat()
    intent = classify_intent(message, mode=mode)
    if buffett_mode or intent == "buffett":
        intent = "buffett" if not mode else intent

    clean_user = str(user_id or "").strip()
    clean_symbol = str(symbol or "").strip().upper()
    clean_analysis = str(analysis_id or "").strip()
    durable = bool(clean_user and clean_symbol and clean_analysis)

    session_service = get_research_session_service() if durable else None
    session_id: str | None = None
    if durable and session_service:
        session_id = compute_session_id(clean_user, clean_symbol, clean_analysis)
        session_service.get_or_create_session(
            user_id=clean_user,
            symbol=clean_symbol,
            analysis_id=clean_analysis,
        )
        cid = session_id
        store.ensure(cid)

        # Hydrate memory store from durable research turns
        durable_turns = session_service.get_turns(session_id, user_id=clean_user)
        with store._lock:
            hydrated: list[dict[str, Any]] = []
            for dt in durable_turns:
                meta = dt.get("metadata") or {}
                hydrated.append({
                    "turn_id": dt.get("turn_id"),
                    "role": dt.get("role"),
                    "message": dt.get("content"),
                    "created_at": dt.get("created_at"),
                    "intent": meta.get("intent", "chat"),
                    "unavailable": meta.get("unavailable", False),
                    "sources": meta.get("sources", []),
                    "idempotency_key": meta.get("idempotency_key"),
                })
            store._turns[cid] = hydrated
    else:
        cid = store.ensure(conversation_id)

    hinted = list(symbols or [])
    if symbol:
        hinted.insert(0, symbol)
    ctx = store.get_context(cid)
    if ctx.get("symbols"):
        hinted.extend(list(ctx["symbols"]))
    resolved_symbols = extract_symbols(message, hinted=hinted)

    context_patch: dict[str, Any] = {
        "previous_questions": [message.strip()] if message.strip() else [],
        "mode": intent,
        "current_workspace": workspace or ctx.get("current_workspace"),
    }
    if resolved_symbols:
        context_patch["symbols"] = resolved_symbols
        context_patch["current_company"] = resolved_symbols[0]
    if portfolio_id:
        context_patch["current_portfolio_id"] = portfolio_id
    if intent == "comparison" and len(resolved_symbols) >= 2:
        context_patch["previous_comparisons"] = [" vs ".join(resolved_symbols[:2])]
    if analyse_response is not None:
        context_patch["selected_valuation"] = "analyse_payload"

    ctx = store.update_context(cid, context_patch)

    clean_idem = str(idempotency_key or "").strip() or None
    lock = _get_idempotency_lock(clean_user or "anon", cid, clean_idem) if (durable and clean_idem) else None

    if lock:
        lock.acquire()
    try:
        if durable and session_service and session_id and clean_idem:
            # Check for existing completed assistant turn for this idempotency key
            turns = session_service.get_turns(session_id, user_id=clean_user)
            user_idx = None
            for idx, t in enumerate(turns):
                if t.get("role") == "user" and (t.get("metadata") or {}).get("idempotency_key") == clean_idem:
                    user_idx = idx
                    break
            if user_idx is not None and user_idx + 1 < len(turns):
                next_t = turns[user_idx + 1]
                if next_t.get("role") == "assistant":
                    next_meta = next_t.get("metadata") or {}
                    return {
                        "response_id": str(uuid.uuid4()),
                        "conversation_id": cid,
                        "created_at": next_t.get("created_at") or created_at,
                        "intent": next_meta.get("intent") or intent,
                        "answer": next_t.get("content") or "",
                        "unavailable": bool(next_meta.get("unavailable", False)),
                        "sources": next_meta.get("sources") or [],
                        "context": ctx,
                        "engine_payload": None,
                        "suggested_questions": _suggested_for(intent, resolved_symbols),
                        "provenance": {
                            "schema_version": COPILOT_V2_SCHEMA_VERSION,
                            "service_version": COPILOT_V2_SERVICE_VERSION,
                            "orchestration_only": True,
                            "calculations_performed": False,
                            "engines_called": bool(next_meta.get("sources")),
                            "replayed_from_idempotency": True,
                        },
                        "message": UNAVAILABLE_MESSAGE if next_meta.get("unavailable") else None,
                    }

        # 8. Persist user turn BEFORE generation
        user_turn_id = str(uuid.uuid4())
        user_meta: dict[str, Any] = {"intent": intent}
        if clean_idem:
            user_meta["idempotency_key"] = clean_idem

        if durable and session_service and session_id:
            session_service.append_turn(
                session_id=session_id,
                user_id=clean_user,
                role="user",
                content=message,
                symbol=clean_symbol,
                analysis_id=clean_analysis,
                turn_id=user_turn_id,
                metadata=user_meta,
            )

        store.append(
            cid,
            {
                "turn_id": user_turn_id,
                "response_id": str(uuid.uuid4()),
                "created_at": created_at,
                "role": "user",
                "message": message,
                "intent": intent,
                "idempotency_key": clean_idem,
            },
        )

        # 9. Execute generation
        is_ai_mandatory = require_ai or durable
        answer, sources, unavailable, engine_payload = _dispatch(
            platform,
            intent=intent,
            message=message,
            symbols=resolved_symbols,
            portfolio_id=portfolio_id or ctx.get("current_portfolio_id"),
            analyse_response=analyse_response,
            secondary_analyse_response=secondary_analyse_response,
            research_object=research_object,
            report=report,
            portfolio=portfolio,
            portfolio_intelligence=portfolio_intelligence,
            committee_result=committee_result,
            comparison_result=comparison_result,
            document_kind=document_kind,
            buffett_mode=buffett_mode or intent == "buffett",
            research_orchestrator=research_orchestrator,
            language_model=language_model,
            provider_registry=provider_registry,
            require_ai=is_ai_mandatory,
        )

        response_id = str(uuid.uuid4())
        asst_turn_id = str(uuid.uuid4())
        asst_meta: dict[str, Any] = {
            "intent": intent,
            "unavailable": unavailable,
            "sources": sources,
        }
        if clean_idem:
            asst_meta["idempotency_key"] = clean_idem

        # 9. Persist assistant turn ONLY after successful generation
        if durable and session_service and session_id:
            session_service.append_turn(
                session_id=session_id,
                user_id=clean_user,
                role="assistant",
                content=answer,
                symbol=clean_symbol,
                analysis_id=clean_analysis,
                turn_id=asst_turn_id,
                metadata=asst_meta,
            )

        store.append(
            cid,
            {
                "turn_id": asst_turn_id,
                "response_id": response_id,
                "created_at": created_at,
                "role": "assistant",
                "message": answer,
                "intent": intent,
                "unavailable": unavailable,
                "sources": sources,
                "idempotency_key": clean_idem,
            },
        )

        return {
            "response_id": response_id,
            "conversation_id": cid,
            "created_at": created_at,
            "intent": intent,
            "answer": answer,
            "unavailable": unavailable,
            "sources": sources,
            "context": ctx,
            "engine_payload": engine_payload,
            "suggested_questions": _suggested_for(intent, resolved_symbols),
            "provenance": {
                "schema_version": COPILOT_V2_SCHEMA_VERSION,
                "service_version": COPILOT_V2_SERVICE_VERSION,
                "orchestration_only": True,
                "calculations_performed": False,
                "engines_called": bool(sources),
            },
            "message": UNAVAILABLE_MESSAGE if unavailable else None,
        }
    finally:
        if lock:
            lock.release()

def _generate_ai_copilot_response(
    *,
    message: str,
    intent: str,
    symbols: list[str],
    evidence_text: str,
    evidence_sources: list[dict[str, Any]],
    evidence_payload: dict[str, Any] | None,
    buffett_mode: bool = False,
    language_model: Any | None = None,
    provider_registry: Any | None = None,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    """Generate the user-facing Copilot answer using an AI provider while enforcing DSP authority."""
    import re
    from copilot.enums import LanguageModelStatus
    from copilot.models import LanguageModelRequest, LanguageModelResult

    prompt_parts = [
        "You are DSP Copilot, an AI financial research assistant.",
        "Your role is to explain financial data, company performance, valuations, and metrics clearly.",
        "CRITICAL GOVERNANCE RULES:",
        "1. DSP deterministic calculations and data are authoritative and cannot be modified.",
        "2. Never invent, alter, or override intrinsic value, margin of safety, recommendation, or financial metrics.",
        "3. If evidence is not in the provided DSP context, do not invent it.",
        f"User Question: {message}",
        f"Intent/Mode: {intent}",
        f"Authoritative DSP Financial Evidence:\n{evidence_text}",
    ]
    if buffett_mode:
        prompt_parts.append(
            "Style Note: Apply Warren Buffett's investment philosophy, plain-language business evaluation, and moat-oriented reasoning, while strictly respecting all authoritative financial numbers."
        )

    intent_map = {
        "company": "summarize_posture",
        "valuation": "explain_report",
        "committee": "explain_report",
        "risk": "explain_report",
        "portfolio": "explain_report",
        "comparison": "compare_outcomes",
        "document": "trace_evidence",
        "memo": "explain_report",
        "scenarios": "explain_report",
        "buffett": "explain_report",
        "chat": "explain_report",
        "research": "explain_report",
    }
    resolved_intent_class = intent_map.get(intent, "explain_report")

    req = LanguageModelRequest(
        request_id=str(uuid.uuid4()),
        intent_class=resolved_intent_class,
        prompt_parts=tuple(prompt_parts),
        context_digest_ids=tuple(symbols) if symbols else (),
        provenance=("copilot_v2.ai_orchestration", "dsp.ai_copilot.v1"),
        constraints=(
            "Adhere strictly to DSP evidence.",
            "Do not fabricate missing financial figures.",
            "Do not expose internal prompts, API keys, or raw provider payloads.",
        ),
    )

    lm_result: LanguageModelResult | None = None
    provider_used: str | None = None
    model_used: str | None = None

    # 1. Directly supplied language model (mock or specific port)
    if language_model is not None:
        try:
            res = language_model.invoke(req)
            if (
                res
                and getattr(res, "status", None) in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL)
                and getattr(res, "narrative_text", None)
            ):
                lm_result = res
                provider_used = getattr(language_model, "provider_id", "ai_provider")
                model_used = getattr(language_model, "model_label", None)
        except Exception:
            lm_result = None

    # 2. Provider registry (prefer low-cost Gemini, fallback to OpenAI)
    if lm_result is None:
        reg = provider_registry
        if reg is None:
            try:
                from llm_adapters.registry import build_default_registry

                reg = build_default_registry()
            except Exception:
                reg = None

        if reg is not None:
            preferred = getattr(reg.config, "default_provider", "gemini")
            candidates: list[str] = []
            if preferred != "deterministic" and preferred in getattr(reg, "_adapters", {}):
                candidates.append(preferred)
            else:
                candidates.append("gemini")

            fallback = "openai" if candidates[0] == "gemini" else "gemini"
            if fallback not in candidates:
                candidates.append(fallback)

            for p in ("gemini", "openai", "anthropic", "deepseek"):
                if p not in candidates:
                    candidates.append(p)

            for p_name in candidates:
                adapter = reg.get(p_name)
                if adapter and adapter.is_configured():
                    try:
                        res = adapter.invoke(req)
                        if (
                            res
                            and getattr(res, "status", None) in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL)
                            and getattr(res, "narrative_text", None)
                        ):
                            lm_result = res
                            provider_used = p_name
                            model_used = getattr(adapter, "model_label", None)
                            break
                    except Exception:
                        pass

                # Direct fallback if gateway provider failed
                direct_adapter = reg.direct_fallback(p_name)
                if direct_adapter and direct_adapter is not adapter and direct_adapter.is_configured():
                    try:
                        res = direct_adapter.invoke(req)
                        if (
                            res
                            and getattr(res, "status", None) in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL)
                            and getattr(res, "narrative_text", None)
                        ):
                            lm_result = res
                            provider_used = p_name
                            model_used = getattr(direct_adapter, "model_label", None)
                            break
                    except Exception:
                        pass

    # 3. Fail closed if no AI provider succeeded
    if lm_result is None or not getattr(lm_result, "narrative_text", None):
        return (
            "AI Copilot is temporarily unavailable. Please try again.",
            [*evidence_sources, source_ref("ai_provider", "unavailable")],
            True,
            None,
        )

    narrative = lm_result.narrative_text.strip()

    # 4. DSP Authority Reconciliation: deterministic values must override AI text
    valuation_map = _from_mapping(evidence_payload, "analyse_response", "valuation") or _from_mapping(evidence_payload, "valuation") or {}
    summary_map = _from_mapping(evidence_payload, "analyse_response", "recommendation_summary") or _from_mapping(evidence_payload, "recommendation_summary") or {}

    dsp_decision = _fmt(
        _from_mapping(summary_map, "label")
        or _from_mapping(summary_map, "decision")
        or _from_mapping(summary_map, "recommendation")
    )
    dsp_mos = _fmt(
        _from_mapping(summary_map, "margin_of_safety")
        or _from_mapping(valuation_map, "margin_of_safety")
    )
    dsp_iv = _fmt(
        _from_mapping(valuation_map, "intrinsic_value")
        or _from_mapping(summary_map, "intrinsic_value")
    )

    if dsp_decision:
        for conflicting_rec in ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"):
            if conflicting_rec.lower() != dsp_decision.lower():
                pattern = re.compile(rf"{re.escape(conflicting_rec)}", re.IGNORECASE)
                narrative = pattern.sub(dsp_decision, narrative)

    auth_lines = []
    if dsp_decision:
        auth_lines.append(f"**Authoritative Recommendation:** {dsp_decision}")
    if dsp_iv:
        auth_lines.append(f"**Valuation:** {dsp_iv}")
    if dsp_mos:
        auth_lines.append(f"**Margin of Safety:** {dsp_mos}")

    if auth_lines:
        auth_block = "\n".join(auth_lines)
        if dsp_decision and f"**Authoritative Recommendation:** {dsp_decision}" not in narrative:
            narrative = f"{narrative}\n\n{auth_block}"
        elif dsp_iv and f"**Valuation:** {dsp_iv}" not in narrative:
            narrative = f"{narrative}\n\n{auth_block}"

    sources = [*evidence_sources, source_ref("ai_provider", f"{provider_used or "gemini"}:{model_used or "default"}")]
    return (narrative, sources, False, evidence_payload)


def _dispatch(
    platform: Any,
    *,
    intent: str,
    message: str,
    symbols: list[str],
    portfolio_id: str | None,
    analyse_response: Mapping[str, Any] | None,
    secondary_analyse_response: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    portfolio: Mapping[str, Any] | None,
    portfolio_intelligence: Mapping[str, Any] | None,
    committee_result: Mapping[str, Any] | None,
    comparison_result: Mapping[str, Any] | None,
    document_kind: str | None,
    buffett_mode: bool,
    research_orchestrator: Any | None = None,
    language_model: Any | None = None,
    provider_registry: Any | None = None,
    require_ai: bool = False,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    if intent == "research":
        return _handle_research(
            platform,
            message=message,
            symbols=symbols,
            analyse_response=analyse_response,
            research_object=research_object,
            report=report,
            research_orchestrator=research_orchestrator,
        )

    handlers = {
        "company": _handle_company,
        "valuation": _handle_valuation,
        "committee": _handle_committee,
        "risk": _handle_risk,
        "portfolio": _handle_portfolio,
        "comparison": _handle_comparison,
        "document": _handle_document,
        "memo": _handle_memo,
        "scenarios": _handle_scenarios,
        "buffett": _handle_buffett,
        "chat": _handle_chat,
    }
    handler = handlers.get(intent, _handle_chat)
    answer, sources, unavailable, payload = cast(Any, handler)(
        platform,
        message=message,
        symbols=symbols,
        portfolio_id=portfolio_id,
        analyse_response=analyse_response,
        secondary_analyse_response=secondary_analyse_response,
        research_object=research_object,
        report=report,
        portfolio=portfolio,
        portfolio_intelligence=portfolio_intelligence,
        committee_result=committee_result,
        comparison_result=comparison_result,
        document_kind=document_kind,
        research_orchestrator=research_orchestrator,
    )
    if buffett_mode and intent != "buffett":
        answer = _buffett_wrap(answer, unavailable=unavailable)
        sources = [*sources, source_ref("explain_like_buffett", "plain_language_wrap")]

    if require_ai:
        if (unavailable and payload is None) or answer.strip() == UNAVAILABLE_MESSAGE or not answer.strip():
            return answer, sources, True, payload
        combined_payload = dict(payload) if isinstance(payload, dict) else {}
        if analyse_response and isinstance(analyse_response, (dict, Mapping)):
            combined_payload["analyse_response"] = dict(analyse_response)
        return _generate_ai_copilot_response(
            message=message,
            intent=intent,
            symbols=symbols,
            evidence_text=answer,
            evidence_sources=sources,
            evidence_payload=combined_payload,
            buffett_mode=buffett_mode,
            language_model=language_model,
            provider_registry=provider_registry,
        )

    return answer, sources, unavailable, payload


def _section(title: str, body: str | None) -> str:
    if not body:
        return f"## {title}\n{UNAVAILABLE_MESSAGE}\n"
    return f"## {title}\n{body}\n"


def _from_mapping(data: Mapping[str, Any] | None, *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


def _fmt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _handle_company(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    del message
    sources: list[dict[str, Any]] = []
    if analyse_response is not None:
        sources.append(source_ref("company_workspace", "analyse_response"))
        summary = _from_mapping(analyse_response, "recommendation_summary") or {}
        stages = _from_mapping(analyse_response, "stage_summaries")
        lines = [
            f"Company analysis for {symbols[0] if symbols else 'current subject'}.",
            f"Decision/label: {_fmt(_from_mapping(summary, 'label') or _from_mapping(summary, 'decision')) or UNAVAILABLE_MESSAGE}",
            f"Margin of Safety: {_fmt(_from_mapping(summary, 'margin_of_safety')) or UNAVAILABLE_MESSAGE}",
            f"Confidence: {_fmt(_from_mapping(summary, 'confidence')) or UNAVAILABLE_MESSAGE}",
        ]
        if isinstance(stages, list) and stages:
            lines.append(f"Stage count (from analyse payload): {len(stages)}")
        return (
            "\n".join(lines),
            sources,
            False,
            {"analyse_response": dict(analyse_response)},
        )

    if research_object is not None or report is not None:
        try:
            grounded = platform.ask_research_copilot(
                "Summarize the company research.",
                research_object=dict(research_object) if research_object else None,
                report=dict(report) if report else None,
            )
            sources.append(source_ref("research_copilot", "ask_research_copilot"))
            answer = str(grounded.get("answer") or UNAVAILABLE_MESSAGE)
            unavailable = (
                bool(grounded.get("unavailable")) or answer == UNAVAILABLE_MESSAGE
            )
            return answer, sources, unavailable, {"research_copilot": grounded}
        except Exception:  # noqa: BLE001
            pass

    if symbols:
        try:
            bundle = platform.get_unified_data_bundle(symbols[0])
            if isinstance(bundle, dict):
                sources.append(source_ref("data_connector", "unified_data_bundle"))
                identity_raw = bundle.get("identity")
                identity: dict[str, Any] = (
                    identity_raw if isinstance(identity_raw, dict) else {}
                )
                return (
                    "\n".join(
                        [
                            f"Workspace data shell for {symbols[0]}.",
                            f"Identity: {_fmt(identity.get('symbol')) or UNAVAILABLE_MESSAGE}",
                            "Full analysis requires a prior Company Workspace /analyse result.",
                            f"Valuation / recommendation: {UNAVAILABLE_MESSAGE}",
                        ]
                    ),
                    sources,
                    True,
                    {"bundle_keys": list(bundle.keys())},
                )
        except Exception:  # noqa: BLE001
            pass

    return UNAVAILABLE_MESSAGE, [source_ref("company_workspace")], True, None


def _handle_valuation(
    platform: Any,
    *,
    message: str,
    analyse_response: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    del platform, message
    payload = analyse_response or research_object
    if payload is None:
        return UNAVAILABLE_MESSAGE, [source_ref("valuation_engine")], True, None

    sources = [source_ref("valuation_engine", "analyse_or_research_object")]
    summary = _from_mapping(payload, "recommendation_summary") or {}
    valuation = (
        _from_mapping(payload, "valuation")
        or _from_mapping(payload, "valuation_signals")
        or _from_mapping(payload, "stages", "valuation")
        or {}
    )
    mos = _fmt(_from_mapping(summary, "margin_of_safety")) or _fmt(
        _from_mapping(valuation, "margin_of_safety")
    )
    iv = _fmt(_from_mapping(valuation, "intrinsic_value")) or _fmt(
        _from_mapping(valuation, "fair_value")
    )
    dcf = _fmt(_from_mapping(valuation, "dcf_assumptions")) or _fmt(
        _from_mapping(valuation, "assumptions")
    )
    buffett = _fmt(_from_mapping(valuation, "buffett_score")) or _fmt(
        _from_mapping(summary, "buffett_score")
    )
    parts = [
        _section("Intrinsic Value", iv),
        _section("Margin of Safety", mos),
        _section("DCF / Assumptions", dcf),
        _section("Buffett Score", buffett),
    ]
    unavailable = all(UNAVAILABLE_MESSAGE in p for p in parts)
    return "\n".join(parts), sources, unavailable, {"valuation": valuation or None}


def _handle_committee(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    committee_result: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    sources: list[dict[str, Any]] = []
    result = committee_result
    if result is None and (
        research_object is not None
        or report is not None
        or analyse_response is not None
    ):
        subject = symbols[0] if symbols else "subject"
        try:
            result = platform.run_institutional_committee(
                subject=subject,
                research_object=dict(research_object) if research_object else None,
                report=dict(report) if report else None,
                portfolio_intelligence=None,
            )
            sources.append(
                source_ref("institutional_committee", "run_institutional_committee")
            )
        except Exception:  # noqa: BLE001
            result = None

    if result is None:
        embedded = _from_mapping(analyse_response, "committee_summary")
        if isinstance(embedded, dict):
            result = embedded
            sources.append(
                source_ref("institutional_committee", "analyse_committee_summary")
            )

    if result is None:
        agents = []
        try:
            agents = platform.list_committee_agents()
            sources.append(
                source_ref("institutional_committee", "list_committee_agents")
            )
        except Exception:  # noqa: BLE001
            agents = []
        return (
            "\n".join(
                [
                    "AI Committee explanation requires a prior committee run or analyse committee summary.",
                    f"Agents registered: {len(agents) if agents else UNAVAILABLE_MESSAGE}",
                    f"Bull / Base / Bear / Voting / Confidence / Minority: {UNAVAILABLE_MESSAGE}",
                    f"Question noted: {message.strip() or UNAVAILABLE_MESSAGE}",
                ]
            ),
            sources or [source_ref("institutional_committee")],
            True,
            {"agents": agents or None},
        )

    bull = _fmt(_from_mapping(result, "bull_case")) or _fmt(
        _from_mapping(result, "scenarios", "bull")
    )
    base = _fmt(_from_mapping(result, "base_case")) or _fmt(
        _from_mapping(result, "scenarios", "base")
    )
    bear = _fmt(_from_mapping(result, "bear_case")) or _fmt(
        _from_mapping(result, "scenarios", "bear")
    )
    voting = _fmt(_from_mapping(result, "voting")) or _fmt(
        _from_mapping(result, "decision")
    )
    confidence = _fmt(_from_mapping(result, "confidence"))
    minority = _fmt(_from_mapping(result, "minority_opinion")) or _fmt(
        _from_mapping(result, "minority")
    )
    text = "\n".join(
        [
            _section("Bull Case", bull),
            _section("Base Case", base),
            _section("Bear Case", bear),
            _section("Voting", voting),
            _section("Confidence", confidence),
            _section("Minority Opinion", minority),
        ]
    )
    unavailable = text.count(UNAVAILABLE_MESSAGE) >= 5
    return (
        text,
        sources,
        unavailable,
        {"committee": dict(result) if isinstance(result, dict) else None},
    )


def _handle_risk(
    platform: Any,
    *,
    message: str,
    analyse_response: Mapping[str, Any] | None,
    portfolio_intelligence: Mapping[str, Any] | None,
    portfolio: Mapping[str, Any] | None,
    symbols: list[str],
    portfolio_id: str | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    del message
    sources: list[dict[str, Any]] = []
    risk = (
        _from_mapping(analyse_response, "risk")
        or _from_mapping(analyse_response, "risk_summary")
        or _from_mapping(analyse_response, "stages", "risk")
    )
    pi = portfolio_intelligence
    if pi is None and (portfolio is not None or symbols):
        try:
            pi = platform.evaluate_portfolio_intelligence(
                portfolio=(
                    dict(portfolio)
                    if portfolio
                    else {
                        "portfolio_id": portfolio_id or "copilot",
                        "holdings": [{"symbol": s} for s in symbols],
                    }
                )
            )
            sources.append(
                source_ref("portfolio_intelligence", "evaluate_portfolio_intelligence")
            )
        except Exception:  # noqa: BLE001
            pi = None

    risk_summary = risk if isinstance(risk, dict) else None
    pi_risk = (
        _from_mapping(pi, "portfolio_risk_summary") if isinstance(pi, dict) else None
    )
    divers = (
        _from_mapping(pi, "diversification_summary") if isinstance(pi, dict) else None
    )
    conc = _from_mapping(pi, "position_concentration") if isinstance(pi, dict) else None

    if risk_summary:
        sources.append(source_ref("risk_engine", "analyse_risk_payload"))
    if pi_risk or divers or conc:
        sources.append(source_ref("portfolio_intelligence", "risk_diversification"))

    if not sources:
        return UNAVAILABLE_MESSAGE, [source_ref("risk_engine")], True, None

    text = "\n".join(
        [
            _section(
                "Risk Score",
                _fmt(_from_mapping(risk_summary, "score"))
                or _fmt(_from_mapping(risk_summary, "risk_score")),
            ),
            _section(
                "Stress Tests",
                _fmt(_from_mapping(risk_summary, "stress_tests")),
            ),
            _section(
                "Monte Carlo",
                _fmt(_from_mapping(risk_summary, "monte_carlo")),
            ),
            _section(
                "Concentration",
                _fmt(_from_mapping(conc, "note")) if isinstance(conc, dict) else None,
            ),
            _section(
                "Diversification",
                (
                    _fmt(_from_mapping(divers, "note"))
                    if isinstance(divers, dict)
                    else None
                ),
            ),
        ]
    )
    # When only notes exist (PI), still available as explanation of linked research gaps
    unavailable = (
        "Risk Score" in text and UNAVAILABLE_MESSAGE in text.split("Stress Tests")[0]
    )
    return text, sources, False, {"risk": risk_summary, "portfolio_intelligence": pi}


def _handle_portfolio(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    portfolio_id: str | None,
    portfolio: Mapping[str, Any] | None,
    portfolio_intelligence: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    del message
    pi = portfolio_intelligence
    sources: list[dict[str, Any]] = []
    if pi is None:
        shell = (
            dict(portfolio)
            if portfolio
            else (
                {
                    "portfolio_id": portfolio_id or "copilot",
                    "holdings": [{"symbol": s} for s in symbols],
                }
                if symbols
                else None
            )
        )
        if shell is None:
            return (
                UNAVAILABLE_MESSAGE,
                [source_ref("portfolio_intelligence")],
                True,
                None,
            )
        try:
            pi = platform.evaluate_portfolio_intelligence(portfolio=shell)
            sources.append(
                source_ref("portfolio_intelligence", "evaluate_portfolio_intelligence")
            )
        except Exception:  # noqa: BLE001
            return (
                UNAVAILABLE_MESSAGE,
                [source_ref("portfolio_intelligence")],
                True,
                None,
            )

    summary = _from_mapping(pi, "portfolio_summary") or {}
    risk = _from_mapping(pi, "portfolio_risk_summary") or {}
    mos = _from_mapping(pi, "margin_of_safety_summary") or {}
    missing = _from_mapping(pi, "missing_research") or []
    text = "\n".join(
        [
            "Portfolio analysis uses Portfolio Intelligence only (no new scores).",
            f"Holdings: {_fmt(_from_mapping(summary, 'holding_count')) or UNAVAILABLE_MESSAGE}",
            f"Linked research: {_fmt(_from_mapping(summary, 'linked_research_count')) or UNAVAILABLE_MESSAGE}",
            f"Missing research: {_fmt(_from_mapping(summary, 'missing_research_count')) or UNAVAILABLE_MESSAGE}",
            f"Risk positions available: {_fmt(_from_mapping(risk, 'available_count')) or UNAVAILABLE_MESSAGE}",
            f"MoS positions available: {_fmt(_from_mapping(mos, 'available_count')) or UNAVAILABLE_MESSAGE}",
            f"Overvalued holding: {UNAVAILABLE_MESSAGE} (requires linked valuation research).",
            f"Diversification suggestion: {UNAVAILABLE_MESSAGE if not missing else 'Cover missing research before suggesting allocation changes.'}",
        ]
    )
    return (
        text,
        sources,
        False,
        {"portfolio_intelligence": dict(pi) if isinstance(pi, dict) else None},
    )


def _handle_comparison(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    secondary_analyse_response: Mapping[str, Any] | None,
    comparison_result: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    del platform, message
    sources: list[dict[str, Any]] = []
    if comparison_result is not None:
        sources.append(source_ref("comparison_engine", "supplied_comparison_result"))
        summary = _fmt(_from_mapping(comparison_result, "summary")) or _fmt(
            _from_mapping(comparison_result, "executive_summary")
        )
        return (
            summary
            or "Comparison artifact present. Detailed narrative fields unavailable.",
            sources,
            summary is None,
            {"comparison": dict(comparison_result)},
        )

    if analyse_response is not None and secondary_analyse_response is not None:
        sources.append(source_ref("comparison_engine", "dual_analyse_payloads"))
        a = symbols[0] if symbols else "A"
        b = symbols[1] if len(symbols) > 1 else "B"
        mos_a = _fmt(
            _from_mapping(
                analyse_response, "recommendation_summary", "margin_of_safety"
            )
        )
        mos_b = _fmt(
            _from_mapping(
                secondary_analyse_response, "recommendation_summary", "margin_of_safety"
            )
        )
        text = "\n".join(
            [
                f"Comparison assistant for {a} vs {b}.",
                "Uses supplied Company Workspace analyse payloads only — no peer scoring.",
                f"{a} Margin of Safety: {mos_a or UNAVAILABLE_MESSAGE}",
                f"{b} Margin of Safety: {mos_b or UNAVAILABLE_MESSAGE}",
                f"Qualitative ranking: {UNAVAILABLE_MESSAGE}",
            ]
        )
        return text, sources, False, None

    if len(symbols) >= 2:
        return (
            f"Compare {symbols[0]} vs {symbols[1]} requires analyse payloads or a comparison result. {UNAVAILABLE_MESSAGE}",
            [source_ref("comparison_engine")],
            True,
            None,
        )
    return UNAVAILABLE_MESSAGE, [source_ref("comparison_engine")], True, None


def _handle_document(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    document_kind: str | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    del message
    if not symbols:
        return UNAVAILABLE_MESSAGE, [source_ref("data_connector")], True, None

    symbol = symbols[0]
    kind = (document_kind or "auto").lower()
    sources: list[dict[str, Any]] = []
    collected: dict[str, Any] = {}

    def _safe(label: str, fn: Any) -> None:
        try:
            payload = fn()
        except Exception:  # noqa: BLE001
            payload = None
        collected[label] = payload
        if payload is not None:
            sources.append(source_ref("data_connector", label))

    if kind in {"auto", "filings", "sec", "nse", "bse"}:
        _safe("filings", lambda: platform.get_authenticated_filings(symbol, limit=5))
    if kind in {"auto", "news"}:
        _safe("news", lambda: platform.get_authenticated_news(symbol, limit=5))
    if kind in {"auto", "transcripts", "conference"}:
        _safe(
            "transcripts",
            lambda: platform.get_authenticated_transcripts(symbol, limit=3),
        )

    if not sources:
        return (
            f"No authenticated documents available for {symbol}. {UNAVAILABLE_MESSAGE}",
            [source_ref("data_connector")],
            True,
            collected,
        )

    lines = [f"Document Q&A for {symbol} (connectors only — no OCR / new parsers)."]
    for label, payload in collected.items():
        if payload is None:
            lines.append(f"{label}: {UNAVAILABLE_MESSAGE}")
            continue
        if isinstance(payload, dict):
            items = (
                payload.get("filings")
                or payload.get("articles")
                or payload.get("transcripts")
                or payload.get("items")
                or []
            )
            count = len(items) if isinstance(items, list) else UNAVAILABLE_MESSAGE
            lines.append(f"{label}: {count} authenticated item(s) retrieved.")
            if isinstance(items, list) and items and isinstance(items[0], dict):
                title = (
                    items[0].get("title")
                    or items[0].get("headline")
                    or items[0].get("filing_type")
                    or items[0].get("form_type")
                )
                lines.append(f"  Latest: {_fmt(title) or UNAVAILABLE_MESSAGE}")
        else:
            lines.append(f"{label}: present")
    lines.append(
        "Content Q&A beyond retrieved metadata requires document bodies in the connector payload; "
        f"full-text answer: {UNAVAILABLE_MESSAGE if not sources else 'limited to authenticated fields above.'}"
    )
    return "\n".join(lines), sources, False, collected


def _handle_memo(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    committee_result: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    **kwargs: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    company_ans, company_src, _, _ = _handle_company(
        platform,
        message=message,
        symbols=symbols,
        analyse_response=analyse_response,
        research_object=research_object,
        report=report,
    )
    val_ans, val_src, _, _ = _handle_valuation(
        platform,
        message=message,
        analyse_response=analyse_response,
        research_object=research_object,
    )
    risk_ans, risk_src, _, _ = _handle_risk(
        platform,
        message=message,
        symbols=symbols,
        analyse_response=analyse_response,
        portfolio_intelligence=kwargs.get("portfolio_intelligence"),
        portfolio=kwargs.get("portfolio"),
        portfolio_id=kwargs.get("portfolio_id"),
    )
    com_ans, com_src, _, com_payload = _handle_committee(
        platform,
        message=message,
        symbols=symbols,
        analyse_response=analyse_response,
        committee_result=committee_result,
        research_object=research_object,
        report=report,
    )
    strengths = _fmt(
        _from_mapping(analyse_response, "recommendation_summary", "strengths")
    )
    weaknesses = _fmt(
        _from_mapping(analyse_response, "recommendation_summary", "weaknesses")
    )
    catalysts = _fmt(
        _from_mapping(analyse_response, "recommendation_summary", "catalysts")
    )
    text = "\n".join(
        [
            "# Investment Memo",
            _section(
                "Investment Thesis",
                company_ans if company_ans != UNAVAILABLE_MESSAGE else None,
            ),
            _section("Strengths", strengths),
            _section("Weaknesses", weaknesses),
            _section("Risks", risk_ans if "Risk Score" in risk_ans else None),
            _section("Catalysts", catalysts),
            _section("Valuation", val_ans),
            _section("AI Committee Summary", com_ans),
        ]
    )
    sources = company_src + val_src + risk_src + com_src
    unavailable = (
        analyse_response is None and research_object is None and report is None
    )
    return (
        text,
        sources or [source_ref("export_engine", "memo_assembly")],
        unavailable,
        com_payload,
    )


def _handle_scenarios(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    committee_result: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    answer, sources, unavailable, payload = _handle_committee(
        platform,
        message=message,
        symbols=symbols,
        analyse_response=analyse_response,
        committee_result=committee_result,
        research_object=research_object,
        report=report,
    )
    header = "# Bull / Base / Bear Report\nProduced from AI Committee outputs only.\n\n"
    return header + answer, sources, unavailable, payload


def _handle_buffett(
    platform: Any,
    *,
    message: str,
    symbols: list[str] | None = None,
    analyse_response: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    **kwargs: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    answer, sources, unavailable, payload = _handle_valuation(
        platform,
        message=message,
        analyse_response=analyse_response,
        research_object=research_object,
        **kwargs,
    )
    if (unavailable or payload is None) and symbols:
        answer, sources, unavailable, payload = _handle_company(
            platform,
            message=message,
            symbols=symbols,
            analyse_response=analyse_response,
            research_object=research_object,
            report=kwargs.get("report"),
        )
    return (
        _buffett_wrap(answer, unavailable=unavailable),
        [
            *sources,
            source_ref("explain_like_buffett"),
        ],
        unavailable,
        payload,
    )


def _handle_research(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    research_orchestrator: Any | None = None,
    **kwargs: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    orch = research_orchestrator or getattr(platform, "research_orchestrator", None)
    clean_sym = symbols[0] if symbols else None

    if orch is None or not clean_sym:
        return (
            f"AI research unavailable; data unavailable. {UNAVAILABLE_MESSAGE}",
            [source_ref("research_orchestrator", "unconfigured")],
            True,
            None,
        )

    from llm_adapters.orchestrator import OrchestratorStatus, UserResearchRequest

    req = UserResearchRequest(
        symbol=clean_sym,
        question=message,
    )
    try:
        res = orch.run(req)
    except Exception:
        return (
            f"AI research unavailable; data unavailable. {UNAVAILABLE_MESSAGE}",
            [source_ref("research_orchestrator", "failed_closed")],
            True,
            None,
        )

    if res.status != OrchestratorStatus.ACCEPTED or res.public is None:
        return (
            f"AI research unavailable; data unavailable. {UNAVAILABLE_MESSAGE}",
            [source_ref("research_orchestrator", "failed_closed")],
            True,
            None,
        )

    pub = res.public

    # Reconcile against DSP deterministic outputs (DSP always authoritative)
    valuation_map = _from_mapping(analyse_response, "valuation") or {}
    summary_map = _from_mapping(analyse_response, "recommendation_summary") or {}

    dsp_decision = _fmt(
        _from_mapping(summary_map, "label")
        or _from_mapping(summary_map, "decision")
        or _from_mapping(summary_map, "recommendation")
    )
    dsp_mos = _fmt(
        _from_mapping(summary_map, "margin_of_safety")
        or _from_mapping(valuation_map, "margin_of_safety")
    )
    dsp_iv = _fmt(
        _from_mapping(valuation_map, "intrinsic_value")
        or _from_mapping(summary_map, "intrinsic_value")
    )

    rec = dsp_decision if dsp_decision else pub.recommendation
    val = dsp_iv if dsp_iv else pub.valuation
    mos = dsp_mos if dsp_mos else None

    analysis_text = (pub.analysis or "Analysis complete.").strip()
    if dsp_decision and pub.recommendation and pub.recommendation != dsp_decision:
        analysis_text = analysis_text.replace(pub.recommendation, dsp_decision)
    if dsp_iv and pub.valuation and pub.valuation != dsp_iv:
        analysis_text = analysis_text.replace(pub.valuation, dsp_iv)

    lines = [
        f"## AI Research Analysis for {clean_sym}",
        analysis_text,
        "",
        f"**Authoritative Recommendation:** {rec}",
    ]
    if val:
        lines.append(f"**Valuation:** {val}")
    if mos:
        lines.append(f"**Margin of Safety:** {mos}")
    if pub.risks:
        lines.extend(["", "### Key Risks"])
        for r in pub.risks:
            lines.append(f"- {r}")
    if pub.limitations:
        lines.extend(["", "### Limitations"])
        for lim in pub.limitations:
            lines.append(f"- {lim}")

    sources = [
        source_ref("research_orchestrator", "dual_verification"),
    ]
    if pub.evidence_citations:
        for cite in pub.evidence_citations:
            sources.append(source_ref("dsp_evidence", str(cite)))

    payload = {
        "research_summary": {
            "recommendation": rec,
            "valuation": val,
            "margin_of_safety": mos,
            "confidence": pub.confidence,
            "evidence_citations": list(pub.evidence_citations),
        }
    }
    return "\n".join(lines), sources, False, payload


def _handle_chat(
    platform: Any,
    *,
    message: str,
    symbols: list[str],
    analyse_response: Mapping[str, Any] | None,
    research_object: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    **kwargs: Any,
) -> tuple[str, list[dict[str, Any]], bool, dict[str, Any] | None]:
    # Prefer extractive research copilot when artifacts exist
    if research_object is not None or report is not None:
        try:
            grounded = platform.ask_research_copilot(
                message,
                research_object=dict(research_object) if research_object else None,
                report=dict(report) if report else None,
            )
            answer = str(grounded.get("answer") or UNAVAILABLE_MESSAGE)
            return (
                answer,
                [source_ref("research_copilot", "ask_research_copilot")],
                bool(grounded.get("unavailable")) or answer == UNAVAILABLE_MESSAGE,
                {"research_copilot": grounded},
            )
        except Exception:  # noqa: BLE001
            pass
    if analyse_response is not None:
        return _handle_company(
            platform,
            message=message,
            symbols=symbols,
            analyse_response=analyse_response,
            research_object=research_object,
            report=report,
        )
    if symbols:
        return _handle_company(
            platform,
            message=message,
            symbols=symbols,
            analyse_response=None,
            research_object=None,
            report=None,
        )
    del kwargs
    return (
        "Ask about a company, valuation, committee, risk, portfolio, comparison, or document. "
        f"Without engine context: {UNAVAILABLE_MESSAGE}",
        [source_ref("copilot_v2")],
        True,
        None,
    )


def _buffett_wrap(answer: str, *, unavailable: bool) -> str:
    if unavailable or answer.strip() == UNAVAILABLE_MESSAGE:
        return (
            "Plain-language view: there is not enough authenticated research output "
            f"to explain this like Buffett yet. {UNAVAILABLE_MESSAGE}"
        )
    return (
        "Plain-language (Buffett-style) explanation of existing platform outputs — "
        "no new numbers:\n\n"
        f"{answer}\n\n"
        "Rule: never invent intrinsic value, margins, or scores. "
        "If a figure is missing above, treat it as unavailable."
    )


def _suggested_for(intent: str, symbols: list[str]) -> list[dict[str, str]]:
    sym = symbols[0] if symbols else "the company"
    base = [
        {"id": "explain_valuation", "label": f"Explain valuation for {sym}"},
        {"id": "explain_committee", "label": "Explain AI Committee cases"},
        {"id": "summarise_risks", "label": f"What are the biggest risks in {sym}?"},
        {"id": "compare_companies", "label": "Compare with a peer"},
        {"id": "investment_memo", "label": "Generate an investment memo"},
        {"id": "buffett", "label": "Explain like Buffett"},
    ]
    if intent == "portfolio":
        base.insert(
            0,
            {"id": "portfolio_concentration", "label": "Where is concentration risk?"},
        )
    if intent == "document":
        base.insert(0, {"id": "filings", "label": f"Summarize filings for {sym}"})
    return base
