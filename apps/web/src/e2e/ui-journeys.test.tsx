/**
 * @vitest-environment jsdom
 *
 * EPIC-F011 — Workspace UI journey smoke (mocked APIs).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
      refreshToken: null,
      tokenType: "Bearer",
      role: "administrator",
      roles: ["administrator"],
      permissions: [
        "read_research",
        "manage_users",
        "view_audit",
        "configure_platform",
      ],
      subject: "u1",
      username: "admin",
      displayName: "Ada Admin",
      email: "ada@example.com",
      authMethod: "rbac",
      sessionId: "s1",
      issuedAt: "2026-07-28T10:00:00.000Z",
      expiresAt: null,
      rememberMe: false,
    },
    user: {
      subject: "u1",
      username: "admin",
      displayName: "Ada Admin",
      email: "ada@example.com",
      role: "administrator",
      roles: ["administrator"],
      permissions: [
        "read_research",
        "manage_users",
        "view_audit",
        "configure_platform",
      ],
    },
    loadProfile: vi.fn(),
    logout: vi.fn(),
    login: vi.fn(),
  }),
}));

vi.mock("@/providers/ThemeProvider", () => ({
  useTheme: () => ({
    mode: "system",
    resolved: "light",
    setMode: vi.fn(),
    cycleMode: vi.fn(),
  }),
}));

vi.mock("@/providers/PersistenceProvider", () => ({
  usePersistence: () => ({
    preferences: {
      theme: "system",
      defaultLandingPage: "/dashboard",
      preferredWatchlistView: null,
    },
    updatePreferences: vi.fn(),
  }),
}));

vi.mock("@/providers/NotificationProvider", () => ({
  useNotifications: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: vi.fn(async () => ({
      ok: true,
      capability: "analyse",
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "1.0.0",
      pipeline_version: "1.0.0",
      correlation_id: "e2e",
      payload: {
        ok: true,
        metadata: {
          pipeline_version: "1.0.0",
          platform_version: "1.0.0",
          execution_order: [],
          confidence_summary: {},
          warnings: [],
          total_elapsed_ms: 1,
        },
        stage_summaries: [],
        results: {},
      },
    })),
    health: vi.fn(async () => ({ ok: true })),
  },
}));

vi.mock("@/lib/api/adminClient", () => ({
  adminApi: {
    dashboard: vi.fn(async () => ({
      generated_at: "2026-07-28T12:00:00.000Z",
      users_count: 1,
      sessions_count: 1,
      active_sessions_count: 1,
      audit_records_count: 0,
      workflow_records_count: 0,
      research_refs_count: 0,
      roles_count: 1,
      permissions_count: 1,
      health_status: "pass",
      metadata: { source: "admin" },
    })),
    listUsers: vi.fn(async () => []),
    listRoles: vi.fn(async () => []),
    listPermissions: vi.fn(async () => []),
    listSessions: vi.fn(async () => []),
    listAudit: vi.fn(async () => []),
    timeline: vi.fn(async () => []),
    health: vi.fn(async () => ({ status: "pass", ready: true, checks: [] })),
    versions: vi.fn(async () => ({ packages: [] })),
    configuration: vi.fn(async () => ({
      items: [],
      message: "Data unavailable.",
    })),
    featureFlags: vi.fn(async () => ({ flags: {}, message: "Data unavailable." })),
    metrics: vi.fn(async () => ({ users: 1 })),
    workflowHistory: vi.fn(async () => []),
    researchArchive: vi.fn(async () => []),
    exportAudit: vi.fn(async () => ({ records: [], count: 0 })),
  },
}));

vi.mock("@/lib/api/rbacAuth", () => ({
  rbacAuthApi: {
    listSessions: vi.fn(async () => ({ ok: true, result: [] })),
  },
}));

vi.mock("@/lib/portfolio/PortfolioProvider", () => ({
  usePortfolio: () => ({
    holdings: [],
    addHolding: vi.fn(),
    removeHolding: vi.fn(),
    clearHoldings: vi.fn(),
  }),
}));

import { useAdminConsolePrefsStore } from "@/lib/admin-console";
import { useSettingsPrefsStore } from "@/lib/settings";
import { useResearchWorkspacePrefsStore } from "@/lib/research-workspace";

function wrap(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("EPIC-F011 UI journeys", () => {
  beforeEach(() => {
    cleanup();
    useAdminConsolePrefsStore.setState({
      activeSection: "overview",
      leftOpen: true,
      rightOpen: true,
    });
    useSettingsPrefsStore.setState({
      activeSection: "about",
      leftOpen: true,
      rightOpen: true,
    });
    useResearchWorkspacePrefsStore.setState({
      activeSection: "diff",
      leftOpen: true,
      rightOpen: true,
    });
  });

  it("admin overview journey loads dashboard region", async () => {
    const { AdminConsole } = await import(
      "@/components/admin-console/AdminConsole"
    );
    wrap(<AdminConsole />);
    expect(await screen.findByText("Administration Overview")).toBeTruthy();
    expect(screen.getByLabelText("Main administration view")).toBeTruthy();
  });

  it("settings about journey shows foundation version", async () => {
    const { SettingsWorkspace } = await import(
      "@/components/settings-workspace/SettingsWorkspace"
    );
    wrap(<SettingsWorkspace />);
    expect(await screen.findByText("Version Information")).toBeTruthy();
  });

  it("research diff journey stays honest when API missing", async () => {
    const { DiffSection } = await import(
      "@/components/research-workspace/Sections"
    );
    wrap(<DiffSection />);
    expect(screen.getByText("Research Diff Viewer")).toBeTruthy();
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("portfolio empty journey shows data unavailable when no holdings", async () => {
    const { SummarySection } = await import(
      "@/components/portfolio-intelligence/Sections"
    );
    wrap(
      <SummarySection holdings={[]} watchlistCount={0} lastUpdated={null} />,
    );
    expect(screen.getByText("Portfolio Overview")).toBeTruthy();
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });
});
