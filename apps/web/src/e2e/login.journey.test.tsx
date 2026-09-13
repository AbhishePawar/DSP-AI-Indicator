/**
 * @vitest-environment jsdom
 *
 * Public login journey — Google OAuth only.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

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
  it("shows only Google login and no alternate auth methods", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("button", { name: /continue with google/i }),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: /username and password/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /mobile number and otp/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /username and otp/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /forgot password/i })).toBeNull();
    expect(screen.queryByText(/demo mode/i)).toBeNull();
    expect(screen.queryByRole("link", { name: /request access/i })).toBeNull();
  });
});
