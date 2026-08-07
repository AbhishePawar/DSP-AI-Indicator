/**
 * @vitest-environment jsdom
 */
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SaasPlatform } from "@/components/saas-platform";

vi.mock("next/navigation", () => ({
  usePathname: () => "/saas",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "tok" },
    user: { id: "admin-1" },
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const saasDashboard = vi.fn(async () => ({
  ok: true,
  result: {
    subscription_overview: {
      organizations: 0,
      subscriptions_tracked: 0,
      licenses_active: 0,
    },
    revenue: {
      available: false,
      message: "Data unavailable.",
      mrr: null,
      note: "No fabricated KPIs.",
    },
    plan_distribution: {
      starter: 0,
      professional: 0,
      enterprise: 0,
      custom: 0,
    },
    most_active_organizations: [],
    growth_metrics: {
      research: 0,
      exports: 0,
      api_usage: 0,
      note: "Observed counters only",
    },
    storage_usage: { storage_bytes: 0 },
  },
}));

const saasListOrganizations = vi.fn(async () => ({
  ok: true,
  result: { organizations: [] },
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    saasDashboard: (...args: unknown[]) => saasDashboard(...args),
    saasListOrganizations: (...args: unknown[]) =>
      saasListOrganizations(...args),
    saasPlans: vi.fn(async () => ({ ok: true, result: { plans: [] } })),
  },
}));

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("SaasPlatform", () => {
  beforeEach(() => {
    cleanup();
    saasDashboard.mockClear();
    saasListOrganizations.mockClear();
  });

  it("renders SaaS shell and loads admin dashboard", async () => {
    renderWithClient(<SaasPlatform />);
    expect(screen.getByTestId("saas-platform")).toBeTruthy();
    await waitFor(() => {
      expect(saasDashboard).toHaveBeenCalled();
      expect(saasListOrganizations).toHaveBeenCalled();
    });
    expect(screen.getByTestId("saas-platform").textContent).toMatch(
      /Commercial SaaS Platform/i,
    );
    await waitFor(() => {
      expect(screen.getByTestId("saas-admin-dashboard")).toBeTruthy();
    });
    expect(
      screen.getByTestId("saas-admin-dashboard").textContent,
    ).toMatch(/Data unavailable/i);
  });
});
