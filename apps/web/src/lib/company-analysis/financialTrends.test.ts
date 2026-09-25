import { describe, expect, it } from "vitest";

import type { FinancialStatementsPayload } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { formatTrendValue, mapFinancialTrends } from "@/lib/company-analysis";

function period(
  fy: number,
  values: {
    revenue?: number | null;
    net_income?: number | null;
    fcf?: number | null;
    net_margin?: number | null;
  },
  period_type = "annual",
): NonNullable<FinancialStatementsPayload["periods"]>[number] {
  return {
    period_type,
    fiscal_year: fy,
    period_end: `${fy}-03-31`,
    income_statement: { revenue: values.revenue, net_income: values.net_income },
    cash_flow: { free_cash_flow: values.fcf },
    ratios: { net_margin: values.net_margin },
  };
}

// Synthetic test fixture only — never production data.
function payload(
  periods: FinancialStatementsPayload["periods"],
  extra: Partial<FinancialStatementsPayload> = {},
): FinancialStatementsPayload {
  return {
    ok: true,
    available: true,
    authenticated: true,
    reporting_currency: "INR",
    provenance: { provider_id: "provider-x", provider_name: "Provider X" },
    periods,
    ...extra,
  };
}

describe("mapFinancialTrends (Figma five-year charts over /fundamentals/statements)", () => {
  it("orders annual periods oldest → newest, caps at five, copies line items verbatim", () => {
    const view = mapFinancialTrends(
      payload([
        period(2025, { revenue: 600, net_income: 60, fcf: 50, net_margin: 0.1 }),
        period(2024, { revenue: 500, net_income: 50, fcf: 40, net_margin: 0.1 }),
        period(2023, { revenue: 400, net_income: 40, fcf: 30, net_margin: 0.1 }),
        period(2022, { revenue: 300, net_income: 30, fcf: 20, net_margin: 0.1 }),
        period(2021, { revenue: 200, net_income: 20, fcf: 10, net_margin: 0.1 }),
        period(2020, { revenue: 100, net_income: 10, fcf: 5, net_margin: 0.1 }),
      ]),
    );
    expect(view.authenticated).toBe(true);
    expect(view.periodType).toBe("annual");
    expect(view.series.revenue.points.map((p) => p.label)).toEqual([
      "FY2021",
      "FY2022",
      "FY2023",
      "FY2024",
      "FY2025",
    ]);
    expect(view.series.revenue.points.map((p) => p.value)).toEqual([200, 300, 400, 500, 600]);
    expect(view.series.net_income.points.at(-1)?.value).toBe(60);
    expect(view.series.free_cash_flow.points.at(-1)?.value).toBe(50);
    expect(view.series.net_margin.points.at(-1)?.value).toBe(0.1);
    expect(view.series.revenue.currency).toBe("INR");
    expect(view.series.net_margin.currency).toBeNull();
    expect(view.series.revenue.available).toBe(true);
    expect(view.series.revenue.source).toContain("Provider X");
    expect(view.series.revenue.source).toContain("/api/v1/fundamentals/statements");
  });

  it("does not compute net margin when the provider omits the ratio", () => {
    const view = mapFinancialTrends(
      payload([
        period(2024, { revenue: 500, net_income: 50 }),
        period(2023, { revenue: 400, net_income: 40 }),
      ]),
    );
    expect(view.series.net_margin.points.map((p) => p.value)).toEqual([null, null]);
    expect(view.series.net_margin.available).toBe(false);
    expect(view.series.revenue.available).toBe(true);
  });

  it("marks a series unavailable with fewer than two valued periods", () => {
    const view = mapFinancialTrends(payload([period(2024, { revenue: 500 })]));
    expect(view.series.revenue.available).toBe(false);
    expect(view.series.revenue.points).toHaveLength(1);
  });

  it("prefers annual periods over quarterly rows in a mixed payload", () => {
    const view = mapFinancialTrends(
      payload([
        period(2024, { revenue: 500 }),
        period(2023, { revenue: 400 }),
        { ...period(2024, { revenue: 130 }, "quarterly"), fiscal_quarter: 4, period_end: "2024-12-31" },
      ]),
    );
    expect(view.series.revenue.points.map((p) => p.value)).toEqual([400, 500]);
  });

  it("is honest for unauthenticated, unavailable, or missing payloads", () => {
    for (const p of [
      null,
      undefined,
      payload([period(2024, { revenue: 1 }), period(2023, { revenue: 2 })], { authenticated: false }),
      payload([period(2024, { revenue: 1 }), period(2023, { revenue: 2 })], { available: false }),
    ]) {
      const view = mapFinancialTrends(p);
      expect(view.authenticated).toBe(false);
      expect(view.periodType).toBeNull();
      for (const s of Object.values(view.series)) {
        expect(s.points).toEqual([]);
        expect(s.available).toBe(false);
        expect(s.authenticated).toBe(false);
        expect(s.source).toBe("Data unavailable.");
      }
    }
  });

  it("formats values without inventing precision or currency", () => {
    const view = mapFinancialTrends(
      payload([period(2024, { revenue: 2_500_000_000, net_margin: 0.2397 }), period(2023, { revenue: 1 })]),
    );
    expect(formatTrendValue(view.series.revenue, 2_500_000_000)).toBe("INR 2.5B");
    expect(formatTrendValue(view.series.revenue, 12_300)).toBe("INR 12.3K");
    expect(formatTrendValue(view.series.net_margin, 0.2397)).toBe("24%");
    expect(formatTrendValue(view.series.revenue, null)).toBe("Data unavailable.");

    const noCurrency = mapFinancialTrends(
      payload([period(2024, { revenue: 1_000 }), period(2023, { revenue: 1 })], {
        reporting_currency: null,
      }),
    );
    expect(noCurrency.series.revenue.currency).toBeNull();
    expect(formatTrendValue(noCurrency.series.revenue, 1_000)).toBe("1K");
  });
});
