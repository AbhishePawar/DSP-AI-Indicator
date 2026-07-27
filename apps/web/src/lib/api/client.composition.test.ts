import { afterEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

vi.stubGlobal("fetch", fetchMock);

describe("api composition client", () => {
  afterEach(() => {
    fetchMock.mockReset();
  });

  it("calls /analyse and returns typed envelope", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () =>
        JSON.stringify({
          ok: true,
          capability: "compose_intelligence",
          payload: { ok: true, stage_summaries: [] },
          limitations: [],
          errors: [],
          api_version: "v1",
          platform_version: "0.7.1",
          pipeline_version: "1.0.0-epic-001",
          correlation_id: "c1",
        }),
    });

    const { api } = await import("@/lib/api/client");
    const result = await api.analyse({
      ticker: "ACM",
      financial_statements: {
        period: { period_type: "annual", period_end: "2024-12-31" },
        income_statement: { revenue: 1 },
      },
      valuation_signals: {
        intrinsic_value_per_share: 100,
        current_market_price: 70,
      },
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/analyse");
    expect(init.method).toBe("POST");
    expect(result.ok).toBe(true);
    expect(result.pipeline_version).toBe("1.0.0-epic-001");
  });

  it("maps network failures to ApiClientError", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const { api } = await import("@/lib/api/client");
    const { ApiClientError } = await import("@/lib/api/types");
    await expect(api.health()).rejects.toBeInstanceOf(ApiClientError);
  });

  it("calls validate, version, and capabilities paths", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ ok: true, valid: true, errors: [], warnings: [], api_version: "v1" }),
    });
    const { api } = await import("@/lib/api/client");
    await api.validateAnalyse({
      ticker: "ACM",
      financial_statements: {
        period: { period_type: "annual", period_end: "2024-12-31" },
      },
    });
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("/validate");

    fetchMock.mockResolvedValue({
      ok: true,
      text: async () =>
        JSON.stringify({
          api_version: "v1",
          api_package_version: "0.2.0",
          platform_version: "0.7.1",
          pipeline_version: "1.0.0-epic-001",
          docs_version: "1.3.32",
          package_versions: {},
        }),
    });
    await api.version();
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("/version");

    fetchMock.mockResolvedValue({
      ok: true,
      text: async () =>
        JSON.stringify({
          analytical_modules: [],
          supported_reports: [],
          pipeline_stages: ["financial"],
          pipeline_version: "1.0.0-epic-001",
          platform_version: "0.7.1",
          api_version: "v1",
          package_versions: {},
          platform_capabilities: [],
        }),
    });
    await api.capabilities();
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("/capabilities");
  });
});
