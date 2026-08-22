/**
 * @vitest-environment jsdom
 *
 * Public login journey — password, OTP methods, Google, forgot password.
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

describe("public login journey", () => {
  it("shows the four intended login methods and no demo auth", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("button", { name: /username and password/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /mobile number and otp/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /username and otp/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /continue with google/i }),
    ).toBeTruthy();
    expect(screen.queryByText(/demo mode/i)).toBeNull();
    expect(screen.queryByRole("link", { name: /request access/i })).toBeNull();
  });

  it("opens username/password with forgot password", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /username and password/i }));
    expect(document.getElementById("login-username")).toBeTruthy();
    expect(document.getElementById("login-password")).toBeTruthy();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /forgot password/i })).toBeTruthy();
  });
});
