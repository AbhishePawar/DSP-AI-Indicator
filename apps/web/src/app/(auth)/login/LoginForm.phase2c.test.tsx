/**
 * @vitest-environment jsdom
 *
 * Client login chooser — password + Google (no email OTP / demo auth).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ThemeProvider } from "@/providers/ThemeProvider";

const loginMock = vi.fn();
const requestOtpMock = vi.fn();
const verifyOtpMock = vi.fn();
const oauthBeginMock = vi.fn();

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

vi.mock("@/lib/api/enterpriseAuth", () => ({
  enterpriseAuthApi: {
    login: (...args: unknown[]) => loginMock(...args),
    requestOtp: (...args: unknown[]) => requestOtpMock(...args),
    verifyOtp: (...args: unknown[]) => verifyOtpMock(...args),
    resendOtp: vi.fn(),
    oauthBegin: (...args: unknown[]) => oauthBeginMock(...args),
  },
}));

vi.mock("@/lib/auth/finishEnterpriseSession", () => ({
  persistEnterpriseSession: vi.fn(),
  extractMfaChallenge: () => null,
  navigateAfterLogin: vi.fn(),
}));

afterEach(() => cleanup());

describe("Login form — Google email + password", () => {
  beforeEach(() => {
    loginMock.mockReset();
    requestOtpMock.mockReset();
    verifyOtpMock.mockReset();
    oauthBeginMock.mockReset();
  });

  it("does not import or render demo auth controls", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(screen.queryByText(/demo mode/i)).toBeNull();
  });

  it("shows password and Google; hides numeric email OTP entry", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("button", { name: /login with password/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /continue with google/i }),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: /login with otp/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /send otp/i })).toBeNull();
    expect(screen.getByRole("link", { name: /sign in with mobile/i })).toBeTruthy();
  });

  it("submits enterprise password login with normalized identifier", async () => {
    loginMock.mockResolvedValue({
      ok: true,
      result: {
        tokens: { access_token: "tok", refresh_token: "r", token_type: "bearer" },
        user: {
          user_id: "u1",
          username: "ada",
          email: "ada@example.com",
          display_name: "Ada",
          roles: ["read_only"],
        },
        session: { session_id: "s1" },
      },
    });
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /login with password/i }));
    fireEvent.change(screen.getByLabelText(/identifier/i), {
      target: { value: "Ada@Example.com" },
    });
    fireEvent.change(document.getElementById("login-password")!, {
      target: { value: "StrongPass1!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^login$/i }));
    await waitFor(() => expect(loginMock).toHaveBeenCalled());
    expect(loginMock.mock.calls[0][0]).toEqual({
      identifier: "ada@example.com",
      password: "StrongPass1!",
      remember_me: false,
    });
    expect(requestOtpMock).not.toHaveBeenCalled();
  });

  it("starts Google OAuth via existing enterprise oauthBegin", async () => {
    oauthBeginMock.mockResolvedValue({
      ok: true,
      result: {
        available: true,
        authorization_url: "https://accounts.google.com/o/oauth2/v2/auth?x=1",
        state: "state-1",
      },
    });
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, origin: "http://localhost:3000", assign },
    });
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    await waitFor(() => expect(oauthBeginMock).toHaveBeenCalled());
    expect(oauthBeginMock.mock.calls[0][0]).toBe("GOOGLE");
    expect(oauthBeginMock.mock.calls[0][1]).toBe(
      "http://localhost:3000/oauth/callback",
    );
    expect(assign).toHaveBeenCalledWith(
      "https://accounts.google.com/o/oauth2/v2/auth?x=1",
    );
    expect(requestOtpMock).not.toHaveBeenCalled();
  });
});
