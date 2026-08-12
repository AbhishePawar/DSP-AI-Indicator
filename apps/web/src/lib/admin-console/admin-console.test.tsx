/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("section=overview"),
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
      permissions: ["manage_users", "view_audit", "configure_platform"],
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
      permissions: ["manage_users", "view_audit", "configure_platform"],
      roles: ["administrator"],
    },
  }),
}));

const dashboardMock = vi.fn();
const usersMock = vi.fn();
const rolesMock = vi.fn();
const permissionsMock = vi.fn();
const sessionsMock = vi.fn();
const getUserMock = vi.fn();
const auditMock = vi.fn();
const timelineMock = vi.fn();
const healthMock = vi.fn();
const versionsMock = vi.fn();
const configMock = vi.fn();
const flagsMock = vi.fn();
const metricsMock = vi.fn();
const workflowMock = vi.fn();
const researchMock = vi.fn();
const exportAuditMock = vi.fn();

vi.mock("@/lib/api/adminClient", () => ({
  adminApi: {
    dashboard: (...args: unknown[]) => dashboardMock(...args),
    listUsers: (...args: unknown[]) => usersMock(...args),
    listRoles: (...args: unknown[]) => rolesMock(...args),
    listPermissions: (...args: unknown[]) => permissionsMock(...args),
    listSessions: (...args: unknown[]) => sessionsMock(...args),
    getUser: (...args: unknown[]) => getUserMock(...args),
    listAudit: (...args: unknown[]) => auditMock(...args),
    timeline: (...args: unknown[]) => timelineMock(...args),
    health: (...args: unknown[]) => healthMock(...args),
    versions: (...args: unknown[]) => versionsMock(...args),
    configuration: (...args: unknown[]) => configMock(...args),
    featureFlags: (...args: unknown[]) => flagsMock(...args),
    metrics: (...args: unknown[]) => metricsMock(...args),
    workflowHistory: (...args: unknown[]) => workflowMock(...args),
    researchArchive: (...args: unknown[]) => researchMock(...args),
    exportAudit: (...args: unknown[]) => exportAuditMock(...args),
  },
}));

import {
  ADMIN_SECTIONS,
  recordsToCsv,
  toJsonSnapshot,
  useAdminConsolePrefsStore,
} from "@/lib/admin-console";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

