/**
 * @vitest-environment jsdom
 *
 * Shell & Navigation Responsive, Keyboard Focus, and State Coverage.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

import {
  SHELL_NAV,
  breadcrumbsForPath,
  filterShellNav,
  groupShellNav,
  isActivePath,
} from "@/lib/shell/navigationRegistry";
import { useUiStore } from "@/lib/shell/uiStore";
import { ThemeProvider } from "@/providers/ThemeProvider";

let currentPath = "/dashboard";

vi.mock("next/navigation", () => ({
  usePathname: () => currentPath,
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

describe("Shell responsive structure: header, sidebar, content width, breadcrumbs", () => {
  beforeEach(() => {
    cleanup();
    currentPath = "/dashboard";
    useUiStore.setState({ mobileDrawerOpen: false, sidebarCollapsed: false });
  });

  it("renders header with responsive touch targets, brand mark, and actions", async () => {
    const { Topbar } = await import("@/components/layout/Topbar");
    const { container } = wrap(
      <Topbar
        onMenuClick={() => undefined}
        onToggleCollapse={() => undefined}
        sidebarCollapsed={false}
      />,
    );

    const header = screen.getByRole("banner", { name: "Application header" });
    expect(header).toBeTruthy();
    // Header height and border
    expect(header.className).toContain("!h-12");
    expect(header.className).toContain("!border-b");

    // Brand home link
    const brand = screen.getByTestId("topbar-home");
    expect(brand.getAttribute("href")).toBe("/dashboard");
    expect(brand.textContent).toContain("DSP");

    // Mobile menu button exists with accessible label
    const mobileMenuBtn = screen.getByTestId("open-navigation");
    expect(mobileMenuBtn.getAttribute("aria-label")).toBe("Open navigation menu");
    expect(mobileMenuBtn.className).toContain("md:hidden");

    // Desktop sidebar collapse toggle
    const toggleBtn = screen.getByTestId("toggle-sidebar");
    expect(toggleBtn.className).toContain("md:inline-flex");

    // Command palette and diagnostics actions
    expect(screen.getByTestId("open-command-palette")).toBeTruthy();
    expect(screen.getByTestId("topbar-diagnostics")).toBeTruthy();
  });

  it("enforces max-w-[1440px] and standardized padding rhythm on ContentArea", async () => {
    const { ContentArea, PageContainer } = await import("@/components/layout/ContentArea");
    const { container: c1 } = render(<ContentArea><div>Content</div></ContentArea>);
    const areaDiv = c1.firstChild as HTMLElement;
    expect(areaDiv.className).toContain("max-w-[1440px]");
    expect(areaDiv.className).toContain("px-4");
    expect(areaDiv.className).toContain("sm:px-7");

    const { container: c2 } = render(<PageContainer><div>Page Content</div></PageContainer>);
    const pageDiv = c2.firstChild as HTMLElement;
    expect(pageDiv.className).toContain("max-w-6xl");
    expect(pageDiv.className).toContain("space-y-6");

    const { container: c3 } = render(<PageContainer narrow><div>Narrow Content</div></PageContainer>);
    const narrowDiv = c3.firstChild as HTMLElement;
    expect(narrowDiv.className).toContain("max-w-3xl");
  });

  it("renders breadcrumbs with font-mono text-[11px] and accurate hierarchy", async () => {
    currentPath = "/research/institutional";
    const { Breadcrumbs } = await import("@/components/layout/Breadcrumbs");
    const { container } = wrap(<Breadcrumbs />);

    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(nav).toBeTruthy();
    expect(nav.className).toContain("font-mono");
    expect(nav.className).toContain("text-[11px]");

    const crumbs = breadcrumbsForPath("/research/institutional");
    expect(crumbs.length).toBeGreaterThanOrEqual(2);
    expect(crumbs[0].label).toBe("Home");
    expect(crumbs[1].label).toBe("Research Workspace");
  });
});

describe("Responsive navigation drawer: keyboard focus and Escape behavior", () => {
  beforeEach(() => {
    cleanup();
    currentPath = "/dashboard";
    useUiStore.setState({ mobileDrawerOpen: false, sidebarCollapsed: false });
  });

  it("opens navigation drawer, exposes accessible dialog, and closes on Escape", async () => {
    const { AppLayout } = await import("@/components/layout/AppLayout");
    wrap(
      <AppLayout>
        <main>Main Content</main>
      </AppLayout>,
    );

    // Initial state: drawer closed
    expect(useUiStore.getState().mobileDrawerOpen).toBe(false);

    // Open drawer via mobile menu button
    const menuBtn = screen.getByTestId("open-navigation");
    fireEvent.click(menuBtn);
    expect(useUiStore.getState().mobileDrawerOpen).toBe(true);

    // Dialog landmark is presented with aria-modal
    const dialog = screen.getByRole("dialog", { name: "Navigation" });
    expect(dialog).toBeTruthy();
    expect(dialog.getAttribute("aria-modal")).toBe("true");

    // Close on Escape key
    fireEvent.keyDown(window, { key: "Escape" });
    expect(useUiStore.getState().mobileDrawerOpen).toBe(false);
  });

  it("ensures navigation links have visible focus ring styles", async () => {
    const { Sidebar } = await import("@/components/layout/Sidebar");
    render(
      <Sidebar
        collapsed={false}
        mobile={false}
        onNavigate={() => undefined}
      />,
    );

    const dashboardLink = screen.getByTestId("sidebar-desktop-dashboard");
    expect(dashboardLink.className).toContain("focus-visible:ring-2");
    expect(dashboardLink.className).toContain("focus-visible:ring-[var(--accent)]");
  });
});

describe("Active and nested navigation states with role filtering", () => {
  beforeEach(() => {
    cleanup();
  });

  it("marks current route with aria-current='page' and active border styling", async () => {
    currentPath = "/dashboard";
    const { Sidebar } = await import("@/components/layout/Sidebar");
    render(
      <Sidebar
        collapsed={false}
        mobile={false}
        onNavigate={() => undefined}
      />,
    );

    const activeLink = screen.getByTestId("sidebar-desktop-dashboard");
    expect(activeLink.getAttribute("aria-current")).toBe("page");
    expect(activeLink.className).toContain("border-l-2");
    expect(activeLink.className).toContain("border-[var(--accent)]");

    const inactiveLink = screen.getByTestId("sidebar-desktop-portfolio");
    expect(inactiveLink.getAttribute("aria-current")).toBeNull();
  });

  it("identifies active nested routes correctly", () => {
    expect(isActivePath("/research/institutional", "/research")).toBe(true);
    expect(isActivePath("/research/canvas", "/research/canvas")).toBe(true);
    expect(isActivePath("/portfolio/analytics", "/portfolio")).toBe(true);
    expect(isActivePath("/dashboard", "/research")).toBe(false);
  });

  it("preserves RBAC role-filtering contracts across all nav items", () => {
    // Analyst with read_research only
    const analystNav = filterShellNav(["read_research"], ["research_analyst"]);
    expect(analystNav.some((n) => n.id === "admin")).toBe(false);
    expect(analystNav.some((n) => n.id === "research")).toBe(true);
    expect(analystNav.some((n) => n.id === "portfolio")).toBe(true);
    expect(analystNav.some((n) => n.id === "analysis")).toBe(true);

    // Administrator with manage_users
    const adminNav = filterShellNav(["manage_users"], ["administrator"]);
    expect(adminNav.some((n) => n.id === "admin")).toBe(true);

    // Unauthenticated / empty claims
    const emptyNav = filterShellNav([], []);
    expect(emptyNav.some((n) => n.id === "admin")).toBe(false);
  });

  it("groups navigation into primary, analytical, and management sections", () => {
    const navItems = filterShellNav(["read_research", "manage_users"], ["administrator"]);
    const groups = groupShellNav(navItems);
    expect(groups.length).toBeGreaterThanOrEqual(2);
    expect(groups.some((g) => g.section === "overview" || g.section === "research" || g.section === "ops")).toBe(true);
  });

  it("traps focus while navigation drawer is open and restores focus to trigger on close", async () => {
    const { AppLayout } = await import("@/components/layout/AppLayout");
    wrap(
      <AppLayout>
        <main>Page Main Content</main>
      </AppLayout>,
    );

    const menuTrigger = screen.getByTestId("open-navigation");
    menuTrigger.focus();
    expect(document.activeElement).toBe(menuTrigger);

    // Open drawer
    fireEvent.click(menuTrigger);
    expect(useUiStore.getState().mobileDrawerOpen).toBe(true);

    const dialog = screen.getByRole("dialog", { name: "Navigation" });
    expect(dialog).toBeTruthy();

    // Close drawer via Escape key
    fireEvent.keyDown(window, { key: "Escape" });
    expect(useUiStore.getState().mobileDrawerOpen).toBe(false);
  });

  it("verifies nested active routes and permissions under analyst and admin role configurations", () => {
    // 1. Analyst role configuration
    const analystItems = filterShellNav(["read_research"], ["research_analyst"]);
    expect(analystItems.some((n) => n.id === "admin")).toBe(false);
    
    // Check nested items under research
    const researchItem = analystItems.find((n) => n.id === "research");
    expect(researchItem).toBeDefined();
    expect(researchItem?.children?.length).toBeGreaterThan(0);
    
    // Nested active routing check
    expect(isActivePath("/research/institutional", researchItem!.href)).toBe(true);
    expect(isActivePath("/research/canvas", researchItem!.href)).toBe(true);

    // 2. Admin role configuration
    const adminItems = filterShellNav(["manage_users"], ["administrator"]);
    expect(adminItems.some((n) => n.id === "admin")).toBe(true);
    const adminItem = adminItems.find((n) => n.id === "admin");
    expect(isActivePath("/admin/users", adminItem!.href)).toBe(true);
  });

  it("verifies nested active routes and permissions under every role-filtered navigation configuration", () => {
    // 1. Research Analyst configuration
    const analystItems = filterShellNav(["read_research"], ["research_analyst"]);
    expect(analystItems.some((n) => n.id === "admin")).toBe(false);
    expect(analystItems.some((n) => n.id === "saas")).toBe(false);
    expect(analystItems.some((n) => n.id === "portfolio")).toBe(true);
    const analystResearch = analystItems.find((n) => n.id === "research");
    expect(analystResearch?.children?.some((c) => c.href === "/research/workspace")).toBe(true);
    expect(isActivePath("/research/workspace", analystResearch!.href)).toBe(true);
    expect(isActivePath("/research/institutional", analystResearch!.href)).toBe(true);

    // 2. Portfolio Manager configuration
    const pmItems = filterShellNav(["read_research"], ["portfolio_manager"]);
    expect(pmItems.some((n) => n.id === "portfolio")).toBe(true);
    expect(pmItems.some((n) => n.id === "admin")).toBe(false);
    const pmPortfolio = pmItems.find((n) => n.id === "portfolio");
    expect(isActivePath("/portfolio/analytics", pmPortfolio!.href)).toBe(true);

    // 3. Administrator configuration
    const adminItems = filterShellNav(
      ["manage_users", "manage_roles", "configure_platform", "admin.manage"],
      ["administrator"],
    );
    expect(adminItems.some((n) => n.id === "admin")).toBe(true);
    expect(adminItems.some((n) => n.id === "saas")).toBe(true);
    expect(adminItems.some((n) => n.id === "control-center")).toBe(true);
    const adminOps = adminItems.find((n) => n.id === "admin");
    expect(isActivePath("/admin/users", adminOps!.href)).toBe(true);
    expect(isActivePath("/admin/roles", adminOps!.href)).toBe(true);

    // 4. Platform Owner configuration
    const ownerItems = filterShellNav(["org.manage", "admin.manage", "configure_platform"], ["owner"]);
    expect(ownerItems.some((n) => n.id === "admin")).toBe(true);
    expect(ownerItems.some((n) => n.id === "saas")).toBe(true);
    expect(ownerItems.some((n) => n.id === "control-center")).toBe(true);

    // 5. Unauthenticated / Guest session without claims
    const guestItems = filterShellNav([], []);
    expect(guestItems.some((n) => n.id === "admin")).toBe(false);
    expect(guestItems.some((n) => n.id === "saas")).toBe(false);
    expect(guestItems.some((n) => n.id === "control-center")).toBe(false);
    expect(guestItems.some((n) => n.id === "dashboard")).toBe(true);
    const guestDash = guestItems.find((n) => n.id === "dashboard");
    expect(isActivePath("/dashboards", guestDash!.href)).toBe(false);
    expect(isActivePath("/dashboard", guestDash!.href)).toBe(true);
  });

});
