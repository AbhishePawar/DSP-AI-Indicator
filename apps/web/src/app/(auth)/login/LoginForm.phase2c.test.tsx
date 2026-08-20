/**
 * @vitest-environment jsdom
 *
 * Phase 2C — client login chooser wiring (no demo auth).
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

describe("Phase 2C login form", () => {
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
  });

  it("requests OTP with identifier body (email or mobile)", async () => {
    requestOtpMock.mockResolvedValue({
      ok: true,
      result: {
        challenge_id: "chal-1",
        channel: "email",
        expires_at: new Date().toISOString(),
        email: { ok: true, detail: "If an account exists, a one-time code was sent." },
      },
    });
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /login with otp/i }));
    fireEvent.change(screen.getByLabelText(/email or mobile/i), {
      target: { value: "otp@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send otp/i }));
    await waitFor(() => expect(requestOtpMock).toHaveBeenCalledWith("otp@example.com"));
    expect(screen.getByRole("heading", { name: /enter otp/i })).toBeTruthy();
    expect(screen.queryByText(/debug/i)).toBeNull();
  });
});