function wrap(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("EPIC-F008 admin console lib", () => {
  it("registers sections", () => {
    expect(ADMIN_SECTIONS.map((s) => s.id)).toEqual([
      "overview",
      "identity",
      "audit",
      "platform",
      "metrics",
      "workflow",
      "research",
      "export",
      "beta",
    ]);
  });

  it("exports json and csv without inventing rows", () => {
    expect(toJsonSnapshot({ a: 1 })).toContain('"a": 1');
    expect(recordsToCsv([])).toContain("Data unavailable.");
    expect(recordsToCsv([{ entity_id: "e1", kind: "audit_record" }])).toContain(
      "entity_id",
    );
  });

  it("persists notes and tags", () => {
    useAdminConsolePrefsStore.setState({
      notes: [],
      tags: [],
    });
    useAdminConsolePrefsStore.getState().addNote("user:u1", "Check access");
    useAdminConsolePrefsStore.getState().addTag("user:u1", "review");
    expect(useAdminConsolePrefsStore.getState().notes[0]?.text).toBe(
      "Check access",
    );
    expect(useAdminConsolePrefsStore.getState().tags[0]?.label).toBe("review");
  });
});

describe("EPIC-F008 admin console UI", () => {
  beforeEach(() => {
    cleanup();
    dashboardMock.mockReset();
    usersMock.mockReset();
    rolesMock.mockReset();
    permissionsMock.mockReset();
    sessionsMock.mockReset();
    getUserMock.mockReset();
    auditMock.mockReset();
    timelineMock.mockReset();
    healthMock.mockReset();
    versionsMock.mockReset();
    configMock.mockReset();
    flagsMock.mockReset();
    metricsMock.mockReset();
    workflowMock.mockReset();
    researchMock.mockReset();
    exportAuditMock.mockReset();

    dashboardMock.mockResolvedValue({
      generated_at: "2026-07-28T12:00:00.000Z",
      users_count: 2,
      sessions_count: 1,
      active_sessions_count: 1,
      audit_records_count: 3,
      workflow_records_count: 0,
      research_refs_count: 0,
      roles_count: 4,
      permissions_count: 11,
      health_status: "pass",
      metadata: { source: "admin" },
    });
    usersMock.mockResolvedValue([
      {
        user_id: "u1",
        username: "admin",
        email: "admin@example.com",
        status: "active",
        roles: ["administrator"],
      },
    ]);
    rolesMock.mockResolvedValue([
      {
        role_id: "administrator",
        name: "Administrator",
        permissions: ["manage_users"],
        configurable: false,
      },
    ]);
    permissionsMock.mockResolvedValue(["manage_users", "view_audit"]);
    sessionsMock.mockResolvedValue([]);
    auditMock.mockResolvedValue([]);
    timelineMock.mockResolvedValue([]);
    healthMock.mockResolvedValue({
      status: "pass",
      ready: true,
      checks: [{ name: "admin", status: "pass", message: "ok" }],
    });
    versionsMock.mockResolvedValue({
      packages: [{ package: "admin", version: "1.0.0" }],
    });
    configMock.mockResolvedValue({
      source: "environ_DSP_prefix",
      count: 0,
      items: [],
      message: "Data unavailable.",
    });
    flagsMock.mockResolvedValue({
      source: "production_platform",
      flags: { research_mode: true },
    });
    metricsMock.mockResolvedValue({
      users: 2,
      sessions_total: 1,
      sessions_active: 1,
      audit_records: 3,
      workflow_records: 0,
      approval_history: 0,
      research_refs: 0,
      citations: 0,
      provenance: 0,
      metadata_entities: 0,
    });
    workflowMock.mockResolvedValue([]);
    researchMock.mockResolvedValue([]);
    exportAuditMock.mockResolvedValue({
      export_kind: "audit_metadata",
      count: 0,
      records: [],
      rules: [],
    });

    useAdminConsolePrefsStore.setState({
      activeSection: "overview",
      leftOpen: true,
      rightOpen: true,
      selectedUserId: null,
      selectedRoleId: null,
      notes: [],
      tags: [],
    });
  });

  it("renders workspace layout and overview dashboard", async () => {
    const { AdminConsole } = await import(
      "@/components/admin-console/AdminConsole"
    );
    wrap(<AdminConsole />);
    expect(screen.getByLabelText("Administration navigation")).toBeTruthy();
    expect(screen.getByLabelText("Main administration view")).toBeTruthy();
    expect(screen.getByLabelText("Administration context panel")).toBeTruthy();
    expect(await screen.findByText("Administration Overview")).toBeTruthy();
    await waitFor(() => {
      expect(dashboardMock).toHaveBeenCalled();
    });
  });

  it("renders identity user list from API", async () => {
    useAdminConsolePrefsStore.setState({ activeSection: "identity" });
    const { IdentitySection } = await import(
      "@/components/admin-console/Sections"
    );
    wrap(<IdentitySection token="tok" />);
    expect(await screen.findByText("User List")).toBeTruthy();
    expect(await screen.findByText("admin")).toBeTruthy();
    expect(usersMock).toHaveBeenCalled();
    expect(rolesMock).toHaveBeenCalled();
  });

  it("shows honest empty audit state", async () => {
    useAdminConsolePrefsStore.setState({ activeSection: "audit" });
    const { AuditSection } = await import(
      "@/components/admin-console/Sections"
    );
    wrap(<AuditSection token="tok" />);
    expect(await screen.findByText("Audit Log Viewer")).toBeTruthy();
    expect(
      (await screen.findAllByText(/Data unavailable/i)).length,
    ).toBeGreaterThan(0);
  });

  it("loads platform health and metrics", async () => {
    const { PlatformSection, MetricsSection } = await import(
      "@/components/admin-console/Sections"
    );
    wrap(<PlatformSection token="tok" />);
    expect(await screen.findByText("Platform Health")).toBeTruthy();
    await waitFor(() => expect(healthMock).toHaveBeenCalled());

    cleanup();
    wrap(<MetricsSection token="tok" />);
    expect(await screen.findByText("System Metrics")).toBeTruthy();
    await waitFor(() => expect(metricsMock).toHaveBeenCalled());
  });
});

describe("EPIC-F008 foundation version", () => {
  it("is foundation 2.0.0-rc.1", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
