/**
 * @vitest-environment jsdom
 *
 * EPIC-F010 — Responsive Design & Accessibility Validation tests.
 * Quality-only: no product feature coverage.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { useState } from "react";

import {
  CRITICAL_ROUTES,
  RESPONSIVE_VIEWPORTS,
  useCollapsePanelsBelowLg,
} from "@/lib/a11y";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";
import { breakpoints } from "@/components/ds/utilities/responsive";
import { ThemeProvider } from "@/providers/ThemeProvider";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
      subject: "u1",
      username: "analyst",
      displayName: "Ada",
      email: "a@example.com",
      roles: ["research_analyst"],
      permissions: ["read_research"],
      role: "research_analyst",
      tokenType: "Bearer",
      refreshToken: null,
      authMethod: "rbac",
      sessionId: "s1",
      issuedAt: "2026-07-28T10:00:00.000Z",
      expiresAt: null,
      rememberMe: false,
    },
    user: {
      subject: "u1",
      username: "analyst",
      displayName: "Ada",
      email: "a@example.com",
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: ["read_research"],
    },
    logout: vi.fn(),
  }),
}));

vi.mock("@/hooks/usePerformanceTiming", () => ({
  useRouteTransitionTiming: () => undefined,
}));

vi.mock("@/components/beta/BetaShellWidgets", () => ({
  BetaShellWidgets: () => null,
}));

vi.mock("@/components/beta/FeedbackContext", () => ({
  FeedbackProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/layout/ShellCommandPalette", () => ({
  ShellCommandPalette: () => null,
}));

vi.mock("@/components/layout/StatusBar", () => ({
  StatusBar: () => <footer aria-label="Status">Status</footer>,
}));

function wrap(ui: ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

function mockMatchMedia(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

describe("EPIC-F010 responsive validation catalogue", () => {
  it("covers required viewport widths", () => {
    expect([...RESPONSIVE_VIEWPORTS]).toEqual([
      320, 375, 390, 414, 768, 1024, 1280, 1440, 1920,
    ]);
  });

  it("covers critical application routes", () => {
    expect([...CRITICAL_ROUTES]).toEqual([
      "/login",
      "/dashboard",
      "/analysis",
      "/portfolio",
      "/research",
      "/admin",
      "/settings",
    ]);
  });

  it("exposes design-system breakpoints including lg 1024", () => {
    expect(breakpoints.sm).toBe(640);
    expect(breakpoints.md).toBe(768);
    expect(breakpoints.lg).toBe(1024);
    expect(breakpoints.xl).toBe(1280);
  });
});

describe("EPIC-F010 collapse panels below lg", () => {
  function Probe() {
    const [left, setLeft] = useState(true);
    const [right, setRight] = useState(true);
    useCollapsePanelsBelowLg(setLeft, setRight);
    return (
      <div>
        <span data-testid="left">{String(left)}</span>
        <span data-testid="right">{String(right)}</span>
      </div>
    );
  }

  beforeEach(() => {
    cleanup();
  });

  it("closes panels when viewport is below lg", () => {
    mockMatchMedia(true);
    render(<Probe />);
    expect(screen.getByTestId("left").textContent).toBe("false");
    expect(screen.getByTestId("right").textContent).toBe("false");
  });

  it("leaves panels open when viewport is lg+", () => {
    mockMatchMedia(false);
    render(<Probe />);
    expect(screen.getByTestId("left").textContent).toBe("true");
    expect(screen.getByTestId("right").textContent).toBe("true");
  });
});

describe("EPIC-F010 shell accessibility", () => {
  beforeEach(() => {
    cleanup();
    mockMatchMedia(false);
  });

  it("provides mobile drawer Escape close and dialog landmark", async () => {
    const { useUiStore } = await import("@/lib/shell/uiStore");
    useUiStore.setState({ mobileDrawerOpen: false, sidebarCollapsed: false });

    const { AppLayout } = await import("@/components/layout/AppLayout");
    wrap(
      <AppLayout>
        <div>Page</div>
      </AppLayout>,
    );

    fireEvent.click(screen.getByLabelText("Open navigation menu"));
    expect(screen.getByRole("dialog", { name: "Navigation" })).toBeTruthy();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(useUiStore.getState().mobileDrawerOpen).toBe(false);
  });

  it("exposes mobile command palette control", async () => {
    const { Topbar } = await import("@/components/layout/Topbar");
    wrap(
      <Topbar
        onMenuClick={() => undefined}
        onToggleCollapse={() => undefined}
        sidebarCollapsed={false}
      />,
    );
    expect(
      screen.getAllByLabelText("Open search and command palette").length,
    ).toBeGreaterThan(0);
  });

  it("keeps page titles as h1 without nested banner header", async () => {
    const { PageHeader } = await import("@/components/layout/PageHeader");
    const { container } = render(
      <PageHeader title="Dashboard" description="Overview" />,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeTruthy();
    expect(container.querySelector("header")).toBeNull();
  });
});

describe("EPIC-F010 appearance a11y datasets", () => {
  it("documents reduced motion and contrast CSS hooks", async () => {
    const { applyAppearanceToDocument } = await import("@/lib/settings");
    applyAppearanceToDocument({
      density: "compact",
      fontSize: "md",
      motionPreference: "reduce",
      contrastPreference: "more",
      focusVisible: true,
    });
    expect(document.documentElement.dataset.motion).toBe("reduce");
    expect(document.documentElement.dataset.contrast).toBe("more");
    expect(document.documentElement.dataset.focusVisible).toBe("on");
  });
});

describe("EPIC-F010 foundation version", () => {
  it("is foundation 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
  });
});
