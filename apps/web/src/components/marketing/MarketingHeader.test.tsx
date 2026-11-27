/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MarketingHeader } from "./MarketingHeader";

const mockUseAuth = vi.fn();
const mockLogout = vi.fn();

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/providers/ThemeProvider", () => ({
  useTheme: () => ({
    mode: "dark",
    resolved: "dark",
    cycleMode: vi.fn(),
  }),
}));

describe("MarketingHeader", () => {
  beforeEach(() => {
    mockLogout.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders 'Log in' when anonymous", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      logout: mockLogout,
    });

    render(<MarketingHeader />);
    const link = screen.getByTestId("marketing-account");
    expect(link).toBeInTheDocument();
    expect(link.textContent).toContain("Log in");
  });

  it("renders user display name and toggles account menu with Profile and Logout when authenticated", () => {
    mockUseAuth.mockReturnValue({
      user: {
        userId: "u-1",
        username: "testuser",
        displayName: "Test User",
        roles: ["admin"],
        permissions: [],
      },
      logout: mockLogout,
    });

    render(<MarketingHeader />);
    const accountBtn = screen.getByTestId("marketing-account");
    expect(accountBtn).toBeInTheDocument();
    expect(accountBtn.textContent).toContain("Test User");
    expect(accountBtn.textContent).not.toContain("Log in");

    // Menu should be closed initially
    expect(screen.queryByTestId("marketing-account-menu")).not.toBeInTheDocument();

    // Click to open menu
    fireEvent.click(accountBtn);

    const menu = screen.getByTestId("marketing-account-menu");
    expect(menu).toBeInTheDocument();

    const profileLink = screen.getByTestId("marketing-account-profile");
    expect(profileLink).toBeInTheDocument();
    expect(profileLink.textContent).toBe("Profile");

    const logoutBtn = screen.getByTestId("marketing-account-logout");
    expect(logoutBtn).toBeInTheDocument();
    expect(logoutBtn.textContent).toBe("Logout");
  });
});
