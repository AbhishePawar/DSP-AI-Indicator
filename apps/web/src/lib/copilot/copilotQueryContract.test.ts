import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "@/lib/api/client";

describe("Copilot Query Contract Suite — api.copilotQuery() -> /api/v1/copilot/complete", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("Contract: calls /copilot/complete and NEVER calls /copilot/query", async () => {
    const mockCompleteResponse = {
      content: "AAPL shows competitive advantages and high return on capital.",
      citations: ["10-K FY2025", "DSP Moat Framework"],
      intent: "research_query",
      unavailable: false,
      provider_id: "deterministic",
      limitations: [],
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify(mockCompleteResponse),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.copilotQuery({
      query: "Explain the moat score",
      symbol: "AAPL",
      analysis_id: "ana-9982",
      section_context: "Economic Moat",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [calledUrl, calledOptions] = fetchMock.mock.calls[0];

    // Assert actual route is /copilot/complete and NOT /copilot/query
    expect(calledUrl).toContain("/copilot/complete");
    expect(calledUrl).not.toContain("/copilot/query");
    expect(calledOptions.method).toBe("POST");

    const payload = JSON.parse(calledOptions.body);
    // Verified fields matching CopilotCompleteRequest schema
    expect(payload.question_id).toBe("freeform");
    expect(payload.freeform).toBe("Explain the moat score");
    expect(payload.market_context).toEqual({
      symbol: "AAPL",
      analysis_id: "ana-9982",
      section_context: "Economic Moat",
      query: "Explain the moat score",
    });

    // Frontend mapping
    expect(result.content).toBe(mockCompleteResponse.content);
    expect(result.citations).toEqual(mockCompleteResponse.citations);
    expect(result.provider_id).toBe("deterministic");
  });

  it("Dynamic Context Contract: section S09 valuation and S03 buffett context", async () => {
    const fetchMock = vi.fn().mockImplementation(async (_url, options) => {
      const body = JSON.parse(options.body);
      return {
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            content: `Analysis for ${body.market_context.section_context} on ${body.market_context.symbol}`,
            citations: [],
            intent: "research_query",
            unavailable: false,
            provider_id: "deterministic",
            limitations: [],
          }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    // Call 1: Section S09 Valuation
    const s09Result = await api.copilotQuery({
      query: "What is the intrinsic value range?",
      symbol: "NVDA",
      analysis_id: "analysis-nvda-1",
      section_context: "S09 Valuation Model",
      prompt: "Context: S09 Valuation Model for NVDA. What is the intrinsic value range?",
    });

    const call1Body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(call1Body.freeform).toContain("S09 Valuation Model");
    expect(call1Body.market_context.section_context).toBe("S09 Valuation Model");
    expect(call1Body.market_context.symbol).toBe("NVDA");
    expect(s09Result.content).toContain("S09 Valuation Model on NVDA");

    // Call 2: Section S03 Buffett Assessment
    const s03Result = await api.copilotQuery({
      query: "How did it score on debt-to-equity and moat?",
      symbol: "NVDA",
      analysis_id: "analysis-nvda-1",
      section_context: "S03 Buffett Assessment",
      prompt: "Context: S03 Buffett Assessment for NVDA. How did it score on debt-to-equity and moat?",
    });

    const call2Body = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(call2Body.freeform).toContain("S03 Buffett Assessment");
    expect(call2Body.market_context.section_context).toBe("S03 Buffett Assessment");
    expect(call2Body.market_context.symbol).toBe("NVDA");
    expect(s03Result.content).toContain("S03 Buffett Assessment on NVDA");
  });

  it("Error Contract: surfaces backend 503 error cleanly", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        text: async () => JSON.stringify({ detail: "Copilot service is not configured" }),
      })
    );

    await expect(
      api.copilotQuery({
        query: "What is the margin trend?",
        symbol: "TCS",
      })
    ).rejects.toThrow();
  });
});
