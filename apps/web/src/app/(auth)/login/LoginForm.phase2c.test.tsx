/**
 * @vitest-environment jsdom
 *
 * Public login — username/password, mobile OTP, username OTP, Google.
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

describe("Login form — public methods", () => {
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

  it("shows username/password, mobile OTP, username OTP, and Google", async () => {
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
    const google = screen.getByRole("button", { name: /continue with google/i });
    expect(google).toBeTruthy();
    expect(google).not.toBeDisabled();
    expect(screen.getByRole("link", { name: /create account/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /request access/i })).toBeNull();
    expect(screen.queryByText(/demo mode/i)).toBeNull();
  });

  it("submits username + password", async () => {
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
    fireEvent.click(screen.getByRole("button", { name: /username and password/i }));
    fireEvent.change(document.getElementById("login-username")!, {
      target: { value: "ada" },
    });
    fireEvent.change(document.getElementById("login-password")!, {
      target: { value: "StrongPass1!" },
    });
    expect(screen.getByRole("link", { name: /forgot password/i })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() => expect(loginMock).toHaveBeenCalled());
    expect(loginMock.mock.calls[0][0]).toEqual({
      identifier: "ada",
      password: "StrongPass1!",
      remember_me: false,
    });
    expect(requestOtpMock).not.toHaveBeenCalled();
  });

  it("sends OTP for mobile number login", async () => {
    requestOtpMock.mockResolvedValue({
      ok: true,
      result: { challenge_id: "ch-1", channel: "mobile", expires_at: "t" },
    });
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /mobile number and otp/i }));
    fireEvent.change(screen.getByLabelText(/mobile number/i), {
      target: { value: "9826912345" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send otp/i }));
    await waitFor(() => expect(requestOtpMock).toHaveBeenCalled());
    expect(requestOtpMock.mock.calls[0][0]).toBe("+919826912345");
  });

  it("sends OTP for username login", async () => {
    requestOtpMock.mockResolvedValue({
      ok: true,
      result: { challenge_id: "ch-2", channel: "mobile", expires_at: "t" },
    });
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /username and otp/i }));
    fireEvent.change(document.getElementById("login-otp-identifier")!, {
      target: { value: "abhishek" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send otp/i }));
    await waitFor(() => expect(requestOtpMock).toHaveBeenCalled());
    expect(requestOtpMock.mock.calls[0][0]).toBe("abhishek");
  });

  it("keeps Continue with Google enabled (always clickable)", async () => {
    const { default: LoginForm } = await import("@/app/(auth)/login/LoginForm");
    render(
      <ThemeProvider>
        <LoginForm />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("button", { name: /continue with google/i }),
    ).not.toBeDisabled();
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
