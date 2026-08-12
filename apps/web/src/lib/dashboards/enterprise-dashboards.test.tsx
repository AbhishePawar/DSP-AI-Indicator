/**
 * @vitest-environment jsdom
 */
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { RoleDashboard } from "@/components/dashboards";
import {
  ENTERPRISE_DASHBOARD_ROLES,
  isEnterpriseDashboardRole,
  metaForRole,
} from "@/lib/dashboards/roleRegistry";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboards/research",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ role: "research" }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "tok" },
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const enterpriseDashboard = vi.fn(async () => ({
  ok: true,
  result: {
    role: "research",
    generated_at: "2026-08-06T12:00:00+00:00",
    widgets: {
      research_coverage: {
        available: true,
        source: "research_engine",
        data: { note: "ok" },
        message: null,
      },
      companies_under_review: {
        available: false,
        source: "institutional_workflow",
        data: null,
        message: "Data unavailable.",
      },
      pending_research: {
        available: false,
        source: "institutional_workflow",
        data: null,
        message: "Data unavailable.",
      },
      recent_reports: {
        available: false,
        source: "admin_research_archive_metadata",
        data: null,
        message: "Data unavailable.",
      },
      research_score: {
        available: true,
        source: "research_intelligence",
        data: { score: "Data unavailable." },
        message: null,
      },
      ai_committee_summary: {
        available: true,
        source: "institutional_committee",
        data: { agents: [] },
        message: null,
      },
      watchlist: {
        available: false,
        source: "research_monitoring_watchlist",
        data: null,
        message: "Data unavailable.",
      },
      recent_news: {
        available: false,
        source: "data_connector_news",
        data: null,
        message: "Data unavailable.",
      },
    },
  },
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    enterpriseDashboard: (...args: unknown[]) => enterpriseDashboard(...args),
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

describe("enterprise dashboards registry", () => {
  it("exposes five role dashboards", () => {
    expect(ENTERPRISE_DASHBOARD_ROLES).toHaveLength(5);
    expect(isEnterpriseDashboardRole("research")).toBe(true);
    expect(isEnterpriseDashboardRole("trader")).toBe(false);
    expect(metaForRole("executive")?.title).toMatch(/Executive/);
  });
});

describe("RoleDashboard", () => {
  beforeEach(() => {
    cleanup();
    enterpriseDashboard.mockClear();
  });

  it("lazy-loads research widgets from GET /dashboards/research", async () => {
    renderWithClient(<RoleDashboard role="research" symbols="AAPL" />);
    expect(screen.getByTestId("role-dashboard-research")).toBeTruthy();
    await waitFor(() => {
      expect(enterpriseDashboard).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText(/Research Analyst Dashboard/i)).toBeTruthy();
    });
    expect(screen.getAllByText(/Data unavailable\./i).length).toBeGreaterThan(0);
    expect(screen.getByTestId("role-dashboard-research")).toBeTruthy();
  });
});
