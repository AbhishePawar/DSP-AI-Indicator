/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const dashboardPush = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: dashboardPush, replace: vi.fn() }),
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
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
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
    expect(useDashboardPrefsStore.getState().isWidgetVisible("welcome")).toBe(true);
    useDashboardPrefsStore.getState().toggleWidgetVisible("welcome");
    expect(useDashboardPrefsStore.getState().isWidgetVisible("welcome")).toBe(false);
    useDashboardPrefsStore.getState().pinCompany("aapl", "Apple");
    expect(useDashboardPrefsStore.getState().isPinned("AAPL")).toBe(true);
    useDashboardPrefsStore.getState().recordSearch("MSFT");
    expect(useDashboardPrefsStore.getState().recentSearches[0]?.query).toBe("MSFT");
  });
});

describe("canonical public dashboard", () => {
  beforeEach(() => cleanup());

  it("renders SearchFirstDashboard without legacy executive surfaces", async () => {
    const { SearchFirstDashboard } =
      await import("@/components/dashboard/SearchFirstDashboard");
    wrap(<SearchFirstDashboard />);
    expect(screen.getByRole("heading", { name: "Research any company." })).toBeTruthy();
    expect(screen.getByRole("searchbox", { name: /search a company/i })).toBeTruthy();
    expect(screen.queryByText("Executive Dashboard")).toBeNull();
    expect(screen.queryByText("Trust Ladder")).toBeNull();
    expect(screen.queryByLabelText("Dashboard widgets")).toBeNull();
  });

  it("routes a company search into the canonical DSP analysis intent", async () => {
    dashboardPush.mockClear();
    const { SearchFirstDashboard } =
      await import("@/components/dashboard/SearchFirstDashboard");
    wrap(<SearchFirstDashboard />);
    const search = screen.getByRole("searchbox", { name: /search a company/i });
    fireEvent.change(search, { target: { value: "TCS" } });
    fireEvent.keyDown(search, { key: "Enter", code: "Enter" });
    expect(dashboardPush).toHaveBeenCalledWith(
      "/analysis?symbol=TCS&intent=dsp_indicator",
    );
  });
});

describe("EPIC-F004 foundation version", () => {
  it("is foundation 2.0.0-rc.1", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
