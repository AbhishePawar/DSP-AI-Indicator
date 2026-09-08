/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

import {
  SHELL_NAV,
  breadcrumbsForPath,
  canAccessNavItem,
  filterShellNav,
  groupShellNav,
  isActivePath,
  resolveShellAudience,
  searchableRoutes,
} from "@/lib/shell/navigationRegistry";
import { useUiStore } from "@/lib/shell/uiStore";
import { breadcrumbsFor } from "@/lib/navigation";
import { FRONTEND_FOUNDATION_VERSION } from "@/foundation";
import { LoadingLayout, EmptyLayout, ErrorLayout, PageContainer } from '../../components/layout/ContentArea';
import { Breadcrumbs } from '../../components/layout/Breadcrumbs';



describe("EPIC-F003 navigation registry", () => {
  it("includes institutional shell destinations", () => {
    const hrefs = SHELL_NAV.map((n) => n.href);
    expect(hrefs).toEqual(
      expect.arrayContaining([
        "/dashboard",
        "/analysis",
        "/portfolio",
        "/research",
        "/admin",
        "/settings",
        "/profile",
      ]),
    );
  });

  it("supports nested research navigation", () => {
    const research = SHELL_NAV.find((n) => n.id === "research");
    expect(
      research?.children?.some((c) => c.href === "/research/institutional"),
    ).toBe(true);
    expect(
      research?.children?.some((c) => c.href === "/research/canvas"),
    ).toBe(true);
  });

  it("filters admin without permissions", () => {
    const visible = filterShellNav(["read_research"], ["research_analyst"]);
    expect(visible.some((i) => i.id === "admin")).toBe(false);
    expect(visible.some((i) => i.id === "analysis")).toBe(false);
    expect(visible.map((i) => i.id)).toEqual(["research-home", "settings"]);
  });

  it("keeps institutional nav for operators and administrators", () => {
    const operator = filterShellNav(["ops.view", "read_research"], [
      "portfolio_manager",
    ]);
    expect(operator.some((i) => i.id === "analysis")).toBe(true);
    expect(operator.some((i) => i.id === "admin")).toBe(false);

    const admin = filterShellNav(["manage_users"], ["administrator"]);
    expect(admin.some((i) => i.id === "admin")).toBe(true);
  });

  it("shows admin for manage_users", () => {
    const visible = filterShellNav(["manage_users"], ["administrator"]);
    expect(visible.some((i) => i.id === "admin")).toBe(true);
  });

  it("hides admin for legacy empty claims", () => {
    expect(
      canAccessNavItem(SHELL_NAV.find((i) => i.id === "admin")!, [], []),
    ).toBe(false);
    expect(
      canAccessNavItem(SHELL_NAV.find((i) => i.id === "analysis")!, [], []),
    ).toBe(true);
  });

  it("groups ordinary nav as research then account", () => {
    const groups = groupShellNav(filterShellNav([], []));
    expect(groups.map((g) => g.section)).toEqual(["research", "account"]);
  });

  it("builds breadcrumbs for nested and ticker routes", () => {
    expect(
      breadcrumbsForPath("/research/institutional").map((c) => c.label),
    ).toEqual(["Home", "Research Workspace", "Research Reports"]);
    expect(breadcrumbsFor("/research/acm").map((c) => c.label)).toContain(
      "ACM",
    );
    expect(breadcrumbsForPath("/settings").at(-1)?.label).toBe("Settings");
  });

  it("RBAC-filters searchable routes and hides unfinished AUX", () => {
    const ordinary = searchableRoutes(
      ["read_research"],
      ["research_analyst"],
    ).map((r) => r.path);
    expect(ordinary).not.toContain("/analysis");
    expect(ordinary).not.toContain("/research/canvas");
    expect(ordinary).not.toContain("/admin");
    expect(ordinary).toContain("/settings");

    const operator = searchableRoutes(
      ["ops.view", "read_research"],
      ["portfolio_manager"],
    ).map((r) => r.path);
    expect(operator).toEqual(
      expect.arrayContaining([
        "/analysis",
        "/portfolio",
        "/research",
        "/research/institutional",
      ]),
    );
    expect(operator).not.toContain("/copilot");
    expect(operator).not.toContain("/advisor");
    expect(operator).not.toContain("/launch");
    expect(operator).not.toContain("/screening");
    expect(operator).not.toContain("/admin");

    const admin = searchableRoutes(
      ["manage_users", "read_research"],
      ["administrator"],
    ).map((r) => r.path);
    expect(admin).toContain("/admin");
  });

  it("detects active paths", () => {
    expect(isActivePath("/research/acm", "/research")).toBe(true);
    expect(isActivePath("/dashboard", "/analysis")).toBe(false);
  });

  it("classifies shell audience without deleting institutional routes", () => {
    expect(resolveShellAudience(["read_research"], ["research_analyst"])).toBe(
      "ordinary",
    );
    expect(resolveShellAudience(["ops.view"], ["portfolio_manager"])).toBe(
      "operator",
    );
    expect(resolveShellAudience(["manage_users"], ["administrator"])).toBe(
      "administrator",
    );
    expect(SHELL_NAV.some((i) => i.id === "analysis")).toBe(true);
  });
});

describe("EPIC-F003 uiStore", () => {
  beforeEach(() => {
    useUiStore.setState({
      sidebarCollapsed: false,
      mobileDrawerOpen: false,
      commandPaletteOpen: false,
      recentPages: [],
      favouritePages: [],
    });
  });

  it("toggles sidebar collapse", () => {
    useUiStore.getState().toggleSidebarCollapsed();
    expect(useUiStore.getState().sidebarCollapsed).toBe(true);
  });

  it("records recent and favourites (UI only)", () => {
    useUiStore.getState().recordRecentPage("/analysis", "Company Analysis");
    expect(useUiStore.getState().recentPages[0]?.path).toBe("/analysis");
    useUiStore.getState().toggleFavourite("/analysis", "Company Analysis");
    expect(useUiStore.getState().isFavourite("/analysis")).toBe(true);
    useUiStore.getState().toggleFavourite("/analysis", "Company Analysis");
    expect(useUiStore.getState().isFavourite("/analysis")).toBe(false);
  });
});

describe("EPIC-F003 layout primitives", () => {
  it("renders loading / empty / error layouts", () => {
    const { rerender } = render(<LoadingLayout label="Loading shell…" />);
    expect(screen.getByLabelText("Loading shell…")).toBeTruthy();

    rerender(
      <EmptyLayout title="Data unavailable." description="Nothing here yet." />,
    );
    expect(screen.getByText("Data unavailable.")).toBeTruthy();

    rerender(<ErrorLayout title="Failed" description="Data unavailable." />);
    expect(screen.getByRole("alert")).toBeTruthy();

    rerender(
      <PageContainer>
        <p>Page body</p>
      </PageContainer>,
    );
    expect(screen.getByText("Page body")).toBeTruthy();
  });

  it("renders breadcrumbs for current route", async () => {
    const { Breadcrumbs } = await import("@/components/layout/Breadcrumbs");
    render(<Breadcrumbs />);
    expect(screen.getByLabelText("Breadcrumb")).toBeTruthy();
    expect(screen.getByText("Settings")).toBeTruthy();
  });
});

describe("EPIC-F003 foundation version", () => {
  it("tracks current foundation version", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
  });
});
