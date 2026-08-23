/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
      refreshToken: null,
      tokenType: "Bearer",
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: ["read_research"],
      subject: "u1",
      username: "analyst",
      displayName: "Ada Analyst",
      email: "ada@example.com",
      authMethod: "rbac",
      sessionId: "s1",
      issuedAt: "2026-07-28T10:00:00.000Z",
      expiresAt: null,
      rememberMe: false,
    },
    user: {
      subject: "u1",
      username: "analyst",
      displayName: "Ada Analyst",
      email: "ada@example.com",
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: ["read_research"],
    },
    login: vi.fn(),
    logout: vi.fn(),
    refreshSession: vi.fn(),
    loadProfile: vi.fn(),
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    health: vi.fn(async () => ({
      ready: true,
      status: "ok",
      api_version: "v1",
      platform_version: "1.0.0",
    })),
    version: vi.fn(async () => ({
      platform_version: "1.0.0",
      pipeline_version: "1.0.0",
    })),
    capabilities: vi.fn(async () => ({ ok: true })),
    marketHealth: vi.fn(async () => ({ ok: true, provider: {} })),
    dataHealth: vi.fn(async () => ({ ok: true, health: {} })),
    copilotProviders: vi.fn(async () => ({
      providers: [{ id: "mock", label: "Mock" }],
    })),
    getReport: vi.fn(),
  },
}));

vi.mock("@/lib/api/rbacAuth", () => ({
  rbacAuthApi: {
    me: vi.fn(async () => ({
      ok: true,
      result: {
        user_id: "u1",
        username: "analyst",
        email: "ada@example.com",
        display_name: "Ada Analyst",
        status: "active",
        created_at: "2026-01-01T00:00:00.000Z",
        updated_at: "2026-07-28T10:00:00.000Z",
        last_login: "2026-07-27T18:00:00.000Z",
        roles: ["research_analyst"],
      },
    })),
  },
}));

import {
  DASHBOARD_WIDGETS,
  DEFAULT_HIDDEN_WIDGETS,
  DEFAULT_WIDGET_ORDER,
  useDashboardPrefsStore,
} from "@/lib/dashboard";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("EPIC-F004 dashboard registry", () => {
  it("registers institutional widget set with coherent defaults", () => {
    expect(DEFAULT_WIDGET_ORDER.length).toBe(DASHBOARD_WIDGETS.length - 1);
    expect(DEFAULT_WIDGET_ORDER).toEqual(
      expect.arrayContaining([
        "welcome",
        "attention_brief",
        "market_overview",
        "platform_health",
        "research_reports",
      ]),
    );
    expect(DEFAULT_HIDDEN_WIDGETS).toEqual(
      expect.arrayContaining([
        "valuation_summary",
        "business_quality_summary",
        "risk_summary",
        "tasks",
        "copilot_activity",
      ]),
    );
  });

  it("persists widget visibility and order in store", () => {
    useDashboardPrefsStore.setState({
      widgetOrder: [...DEFAULT_WIDGET_ORDER],
      hiddenWidgets: [...DEFAULT_HIDDEN_WIDGETS],
      pinnedCompanies: [],
      recentSearches: [],
      savedSearches: [],
    });
    // Toggle a default-visible widget off (background_jobs is already in DEFAULT_HIDDEN).
    expect(useDashboardPrefsStore.getState().isWidgetVisible("welcome")).toBe(
      true,
    );
    useDashboardPrefsStore.getState().toggleWidgetVisible("welcome");
    expect(useDashboardPrefsStore.getState().isWidgetVisible("welcome")).toBe(
      false,
    );
    useDashboardPrefsStore.getState().pinCompany("aapl", "Apple");
    expect(useDashboardPrefsStore.getState().isPinned("AAPL")).toBe(true);
    useDashboardPrefsStore.getState().recordSearch("MSFT");
    expect(useDashboardPrefsStore.getState().recentSearches[0]?.query).toBe(
      "MSFT",
    );
  });
});

describe("EPIC-F004 dashboard UI", () => {
  beforeEach(() => {
    cleanup();
    useDashboardPrefsStore.setState({
      widgetOrder: [...DEFAULT_WIDGET_ORDER],
      // RC3-003 — align test state with production defaults (empty executive widgets hidden).
      hiddenWidgets: [...DEFAULT_HIDDEN_WIDGETS],
      pinnedCompanies: [],
      recentSearches: [],
      savedSearches: [],
    });
  });

  it("renders dashboard layout and welcome", async () => {
    const { InstitutionalDashboard } = await import(
      "@/components/dashboard/InstitutionalDashboard"
    );
    wrap(<InstitutionalDashboard />);
    expect(
      screen.getByRole("heading", { name: "Executive Dashboard" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Dashboard widgets")).toBeTruthy();
    expect(screen.getByLabelText("Executive questions")).toBeTruthy();
    expect(await screen.findByText(/Welcome, Ada Analyst/i)).toBeTruthy();
  });

  it("shows empty states without inventing portfolio metrics", async () => {
    const { PortfolioSummaryWidget } = await import(
      "@/components/dashboard/widgets/ResearchPortfolioWidgets"
    );
    wrap(<PortfolioSummaryWidget />);
    const heading = screen.getByRole("heading", { name: "Portfolio Snapshot" });
    const card = heading.closest('[class*="rounded"]') ?? heading.parentElement!;
    expect(within(card as HTMLElement).getAllByText("Data unavailable.").length).toBeGreaterThan(0);
    expect(
      within(card as HTMLElement).getByRole("link", { name: /Open Portfolio/i }),
    ).toBeTruthy();
  });

  it("loads platform health from API", async () => {
    const { PlatformHealthWidget } = await import(
      "@/components/dashboard/widgets/SystemAiWidgets"
    );
    wrap(<PlatformHealthWidget />);
    expect(await screen.findByText(/ready=true/i)).toBeTruthy();
  });
});

describe("EPIC-F004 foundation version", () => {
  it("is foundation 2.0.0-rc.1", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
