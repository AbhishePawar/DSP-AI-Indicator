import { describe, expect, it } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import {
  AIService,
  buildAIRequest,
  createAIService,
  createDefaultRegistry,
  createMockProvider,
  ProviderRegistry,
} from "@/lib/ai";
import { composeCopilotAnswer } from "@/lib/copilot/placeholderAnswers";
import { UNAVAILABLE_ANSWER } from "@/lib/copilot/questions";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

function sampleResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    api_version: "0.2.0",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0",
    correlation_id: "ai-test",
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
      stage_summaries: [],
      metadata: {
        warnings: [],
        evidence_counts: {},
        confidence_summary: {},
      },
    },
  };
}

describe("AI provider registry", () => {
  it("registers mock and deterministic providers", () => {
    const registry = createDefaultRegistry();
    expect(registry.list().map((p) => p.id)).toEqual([
      "deterministic",
      "mock",
      "backend",
    ]);
    expect(registry.get("deterministic")?.getCapabilities()).toContain("chat");
    expect(registry.get("mock")?.getCapabilities()).toContain("streaming");
  });
});

describe("AIService", () => {
  it("defaults to deterministic provider", () => {
    const service = createAIService();
    expect(service.getActiveProviderId()).toBe("deterministic");
    expect(service.supportsCapability("compare")).toBe(true);
    expect(service.supportsCapability("vision")).toBe(false);
  });

  it("swaps providers at runtime", async () => {
    const service = createAIService();
    const request = buildAIRequest({
      questionId: "why_buy",
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
    });

    const deterministic = await service.complete(request);
    expect(deterministic.providerId).toBe("deterministic");
    expect(deterministic.content).toContain("Buy");

    service.setActiveProvider("mock");
    const mock = await service.complete(request);
    expect(mock.providerId).toBe("mock");
    expect(mock.content).toContain("[mock:mock]");
  });

  it("returns placeholder stream for deterministic provider", async () => {
    const service = createAIService();
    const request = buildAIRequest({
      questionId: "why_buy",
      request: null,
      response: null,
    });
    const stream = await service.stream(request);
    expect(stream.final?.unavailable).toBe(true);
    expect(stream.chunks.length).toBeGreaterThan(0);
  });
});

describe("DeterministicProvider", () => {
  it("matches legacy composeCopilotAnswer output", async () => {
    const service = createAIService(
      createDefaultRegistry(),
      { activeProviderId: "deterministic" },
    );
    const options = {
      questionId: "why_buy" as const,
      request: SAMPLE_ANALYSE_REQUEST,
      response: sampleResponse(),
    };
    const legacy = composeCopilotAnswer(options.questionId, {
      request: options.request,
      response: options.response,
    });
    const viaProvider = await service.complete(buildAIRequest(options));

    expect(viaProvider.content).toBe(legacy.content);
    expect(viaProvider.citations).toEqual(legacy.citations);
    expect(viaProvider.intent).toBe(legacy.intent);
    expect(viaProvider.unavailable).toBe(legacy.unavailable);
  });

  it("returns unavailable without session", async () => {
    const service = createAIService();
    const response = await service.complete(
      buildAIRequest({
        questionId: "why_buy",
        request: null,
        response: null,
      }),
    );
    expect(response.content).toContain(UNAVAILABLE_ANSWER);
    expect(response.unavailable).toBe(true);
  });
});

describe("MockProvider", () => {
  it("returns simulated responses", async () => {
    const registry = new ProviderRegistry();
    registry.register(createMockProvider());
    const service = new AIService(registry, { activeProviderId: "mock" });
    const response = await service.complete(
      buildAIRequest({
        questionId: "freeform",
        freeform: "hello",
        request: SAMPLE_ANALYSE_REQUEST,
        response: sampleResponse(),
      }),
    );
    expect(response.metadata?.simulated).toBe(true);
    expect(response.content).toContain("ACM");
  });

  it("exposes streaming placeholder chunks", async () => {
    const registry = new ProviderRegistry();
    const mock = createMockProvider();
    registry.register(mock);
    const service = new AIService(registry, { activeProviderId: "mock" });
    const stream = await service.stream(
      buildAIRequest({
        questionId: "explain_moat",
        request: SAMPLE_ANALYSE_REQUEST,
        response: sampleResponse(),
      }),
    );
    expect(stream.chunks.length).toBeGreaterThan(1);
    expect(stream.final?.providerId).toBe("mock");
  });
});

describe("capability discovery", () => {
  it("lists provider capabilities", () => {
    const service = createAIService();
    const providers = service.listProviders();
    expect(providers).toHaveLength(3);
    expect(
      providers.find((p) => p.id === "deterministic")?.capabilities,
    ).toEqual(["chat", "compare"]);
    expect(
      providers.find((p) => p.id === "mock")?.capabilities,
    ).toContain("streaming");
  });
});
