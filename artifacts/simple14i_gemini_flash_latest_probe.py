"""SIMPLE-14I generateContent probe for a non-SIMPLE-11 Gemini model.

Never calls gemini-2.5-flash / pro / lite. Never prints the API key.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime

from data_engine.multi_agent_research.contracts import ResearchRequest
from data_engine.security_identity import set_security_master_for_tests
from llm_adapters.gemini import (
    SIMPLE11_BLOCKED_GEMINI_MODELS,
    GeminiLiveResearchAgent,
)
from llm_adapters.research import qualification_security_master

MODEL = os.environ.get("DSP_AI_GEMINI_RESEARCH_MODEL") or "gemini-flash-latest"


def main() -> int:
    if MODEL in SIMPLE11_BLOCKED_GEMINI_MODELS:
        print("refusing SIMPLE-11 blocked model", MODEL)
        return 2
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    print("configured", bool(key), "model", MODEL)
    if not key:
        print("NOT_CONFIGURED")
        return 2
    master = qualification_security_master()
    set_security_master_for_tests(master)
    identity = master.resolve(ticker="INFY", exchange="NSE")
    print(
        "identity",
        identity.status.value,
        identity.ticker,
        identity.isin,
        identity.mic,
        identity.exchange,
    )
    request = ResearchRequest.from_identity(
        identity,
        requested_fields=("listing_status",),
        requested_as_of=datetime.now(tz=UTC).date().isoformat(),
        research_purpose="simple14i-primary-source",
        created_at=datetime.now(tz=UTC),
    )
    agent = GeminiLiveResearchAgent(
        api_key=key, model=MODEL, enable_google_search=True
    )
    result = agent.research(request)
    print("search_failure", result.failure.value)
    print("search_detail", result.detail)
    print("search_claim_count", len(result.claims))
    if result.failure.value != "NONE":
        plain = GeminiLiveResearchAgent(
            api_key=key, model=MODEL, enable_google_search=False
        )
        plain_result = plain.research(request)
        print("plain_failure", plain_result.failure.value)
        print("plain_detail", plain_result.detail)
        print("plain_claim_count", len(plain_result.claims))
    print("failure", result.failure.value)
    print("capability", result.capability_state.value)
    print("detail", result.detail)
    print("claim_count", len(result.claims))
    for claim in result.claims:
        print(
            json.dumps(
                {
                    "field": claim.field,
                    "value": claim.candidate_value,
                    "source": claim.source,
                    "source_url_host": claim.source_url.split("/")[2]
                    if "://" in claim.source_url
                    else "",
                    "has_url": bool(claim.source_url),
                    "has_locator": bool(claim.evidence_locator),
                    "has_document_date": bool(claim.document_date),
                    "agent": claim.agent,
                }
            )
        )
    set_security_master_for_tests(None)
    return 0 if result.failure.value in {"NONE", "EVIDENCE_INSUFFICIENT"} else 1


if __name__ == "__main__":
    sys.exit(main())
