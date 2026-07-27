import { describe, expect, it } from "vitest";

import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { appendExchange, createConversation } from "@/lib/copilot/conversation";
import { SUGGESTED_QUESTIONS, UNAVAILABLE_ANSWER } from "@/lib/copilot/questions";
import { buildPlaceholderAnswer } from "@/lib/copilot/placeholderAnswers";
import { breadcrumbsFor, getPrimaryNav } from "@/lib/navigation";

function sampleResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    api_version: "0.2.0",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0",
    correlation_id: "copilot-test",
    limitations: [],
    errors: [],
    payload: {
      ok: true,
      recommendation_summary: {
        decision: "Buy",
        confidence: 0.8,
        margin_of_safety: 0.25,
      },
      committee_summary: {
        decision: "Approve",
        confidence: 0.7,
        consensus: "majority",
        rationale: "Quality franchise",
      },
      stage_summaries: [
        {
          stage: "economic_moat",
          status: "succeeded",
          has_result: true,
          label: "Wide",
          decision: "Durable",
          score: 0.8,
        },
        {
          stage: "valuation",
          status: "succeeded",
          has_result: true,
          label: "DCF",
          confidence: 0.7,
        },
      ],
      metadata: {
        warnings: [],
        evidence_counts: {},
        confidence_summary: {},
      },
    },
  };
}

describe("copilot placeholder answers", () => {
  it("returns unavailable without a research session", () => {
    const answer = buildPlaceholderAnswer("why_buy", {
      request: null,
      response: null,
    });
    expect(answer).toContain(UNAVAILABLE_ANSWER);
  });

  it("explains recommendation from API fields only", () => {
    const answer = buildPlaceholderAnswer("why_buy", {
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
    });
    expect(answer).toContain("Buy");
    expect(answer).toContain("Margin of safety");
    expect(answer).not.toContain("OpenAI");
  });

  it("returns unavailable for compare companies", () => {
    const answer = buildPlaceholderAnswer("compare_companies", {
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
    });
    expect(answer).toContain(UNAVAILABLE_ANSWER);
    expect(answer).toContain("two analysed companies");
  });

  it("summarises strengths when present", () => {
    const response = sampleResponse();
    response.payload.stage_summaries = [
      ...(response.payload.stage_summaries ?? []),
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
        label: "Solid balance sheet",
      },
    ];
    const answer = buildPlaceholderAnswer("summarise_strengths", {
      request: SAMPLE_ANALYSE_REQUEST,
      response,
    });
    expect(answer).toContain("Solid balance sheet");
  });
});

describe("copilot conversation helpers", () => {
  it("appends user and assistant messages", () => {
    const base = createConversation("Test");
    const next = appendExchange(base, "Explain the moat.", "Moat summary");
    expect(next.messages.filter((m) => m.role === "user")).toHaveLength(1);
    expect(next.messages.at(-1)?.content).toBe("Moat summary");
    expect(next.title).toBe("Explain the moat.");
  });
});

describe("copilot navigation", () => {
  it("includes Copilot in primary nav", () => {
    expect(getPrimaryNav().some((n) => n.href === "/copilot")).toBe(true);
  });

  it("builds breadcrumbs for /copilot", () => {
    expect(breadcrumbsFor("/copilot").map((c) => c.label)).toEqual([
      "Home",
      "Copilot",
    ]);
  });

  it("exposes the expected suggested questions", () => {
    expect(SUGGESTED_QUESTIONS.length).toBeGreaterThanOrEqual(7);
  });
});
