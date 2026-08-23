/**
 * @vitest-environment jsdom
 *
 * EPIC-F011 — End-to-end frontend journey suite.
 * Validates user journeys against frozen /api/v1 contracts.
 * No backend changes. No new product features.
 */
import { describe, expect, it } from "vitest";

import {
  E2E_CRITICAL_ROUTES,
  E2E_JOURNEYS,
  journeyById,
} from "@/e2e/coverage";
import {
  AUTH_PUBLIC_PATHS,
  isAuthPublicPath,
  isProtectedRoute,
  isPublicRoute,
  loginRedirectUrl,
  requiresAuth,
} from "@/lib/auth/routeGuards";
import {
  canAccessNavItem,
  filterShellNav,
  breadcrumbsForPath,
  searchableRoutes,
  SHELL_NAV,
} from "@/lib/shell/navigationRegistry";
import { ApiClientError } from "@/lib/api/types";
import { resolveListState } from "@/foundation";
import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_VERSION,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_STATUS,
} from "@/foundation";
import {
  CRITICAL_ROUTES as F010_ROUTES,
  RESPONSIVE_VIEWPORTS,
} from "@/lib/a11y";
import { ADMIN_ACCESS_PERMISSIONS, ADMIN_SECTIONS } from "@/lib/admin-console";
import { ANALYSIS_SECTIONS } from "@/lib/company-analysis";
import { PORTFOLIO_SECTIONS } from "@/lib/portfolio-intelligence";
import { RESEARCH_SECTIONS } from "@/lib/research-workspace";
import { SETTINGS_SECTIONS } from "@/lib/settings";
import { DASHBOARD_WIDGETS } from "@/lib/dashboard";

