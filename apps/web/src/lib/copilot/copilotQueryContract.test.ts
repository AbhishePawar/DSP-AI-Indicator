import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "@/lib/api/client";

describe("Copilot Query Contract Suite — /api/v1/copilot/query", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("Success Contract: attaches symbol, analysis_id, section_context and processes reply", async () => {
    const mockResponse = {
      content: "AAPL maintains significant competitive advantages with strong ROCE.",
      citations: ["10-K FY2025", "DSP Moat Model"],
      intent: "research_query",
      unavailable: false,
      provider_id: "deterministic",
      limitations: [],
      symbol: "AAPL",
      analysis_id: "ana-9982",
      section_context: "Economic Moat",
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
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
    expect(calledUrl).toContain("/copilot/query");
    expect(calledOptions.method).toBe("POST");

    const payload = JSON.parse(calledOptions.body);
    expect(payload.query).toBe("Explain the moat score");
    expect(payload.symbol).toBe("AAPL");
    expect(payload.analysis_id).toBe("ana-9982");
    expect(payload.section_context).toBe("Economic Moat");

    expect(result.content).toBe(mockResponse.content);
    expect(result.provider_id).toBe("deterministic");
  });

  it("Error Contract: handles 503 backend failure safely", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ ok: false, error: "Copilot service is not configured" }),
      })
    );

    await expect(
      api.copilotQuery({
        query: "Explain margin trend",
        symbol: "TCS",
      })
    ).rejects.toThrow();
  });

  it("Context Contract: Preserves prompt and section_context when user provides freeform text", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        content: "Detailed breakdown.",
        citations: [],
        intent: "research_query",
        unavailable: false,
        provider_id: "deterministic",
        limitations: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.copilotQuery({
      query: "Management integrity",
      prompt: "Context: Management Evaluation for INFY",
      symbol: "INFY",
      analysis_id: "id-445",
      section_context: "Management Evaluation",
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.symbol).toBe("INFY");
    expect(body.section_context).toBe("Management Evaluation");
    expect(body.analysis_id).toBe("id-445");
  });
});
