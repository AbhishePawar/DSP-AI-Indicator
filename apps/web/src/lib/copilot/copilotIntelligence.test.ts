import { describe, expect, it } from "vitest";

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { composeAnswer } from "@/lib/copilot/answerComposer";
import { compareCompanyContexts } from "@/lib/copilot/comparison";
import {
  appendExchange,
  createConversation,
} from "@/lib/copilot/conversation";
import { buildCopilotContext } from "@/lib/copilot/contextBuilder";
import {
  intentFromSuggestedId,
  resolveIntent,
} from "@/lib/copilot/intentResolver";
import { composeCopilotAnswer } from "@/lib/copilot/placeholderAnswers";
import { UNAVAILABLE_ANSWER } from "@/lib/copilot/questions";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

function makeResponse(overrides?: {
  decision?: string;
  mos?: number;
  stages?: AnalyseResponse["payload"]["stage_summaries"];
}): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    payload: {
      ok: true,
      metadata: {
        pipeline_version: "1.0.0-epic-001",
        total_elapsed_ms: 12.5,
        evidence_counts: {},
        confidence_summary: {},
        warnings: [],
        package_versions: {},
        execution_order: [],
        failed_stage: null,
      },
      stage_summaries: overrides?.stages ?? [
        {
          stage: "economic_moat",
          status: "succeeded",
          has_result: true,
          label: "Wide",
          score: 0.8,
          confidence: 0.7,
        },
        {
          stage: "management_quality",
          status: "succeeded",
          has_result: true,
          label: "Strong",
          score: 0.75,
        },
        {
          stage: "financial_strength",
          status: "succeeded",
          has_result: true,
          label: "Solid",
        },
        {
          stage: "earnings_quality",
          status: "succeeded",
          has_result: true,
          label: "High",
        },
        {
          stage: "growth_quality",
          status: "succeeded",
          has_result: true,
          label: "Steady",
        },
        {
          stage: "business_quality_aggregator",
          status: "succeeded",
          has_result: true,
          label: "Strong",
          score: 0.72,
        },
      ],
      recommendation_summary: {
        decision: overrides?.decision ?? "Buy",
        confidence: 0.66,
        margin_of_safety: overrides?.mos ?? 0.3,
      },
      committee_summary: {
        decision: "Approve",
        confidence: 0.7,
        consensus: "majority",
        rationale: "Risk officer dissent noted",
      },
      errors: [],
      limitations: [],
    },
    limitations: [],
    errors: [],
    api_version: "v1",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0-epic-001",
    correlation_id: "test-1",
  };
}

describe("intentResolver", () => {
  it("maps suggested ids to intents", () => {
    expect(intentFromSuggestedId("why_buy")).toBe("explain_recommendation");
    expect(intentFromSuggestedId("compare_companies")).toBe("compare_companies");
  });

  it("resolves freeform valuation and moat questions", () => {
    expect(resolveIntent("Explain the valuation.")).toBe("explain_valuation");
    expect(resolveIntent("What is the economic moat?")).toBe("explain_moat");
    expect(resolveIntent("Why is this company recommended?")).toBe(
      "explain_recommendation",
    );
  });

  it("reuses lastIntent for follow-ups", () => {
    expect(
      resolveIntent("tell me more", { lastIntent: "explain_moat" }),
    ).toBe("explain_moat");
  });
});

describe("contextBuilder", () => {
  it("builds deterministic context from request + response", () => {
    const ctx = buildCopilotContext(SAMPLE_ANALYSE_REQUEST, makeResponse());
    expect(ctx?.ticker).toBe("ACM");
    expect(ctx?.recommendation).toBe("Buy");
    expect(ctx?.marginOfSafety).toBe(0.3);
    expect(ctx?.intrinsicValue).toBe(100);
    expect(ctx?.economicMoat.available).toBe(true);
    expect(ctx?.economicMoat.label).toBe("Wide");
  });

  it("returns null without response", () => {
    expect(buildCopilotContext(SAMPLE_ANALYSE_REQUEST, null)).toBeNull();
  });
});

describe("answerComposer", () => {
  it("explains recommendation with citations", () => {
    const primary = buildCopilotContext(SAMPLE_ANALYSE_REQUEST, makeResponse());
    const answer = composeAnswer("explain_recommendation", primary);
    expect(answer.unavailable).toBe(false);
    expect(answer.content).toContain("Buy");
    expect(answer.citations).toContain("Recommendation");
  });

  it("returns unavailable for missing stage fields", () => {
    const primary = buildCopilotContext(
      SAMPLE_ANALYSE_REQUEST,
      makeResponse({ stages: [] }),
    );
    const answer = composeAnswer("explain_moat", primary);
    expect(answer.content).toBe(UNAVAILABLE_ANSWER);
    expect(answer.unavailable).toBe(true);
  });
});

describe("comparison", () => {
  it("compares overlapping present fields only", () => {
    const a = buildCopilotContext(SAMPLE_ANALYSE_REQUEST, makeResponse());
    const bRequest: AnalyseRequest = {
      ...SAMPLE_ANALYSE_REQUEST,
      ticker: "BETA",
      company: "Beta Corp",
      valuation_signals: {
        ...SAMPLE_ANALYSE_REQUEST.valuation_signals!,
        intrinsic_value_per_share: 80,
      },
    };
    const b = buildCopilotContext(
      bRequest,
      makeResponse({ decision: "Hold", mos: 0.1 }),
    );
    const result = compareCompanyContexts(a, b);
    expect(result.unavailable).toBe(false);
    expect(result.content).toContain("ACM");
    expect(result.content).toContain("BETA");
    expect(result.content).toContain("Buy vs Hold");
  });

  it("explains when secondary is missing", () => {
    const a = buildCopilotContext(SAMPLE_ANALYSE_REQUEST, makeResponse());
    const result = compareCompanyContexts(a, null);
    expect(result.unavailable).toBe(true);
    expect(result.content).toContain(UNAVAILABLE_ANSWER);
  });
});

describe("conversation context", () => {
  it("stores lastIntent across exchanges", () => {
    let conversation = createConversation("Test");
    conversation = appendExchange(conversation, "Explain the moat", "Wide moat", {
      intent: "explain_moat",
      ticker: "ACM",
      citations: ["Economic Moat"],
    });
    expect(conversation.context.lastIntent).toBe("explain_moat");
    expect(conversation.context.lastTicker).toBe("ACM");
    expect(conversation.messages.at(-1)?.citations).toEqual(["Economic Moat"]);
  });
});

describe("composeCopilotAnswer integration", () => {
  it("routes freeform through intent + composer", () => {
    const answer = composeCopilotAnswer("freeform", {
      request: SAMPLE_ANALYSE_REQUEST,
      response: makeResponse(),
      freeform: "Explain the margin of safety.",
    });
    expect(answer.intent).toBe("explain_margin_of_safety");
    expect(answer.content).toContain("30.0%");
    expect(answer.citations).toContain("Valuation");
  });
});
