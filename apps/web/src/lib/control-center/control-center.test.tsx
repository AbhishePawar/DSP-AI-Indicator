/**
 * @vitest-environment jsdom
 */
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ControlCenter } from "@/components/control-center";

vi.mock("next/navigation", () => ({
  usePathname: () => "/control-center",
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

const controlCenterDashboard = vi.fn(async () => ({
  ok: true,
  result: {
    modules: ["branding", "feature_flags", "valuation"],
    feature_flags: { copilot: true },
    branding: { theme: "system" },
    recent_changes: [],
    business_rules_count: 0,
    note: "Super Admin Control Center — configuration operating system.",
  },
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    controlCenterDashboard: (...args: unknown[]) =>
      controlCenterDashboard(...args),
    controlCenterRegistry: vi.fn(async () => ({
      ok: true,
      result: {
        modules: {
          branding: { theme: "system" },
          feature_flags: { copilot: true },
        },
      },
    })),
    controlCenterHistory: vi.fn(async () => ({
      ok: true,
      result: { history: [] },
    })),
    controlCenterBusinessRules: vi.fn(async () => ({
      ok: true,
      result: { rules: [] },
    })),
    controlCenterMonitoring: vi.fn(async () => ({
      ok: true,
      result: { note: "reuse" },
    })),
    controlCenterAudit: vi.fn(async () => ({
      ok: true,
      result: { audit: [] },
    })),
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

describe("ControlCenter", () => {
  beforeEach(() => {
    cleanup();
    controlCenterDashboard.mockClear();
  });

  it("renders overview from control center API", async () => {
    renderWithClient(<ControlCenter />);
    expect(screen.getByTestId("control-center")).toBeTruthy();
    await waitFor(() => {
      expect(controlCenterDashboard).toHaveBeenCalled();
    });
    expect(
      screen.getByRole("heading", { name: /Super Admin Control Center/i }),
    ).toBeTruthy();
    expect(screen.getByRole("tab", { name: /Overview/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /Feature flags/i })).toBeTruthy();
  });
});
