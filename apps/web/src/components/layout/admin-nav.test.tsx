/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

const pathname = vi.hoisted(() => ({ value: "/dashboard" }));

vi.mock("next/navigation", () => ({
  usePathname: () => pathname.value,
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
      permissions: ["manage_users"],
      roles: ["administrator"],
    },
    user: {
      displayName: "Ada Admin",
      permissions: ["manage_users"],
      roles: ["administrator"],
    },
  }),
}));

vi.mock("@/lib/analysis/recentAnalyses", () => ({
  loadRecentAnalyses: () => [],
}));

import { Sidebar } from "./Sidebar";

describe("Admin navigation", () => {
  beforeEach(() => {
    cleanup();
  });

  it("links Admin in the desktop sidebar and marks /admin active", () => {
    pathname.value = "/admin";
    render(<Sidebar collapsed={false} />);
    const link = screen.getByRole("link", { name: "Admin" });
    expect(link.getAttribute("href")).toBe("/admin");
    expect(link.getAttribute("aria-current")).toBe("page");
    expect(
      screen.getByRole("link", { name: "Dashboard" }).getAttribute("aria-current"),
    ).toBeNull();
  });

  it("links Admin in the mobile drawer and closes it on click", () => {
    pathname.value = "/dashboard";
    const onNavigate = vi.fn();
    render(<Sidebar collapsed={false} mobile onNavigate={onNavigate} />);
    const link = screen.getByRole("link", { name: "Admin" });
    expect(link.getAttribute("href")).toBe("/admin");
    fireEvent.click(link);
    expect(onNavigate).toHaveBeenCalled();
  });
});
