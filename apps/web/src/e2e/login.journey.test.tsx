/**
 * @vitest-environment jsdom
 *
 * EPIC-F011 — Login journey (auth public surface).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ThemeProvider } from "@/providers/ThemeProvider";

vi.mock("next/navigation", () => ({
  usePathname: () => "/login",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "unauthenticated",
    session: null,
    user: null,
    login: vi.fn(),
  }),
}));

describe("EPIC-F011 login journey", () => {
  it("exposes accessible sign-in controls", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(screen.getByLabelText(/^username/i)).toBeTruthy();
    expect(document.getElementById("login-password")).toBeTruthy();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /forgot password/i })).toBeTruthy();
  });
});
