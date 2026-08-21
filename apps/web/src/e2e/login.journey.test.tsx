/**
 * @vitest-environment jsdom
 *
 * EPIC-F011 — Login journey (auth public surface).
 * Chooser → password / Google (email OTP removed; mobile OTP on /mobile-login).
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

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

vi.mock("@/lib/auth/useAuthProviders", () => ({
  useAuthProviders: () => ({
    loading: false,
    oauthAvailable: [{ provider: "GOOGLE", available: true, status: "available" }],
    oauthComingSoon: [],
    smsStatus: "available",
    smsMessage: null,
    magicLinkStatus: "coming_soon",
    magicLinkMessage: null,
    webauthnAvailable: false,
    webauthnMessage: null,
  }),
}));

afterEach(() => cleanup());

describe("EPIC-F011 login journey", () => {
  it("shows password and Google; no email OTP chooser", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("button", { name: /login with password/i }),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: /login with otp/i })).toBeNull();
    expect(
      screen.getByRole("button", { name: /continue with google/i }),
    ).toBeTruthy();
    expect(screen.getByText(/how would you like to login/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: /sign in with mobile/i })).toBeTruthy();
  });

  it("opens password step with username/email/mobile identifier", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /login with password/i }));
    expect(screen.getByLabelText(/identifier/i)).toBeTruthy();
    expect(document.getElementById("login-password")).toBeTruthy();
    expect(screen.getByRole("button", { name: /^login$/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /forgot password/i })).toBeTruthy();
  });
});
