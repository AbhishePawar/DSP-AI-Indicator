/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("section=appearance"),
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
    loadProfile: vi.fn(),
    logout: vi.fn(),
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

vi.mock("@/lib/api/rbacAuth", () => ({
  rbacAuthApi: {
    listSessions: vi.fn(async () => ({
      ok: true,
      result: [
        {
          session_id: "s1",
          user_id: "u1",
          created_at: "2026-07-28T10:00:00.000Z",
          expires_at: "2026-07-29T10:00:00.000Z",
          revoked: false,
        },
      ],
    })),
  },
}));

import {
  SETTINGS_SECTIONS,
  applyAppearanceToDocument,
  useSettingsPrefsStore,
} from "@/lib/settings";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";

function wrap(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("EPIC-F009 settings lib", () => {
  it("registers sections", () => {
    expect(SETTINGS_SECTIONS.map((s) => s.id)).toEqual([
      "profile",
      "appearance",
      "dashboard",
      "workspace",
      "notifications",
      "security",
      "accessibility",
      "about",
    ]);
  });

  it("persists appearance preferences", () => {
    useSettingsPrefsStore.setState({
      density: "comfortable",
      fontSize: "md",
      motionPreference: "system",
      contrastPreference: "system",
    });
    useSettingsPrefsStore.getState().setDensity("compact");
    useSettingsPrefsStore.getState().setFontSize("lg");
    useSettingsPrefsStore.getState().setMotionPreference("reduce");
    expect(useSettingsPrefsStore.getState().density).toBe("compact");
    expect(useSettingsPrefsStore.getState().fontSize).toBe("lg");
    expect(useSettingsPrefsStore.getState().motionPreference).toBe("reduce");
  });

  it("applies appearance dataset to document", () => {
    applyAppearanceToDocument({
      density: "compact",
      fontSize: "sm",
      motionPreference: "reduce",
      contrastPreference: "more",
      focusVisible: true,
    });
    expect(document.documentElement.dataset.density).toBe("compact");
    expect(document.documentElement.dataset.fontScale).toBe("sm");
    expect(document.documentElement.dataset.motion).toBe("reduce");
    expect(document.documentElement.dataset.contrast).toBe("more");
    expect(document.documentElement.dataset.focusVisible).toBe("on");
  });
});

describe("EPIC-F009 settings workspace UI", () => {
  beforeEach(() => {
    cleanup();
    useSettingsPrefsStore.setState({
      activeSection: "appearance",
      leftOpen: true,
      rightOpen: true,
      density: "comfortable",
      fontSize: "md",
      notes: [],
    });
  });

  it("renders workspace layout and theme controls", async () => {
    const { SettingsWorkspace } = await import(
      "@/components/settings-workspace/SettingsWorkspace"
    );
    wrap(<SettingsWorkspace />);
    expect(screen.getByLabelText("Settings navigation")).toBeTruthy();
    expect(screen.getByLabelText("Main settings panel")).toBeTruthy();
    expect(screen.getByLabelText("Settings context panel")).toBeTruthy();
    expect(screen.getByText("Theme")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dark" })).toBeTruthy();
  });

  it("switches density preference from UI", async () => {
    const { AppearanceSection } = await import(
      "@/components/settings-workspace/Sections"
    );
    wrap(<AppearanceSection />);
    fireEvent.click(screen.getByRole("button", { name: "Compact" }));
    expect(useSettingsPrefsStore.getState().density).toBe("compact");
  });

  it("displays profile information", async () => {
    useSettingsPrefsStore.setState({ activeSection: "profile" });
    const { ProfileSection } = await import(
      "@/components/settings-workspace/Sections"
    );
    wrap(<ProfileSection />);
    expect(screen.getByText("Account Summary")).toBeTruthy();
    expect(screen.getByText("Ada Analyst")).toBeTruthy();
    expect((await screen.findAllByText("research_analyst")).length).toBeGreaterThan(0);
  });

  it("displays session information in security section", async () => {
    const { SecuritySection } = await import(
      "@/components/settings-workspace/Sections"
    );
    wrap(<SecuritySection />);
    expect(await screen.findByText("Active Sessions")).toBeTruthy();
    expect(await screen.findByText("s1")).toBeTruthy();
  });

  it("displays version information", async () => {
    const { AboutSection } = await import(
      "@/components/settings-workspace/Sections"
    );
    wrap(<AboutSection />);
    expect(screen.getByText("Version Information")).toBeTruthy();
    expect(screen.getAllByText(FRONTEND_FOUNDATION_VERSION).length).toBeGreaterThanOrEqual(1);
  });
});

describe("EPIC-F009 foundation version", () => {
  it("is foundation 2.0.0-rc.1", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
