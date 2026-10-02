/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

const pathname = vi.hoisted(() => ({ value: "/" }));

vi.mock("next/navigation", () => ({
  usePathname: () => pathname.value,
}));

vi.mock("@/providers/ThemeProvider", () => ({
  useTheme: () => ({
    cycleMode: vi.fn(),
    resolved: "light",
    mode: "light",
  }),
}));

import { MarketingHeader } from "./MarketingHeader";

describe("Marketing menu", () => {
  beforeEach(() => {
    cleanup();
    pathname.value = "/";
  });

  it("includes Admin in the slide-out menu and links to /admin", () => {
    render(<MarketingHeader />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation menu" }));
    const mobile = screen.getByRole("navigation", { name: "Marketing mobile" });
    const admin = within(mobile).getByRole("link", { name: "Admin" });
    expect(admin.getAttribute("href")).toBe("/admin");
    expect(within(mobile).getByRole("link", { name: "About" }).getAttribute("href")).toBe(
      "/about",
    );
    expect(within(mobile).getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe(
      "/login",
    );
    fireEvent.click(admin);
    expect(
      screen.queryByRole("navigation", { name: "Marketing mobile" }),
    ).toBeNull();
  });

  it("marks Admin current only on /admin", () => {
    pathname.value = "/admin";
    render(<MarketingHeader />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation menu" }));
    const mobile = screen.getByRole("navigation", { name: "Marketing mobile" });
    expect(within(mobile).getByRole("link", { name: "Admin" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(
      within(mobile).getByRole("link", { name: "Pricing" }).getAttribute("aria-current"),
    ).toBeNull();
  });
});