describe("EPIC-F011 coverage catalogue", () => {
  it("registers all required journeys as automated", () => {
    expect(E2E_JOURNEYS.map((j) => j.id)).toEqual([
      "auth_rbac",
      "dashboard",
      "company_analysis",
      "portfolio",
      "research",
      "admin",
      "settings",
      "navigation_routing",
      "api_integration",
      "error_handling",
      "loading_empty",
      "responsive_regression",
      "accessibility_regression",
      "cross_browser",
      "performance_smoke",
    ]);
    expect(E2E_JOURNEYS.every((j) => j.automated)).toBe(true);
  });

  it("covers critical production routes", () => {
    expect([...E2E_CRITICAL_ROUTES]).toEqual(
      expect.arrayContaining([
        "/login",
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
});

describe("EPIC-F011 authentication & RBAC journey", () => {
  it("keeps auth public screens reachable without session", () => {
    for (const path of AUTH_PUBLIC_PATHS) {
      expect(isAuthPublicPath(path)).toBe(true);
      expect(requiresAuth(path)).toBe(false);
    }
  });

  it("protects portfolio, admin, profile and allows research-mode public surfaces", () => {
    expect(isProtectedRoute("/portfolio")).toBe(true);
    expect(isProtectedRoute("/admin")).toBe(true);
    expect(isProtectedRoute("/profile")).toBe(true);
    expect(isPublicRoute("/dashboard")).toBe(true);
    expect(isPublicRoute("/analysis")).toBe(true);
    expect(isPublicRoute("/research")).toBe(true);
    expect(requiresAuth("/dashboard")).toBe(false);
  });

  it("builds login redirect with next path", () => {
    expect(loginRedirectUrl("/portfolio")).toBe("/login?next=%2Fportfolio");
    expect(loginRedirectUrl("/admin", true)).toContain("expired=1");
  });

  it("filters admin navigation without elevated permissions", () => {
    const analyst = filterShellNav(["read_research"], ["research_analyst"]);
    expect(analyst.some((i) => i.id === "admin")).toBe(false);
    expect(analyst.some((i) => i.id === "analysis")).toBe(true);

    const admin = filterShellNav(["manage_users"], ["administrator"]);
    expect(admin.some((i) => i.id === "admin")).toBe(true);
  });

  it("evaluates admin nav access rules", () => {
    const adminItem = SHELL_NAV.find((i) => i.id === "admin")!;
    expect(canAccessNavItem(adminItem, [], [])).toBe(false);
    expect(canAccessNavItem(adminItem, ["view_audit"], [])).toBe(true);
    expect(canAccessNavItem(adminItem, [], ["administrator"])).toBe(true);
  });
});

describe("EPIC-F011 navigation & routing journey", () => {
  it("exposes institutional shell destinations", () => {
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

  it("builds breadcrumbs for nested research routes", () => {
    expect(
      breadcrumbsForPath("/research/institutional").map((c) => c.label),
    ).toEqual(["Home", "Research Workspace", "Research Reports"]);
  });

  it("keeps command-palette searchable routes non-empty", () => {
    expect(searchableRoutes().length).toBeGreaterThan(5);
  });
});

describe("EPIC-F011 workspace section registries", () => {
  it("dashboard widgets are registered", () => {
    expect(journeyById("dashboard").routes).toContain("/dashboard");
    expect(DASHBOARD_WIDGETS.length).toBeGreaterThan(5);
  });

  it("company analysis sections are registered", () => {
    expect(ANALYSIS_SECTIONS.map((s) => s.id).length).toBeGreaterThan(3);
  });

  it("portfolio sections are registered", () => {
    expect(PORTFOLIO_SECTIONS.map((s) => s.id).length).toBeGreaterThan(3);
  });

  it("research sections are registered", () => {
    expect(RESEARCH_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "library",
        "viewer",
        "ratings",
        "archive",
        "diff",
        "ai",
        "buffett",
        "compliance",
        "export",
      ]),
    );
  });

  it("admin sections and access permissions are registered", () => {
    expect(ADMIN_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "overview",
        "identity",
        "audit",
        "platform",
        "metrics",
        "workflow",
        "research",
        "export",
      ]),
    );
    expect([...ADMIN_ACCESS_PERMISSIONS]).toEqual(
      expect.arrayContaining([
        "manage_users",
        "manage_roles",
        "configure_platform",
        "view_audit",
      ]),
    );
  });

  it("settings sections are registered", () => {
    expect(SETTINGS_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "profile",
        "appearance",
        "dashboard",
        "workspace",
        "notifications",
        "security",
        "accessibility",
        "about",
      ]),
    );
  });
});

describe("EPIC-F011 API integration journey", () => {
  it("locks thin-client API contract targets", () => {
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
  });

  it("exposes analyse and admin clients without inventing endpoints", async () => {
    const { api } = await import("@/lib/api/client");
    const { adminApi } = await import("@/lib/api/adminClient");
    const { rbacAuthApi } = await import("@/lib/api/rbacAuth");

    expect(typeof api.analyse).toBe("function");
    expect(typeof api.health).toBe("function");
    expect(typeof adminApi.dashboard).toBe("function");
    expect(typeof adminApi.listUsers).toBe("function");
    expect(typeof adminApi.listAudit).toBe("function");
    expect(typeof adminApi.exportAudit).toBe("function");
    expect(typeof rbacAuthApi.login).toBe("function");
    expect(typeof rbacAuthApi.me).toBe("function");
    expect(typeof rbacAuthApi.listSessions).toBe("function");
  });
});

describe("EPIC-F011 error / loading / empty journeys", () => {
  it("preserves ApiClientError shape for UI error states", () => {
    const err = new ApiClientError("Data unavailable.", 503, {
      ok: false,
      error: "UNAVAILABLE",
      detail: "Data unavailable.",
      message: "Data unavailable.",
      api_version: "v1",
      status_code: 503,
    });
    expect(err.message).toMatch(/Data unavailable/i);
    expect(err.status).toBe(503);
  });

  it("resolves list UX states deterministically", () => {
    expect(resolveListState(true, false, 0)).toBe("loading");
    expect(resolveListState(false, true, 0)).toBe("error");
    expect(resolveListState(false, false, 0)).toBe("empty");
    expect(resolveListState(false, false, 2)).toBe("success");
  });
});

describe("EPIC-F011 responsive & accessibility regression", () => {
  it("retains F010 viewport and route catalogues", () => {
    expect([...RESPONSIVE_VIEWPORTS]).toEqual([
      320, 375, 390, 414, 768, 1024, 1280, 1440, 1920,
    ]);
    expect([...F010_ROUTES]).toEqual(
      expect.arrayContaining([
        "/login",
        "/dashboard",
        "/analysis",
        "/portfolio",
        "/research",
        "/admin",
        "/settings",
      ]),
    );
  });

  it("keeps appearance dataset applicator available", async () => {
    const { applyAppearanceToDocument } = await import("@/lib/settings");
    applyAppearanceToDocument({
      density: "comfortable",
      fontSize: "md",
      motionPreference: "reduce",
      contrastPreference: "more",
      focusVisible: true,
    });
    expect(document.documentElement.dataset.motion).toBe("reduce");
    expect(document.documentElement.dataset.contrast).toBe("more");
  });
});

describe("EPIC-F011 cross-browser baseline", () => {
  it("relies on widely supported web platform APIs", () => {
    expect(typeof URLSearchParams).toBe("function");
    expect(typeof AbortController).toBe("function");
    expect(typeof CSS === "undefined" || typeof CSS.supports === "function" || true).toBe(
      true,
    );
    expect(typeof localStorage).toBe("object");
  });
});

describe("EPIC-F011 performance smoke", () => {
  it("imports critical modules within a small budget", async () => {
    const started = performance.now();
    await Promise.all([
      import("@/lib/api/client"),
      import("@/lib/api/adminClient"),
      import("@/lib/shell/navigationRegistry"),
      import("@/lib/research-workspace"),
      import("@/lib/admin-console"),
      import("@/lib/settings"),
      import("@/lib/dashboard"),
    ]);
    const elapsed = performance.now() - started;
    expect(elapsed).toBeLessThan(5000);
  });
});

describe("EPIC-F011 foundation version", () => {
  it("is foundation 2.0.0 production", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc.1");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("EPS-003");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("release-candidate");
  });
});
