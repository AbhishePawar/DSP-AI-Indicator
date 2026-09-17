/**
 * @vitest-environment jsdom
 *
 * Public login journey — Google OAuth plus username/password login.
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
  it("shows Google and username/password login methods", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("button", { name: /continue with google/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /username and password/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /mobile number and otp/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /username and otp/i }),
    ).toBeTruthy();
    expect(screen.queryByText(/demo mode/i)).toBeNull();
    expect(screen.queryByRole("link", { name: /request access/i })).toBeNull();
  });
});
